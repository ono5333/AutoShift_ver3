"""
AutoShift - OR-Tools最適化エンジンメイン
2026年2月9日

役割:
- CP-SAT を使用したシフト最適化
- 制約条件の統合管理
- ShiftResultの生成
"""

from ortools.sat.python import cp_model
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import calendar
import time
import sys
from pathlib import Path
from itertools import combinations
import config

# プロジェクトルートからインポート（修正版）
sys.path.append(str(Path(__file__).parent.parent))

try:
    from models import ShiftType, Staff, ShiftResult
    from utils import load_project_staff, load_project_rules, load_project_request_holidays, load_project_carryover_for_month
except ImportError:
    # 相対インポート予備
    from ..models import ShiftType, Staff, ShiftResult
    from ..utils import load_project_staff, load_project_rules, load_project_request_holidays, load_project_carryover_for_month

from .constraints import ConstraintManager


class ShiftOptimizer:
    """
    OR-Tools CP-SAT を使用したシフト自動最適化クラス
    
    機能:
    - 月次スタッフシフトの自動生成
    - 施設ルール・個人ルール・人間関係ルールの制約考慮
    - 違反情報の詳細レポート
    """
    
    def __init__(
        self,
        month_year: str = "2026-02",
        carryover_override: Optional[Dict[str, Any]] = None,
        disabled_constraints: Optional[List[str]] = None,
        enable_diagnosis: bool = True,
    ):
        """
        初期化
        
        Args:
            month_year: 最適化対象月 (例: "2026-02")
        """
        self.month_year = month_year
        self.year, self.month = map(int, month_year.split('-'))
        self.carryover_override = carryover_override
        self.disabled_constraints = [str(item) for item in (disabled_constraints or [])]
        self.enable_diagnosis = enable_diagnosis
        
        # OR-Tools初期化
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # 決定変数: shift[staff_id, date] = 勤務区分
        self.shift = {}
        
        # データ保持
        self.staff_list = []
        self.rules = {}
        self.request_holidays = {}
        self.carryover = {}
        self.dates = []
        
        # 制約マネージャー
        self.constraint_manager: Optional[ConstraintManager] = None
        
        # 結果保存
        self.solve_time = 0.0
        self.solve_status = ""
        self.solver_status_code: Optional[int] = None
        self.solver_status_name: Optional[str] = None
        self.violations = []
        self.diagnosis: Optional[Dict[str, Any]] = None
        
    def load_data(self) -> None:
        """プロジェクトデータの読み込み"""
        try:
            # noisy log removed
            
            # スタッフ・ルール・希望休み読み込み
            self.staff_list = load_project_staff()
            self.staff_list = [s for s in self.staff_list if s.staff_class != "看護師"]
            self._sort_staff_list_for_generation()
            self.rules = load_project_rules()
            self.request_holidays = load_project_request_holidays(self.month_year)
            if isinstance(self.carryover_override, dict):
                self.carryover = self.carryover_override
            else:
                self.carryover = load_project_carryover_for_month(self.month_year)
            
            # 対象月の日付リスト作成
            self._generate_dates()
            
            # noisy log removed
            
        except Exception as e:
            raise Exception(f"データ読み込みエラー: {e}")

    def _sort_staff_list_for_generation(self) -> None:
        """シフト生成時のスタッフ順を仕様に合わせて整列する。"""
        class_priority = {
            "介護士": 0,
            "初級介護士": 1,
            "お風呂": 2,
            "看護師": 3,
        }
        # 未定義クラスは末尾へ。クラス内はID昇順。
        self.staff_list.sort(key=lambda s: (class_priority.get(s.staff_class, 999), s.id))
            
    def _generate_dates(self) -> None:
        """対象月の日付リストを生成"""
        # 月の最終日を取得
        last_day = calendar.monthrange(self.year, self.month)[1]
        
        self.dates = []
        for day in range(1, last_day + 1):
            self.dates.append(date(self.year, self.month, day))
            
    def build_model(self) -> None:
        """最適化モデルの構築"""
        try:
            # noisy log removed
            
            # 1. 決定変数作成
            self._create_variables()
            
            # 2. 制約マネージャー初期化
            self.constraint_manager = ConstraintManager(
                self.model, self.shift, self.staff_list, 
                self.rules, self.request_holidays, self.dates, self.carryover,
                disabled_constraints=self.disabled_constraints
            )
            
            # 3. 制約追加
            self._add_constraints()
            
            # 4. 目的関数構築
            self._build_objective()
            
            # noisy log removed
            
        except Exception as e:
            raise Exception(f"モデル構築エラー: {e}")
    
    def _create_variables(self) -> None:
        """決定変数 shift[staff_id, date] の作成"""
        # noisy log removed
        
        # 勤務区分の範囲: 0-5 (ShiftTypeの値域)
        # 0: DAY, 1: NIGHT, 2: NIGHT_SHIFT_OFF, 3: PUBLIC_HOLIDAY, 4: REQUEST_HOLIDAY, 5: PAID_HOLIDAY
        min_shift = 0
        max_shift = 5
        
        for staff in self.staff_list:
            for target_date in self.dates:
                var_name = f"shift_s{staff.id}_d{target_date.strftime('%m%d')}"
                self.shift[(staff.id, target_date)] = self.model.NewIntVar(
                    min_shift, max_shift, var_name
                )
                
        # noisy log removed
        
    def _add_constraints(self) -> None:
        """全制約の追加"""
        # noisy log removed
        
        if self.constraint_manager is None:
            raise RuntimeError("ConstraintManager が初期化されていません")
        
        # 希望休み制約（最優先 - ランクS）
        self.constraint_manager.add_request_holiday_constraints()
        
        # 施設ルール制約（FR001-FR016）
        self.constraint_manager.add_facility_constraints()
        
        # 個人ルール制約（PR001-PR010）  
        self.constraint_manager.add_personal_constraints()
        
        # 人間関係ルール制約（RR001）
        self.constraint_manager.add_relationship_constraints()
        
        # noisy log removed
        
    def _build_objective(self) -> None:
        """目的関数の構築"""
        # noisy log removed
        
        if self.constraint_manager is None:
            raise RuntimeError("ConstraintManager が初期化されていません")
        
        # ソフト制約（ランクB, C）の違反最小化
        objective_terms = []
        
        # ランクB制約の違反ペナルティ
        objective_terms.extend(self.constraint_manager.get_rank_b_penalties())
        
        # ランクC制約の重み付け最適化
        objective_terms.extend(self.constraint_manager.get_rank_c_weights())
        
        if objective_terms:
            # 違反の合計を最小化
            self.model.Minimize(sum(objective_terms))
        else:
            # 目的関数が無い場合は適当な定数を最小化
            dummy_var = self.model.NewIntVar(0, 1, "dummy")
            self.model.Minimize(dummy_var)
            
        # noisy log removed
        
    def solve(self) -> ShiftResult:
        """
        最適化実行
        
        Returns:
            ShiftResult: 最適化結果（ステータス・シフト・違反情報等）
        """
        try:
            # print("[RUN] 最適化実行中...")
            
            # タイムアウト設定（config.py）
            self.solver.parameters.max_time_in_seconds = float(
                config.SOLVER_CONFIG.get('max_time_in_seconds', 60.0)
            )
            
            # 最適化実行
            start_time = time.time()
            status = self.solver.Solve(self.model)
            end_time = time.time()
            
            self.solve_time = end_time - start_time
            self.solver_status_code = int(status)
            self.solver_status_name = self._status_to_name(status)
            
            # ステータス判定
            if status == cp_model.OPTIMAL:
                self.solve_status = "OPTIMAL"
                # print(f"[OK] 最適解発見！ ({self.solve_time:.2f}秒)")
            elif status == cp_model.FEASIBLE:
                self.solve_status = "FEASIBLE"
                # print(f"[WARN] 実行可能解発見 ({self.solve_time:.2f}秒)")
            elif status == cp_model.INFEASIBLE:
                self.solve_status = "INFEASIBLE"
                self.diagnosis = self._diagnose_infeasibility()
                # print(f"[ERROR] 実行不可能 ({self.solve_time:.2f}秒)")
                # 空の結果を返す
                return ShiftResult(
                    month=self.month_year,
                    shifts={},
                    violations=[],
                    solver_time=self.solve_time,
                    solver_status=self.solve_status,
                    solver_status_code=self.solver_status_code,
                    solver_status_name=self.solver_status_name,
                    diagnosis=self.diagnosis
                )
            else:
                self.solve_status = "UNKNOWN"
                self.diagnosis = {
                    "available": False,
                    "message": "ソルバーステータスがUNKNOWNのため、競合診断をスキップしました。",
                    "solver_status_code": self.solver_status_code,
                    "solver_status_name": self.solver_status_name,
                }
                # print(f"解不明 ({self.solve_time:.2f}秒)")
                # 空の結果を返す
                return ShiftResult(
                    month=self.month_year,
                    shifts={},
                    violations=[],
                    solver_time=self.solve_time,
                    solver_status=self.solve_status,
                    solver_status_code=self.solver_status_code,
                    solver_status_name=self.solver_status_name,
                    diagnosis=self.diagnosis
                )
                
            # 結果抽出
            result = self._extract_solution()
            return result
            
        except Exception as e:
            raise Exception(f"最適化実行エラー: {e}")
            
    def _extract_solution(self) -> ShiftResult:
        """最適化結果の抽出"""
        # noisy log removed
        
        # シフト結果抽出
        shifts = {}
        for (staff_id, target_date), var in self.shift.items():
            shift_value = self.solver.Value(var)
            shifts[(staff_id, target_date)] = ShiftType(shift_value)
            
        # 違反情報抽出
        self.violations = self.constraint_manager.get_violations(self.solver) if self.constraint_manager else []
        
        # ShiftResult作成
        result = ShiftResult(
            month=self.month_year,
            shifts=shifts,
            violations=self.violations,
            solver_time=self.solve_time,
            solver_status=self.solve_status,
            solver_status_code=self.solver_status_code,
            solver_status_name=self.solver_status_name,
            diagnosis=self.diagnosis
        )
        
        # noisy log removed
        
        return result

    @staticmethod
    def _status_to_text(status: int) -> str:
        if status == cp_model.OPTIMAL:
            return "OPTIMAL"
        if status == cp_model.FEASIBLE:
            return "FEASIBLE"
        if status == cp_model.INFEASIBLE:
            return "INFEASIBLE"
        return "UNKNOWN"

    @staticmethod
    def _status_to_name(status: int) -> str:
        status_map = {
            cp_model.OPTIMAL: "OPTIMAL",
            cp_model.FEASIBLE: "FEASIBLE",
            cp_model.INFEASIBLE: "INFEASIBLE",
            getattr(cp_model, "MODEL_INVALID", -999999): "MODEL_INVALID",
            getattr(cp_model, "UNKNOWN", -999998): "UNKNOWN",
        }
        return status_map.get(status, f"UNMAPPED_{status}")

    @staticmethod
    def _is_rank_a(rule: Dict[str, Any]) -> bool:
        return str(rule.get("rank", "A")).upper() == "A"

    def _collect_diagnosis_candidates(self) -> List[str]:
        candidates: List[str] = []
        candidates.append("REQUEST_HOLIDAYS")
        candidates.append("CARRYOVER")

        facility_rank_a_ids = {
            str(rule.get("id"))
            for rule in self.rules.get("facility_rules", [])
            if rule.get("id") and self._is_rank_a(rule)
        }
        ordered_facility_keys = [
            "FR001", "FR023", "FR002", "FR003", "FR008",
            "FR011", "FR012", "FR022", "FR013",
        ]
        for key in ordered_facility_keys:
            if key in facility_rank_a_ids:
                candidates.append(key)
        if any(key in facility_rank_a_ids for key in ("FR004", "FR005", "FR006", "FR007")):
            candidates.append("FR004_TO_FR007")

        for rule in self.rules.get("personal_rules", []):
            rule_id = rule.get("id")
            if rule_id and self._is_rank_a(rule):
                candidates.append(str(rule_id))

        for rule in self.rules.get("relationship_rules", []):
            rule_id = rule.get("id")
            if rule_id and self._is_rank_a(rule):
                candidates.append(str(rule_id))

        unique_candidates: List[str] = []
        seen = set()
        for key in candidates:
            if key in seen:
                continue
            seen.add(key)
            unique_candidates.append(key)
        return unique_candidates

    def _probe_status_with_disabled_constraints(self, extra_disabled: List[str], probe_time_sec: float) -> str:
        disabled = sorted(set(self.disabled_constraints).union(set(extra_disabled)))
        probe = ShiftOptimizer(
            month_year=self.month_year,
            carryover_override=self.carryover_override,
            disabled_constraints=disabled,
            enable_diagnosis=False,
        )
        probe.load_data()
        probe.build_model()
        probe.solver.parameters.max_time_in_seconds = probe_time_sec
        status = probe.solver.Solve(probe.model)
        return self._status_to_text(status)

    def _diagnose_infeasibility(self) -> Dict[str, Any]:
        if not self.enable_diagnosis:
            return {"available": False, "message": "診断は無効化されています。"}

        try:
            candidates = self._collect_diagnosis_candidates()
            base_limit = float(config.SOLVER_CONFIG.get("max_time_in_seconds", 60.0))
            probe_time_sec = max(1.0, min(3.0, base_limit / 30.0))

            single_hits: List[Dict[str, Any]] = []
            max_single_candidates = min(20, len(candidates))
            single_source = candidates[:max_single_candidates]
            for key in single_source:
                status = self._probe_status_with_disabled_constraints([key], probe_time_sec)
                if status in ("OPTIMAL", "FEASIBLE"):
                    single_hits.append({"disabled": [key], "result_status": status})

            pair_hits: List[Dict[str, Any]] = []
            if not single_hits:
                max_pair_candidates = min(10, len(single_source))
                pair_source = single_source[:max_pair_candidates]
                for left, right in combinations(pair_source, 2):
                    status = self._probe_status_with_disabled_constraints([left, right], probe_time_sec)
                    if status in ("OPTIMAL", "FEASIBLE"):
                        pair_hits.append({"disabled": [left, right], "result_status": status})
                    if len(pair_hits) >= 8:
                        break

            return {
                "available": True,
                "base_status": self.solve_status,
                "probe_time_limit_sec": probe_time_sec,
                "candidate_count": len(candidates),
                "single_probe_count": len(single_source),
                "truncated": len(candidates) > len(single_source),
                "single_rule_relaxations": single_hits,
                "pair_rule_relaxations": pair_hits,
                "message": (
                    "single_rule_relaxations が空の場合は、単体ではなく複合条件の競合の可能性があります。"
                ),
            }
        except Exception as e:
            return {
                "available": False,
                "error": f"診断実行エラー: {e}"
            }
        
    def optimize(self) -> ShiftResult:
        """
        シフト最適化の全工程実行
        
        Returns:
            ShiftResult: 最適化結果
        """
        try:
            # データ読み込み
            self.load_data()
            
            # モデル構築
            self.build_model()
            
            # 最適化実行・結果抽出
            result = self.solve()
            
            return result
            
        except Exception as e:
            # print(f"[ERROR] 最適化エラー: {e}")
            raise
