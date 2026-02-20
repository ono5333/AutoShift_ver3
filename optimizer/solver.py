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

# プロジェクトルートからインポート（修正版）
sys.path.append(str(Path(__file__).parent.parent))

try:
    from models import ShiftType, Staff, ShiftResult
    from utils import load_project_staff, load_project_rules, load_project_request_holidays
except ImportError:
    # 相対インポート予備
    from ..models import ShiftType, Staff, ShiftResult
    from ..utils import load_project_staff, load_project_rules, load_project_request_holidays

from .constraints import ConstraintManager


class ShiftOptimizer:
    """
    OR-Tools CP-SAT を使用したシフト自動最適化クラス
    
    機能:
    - 月次スタッフシフトの自動生成
    - 施設ルール・個人ルール・人間関係ルールの制約考慮
    - 違反情報の詳細レポート
    """
    
    def __init__(self, month_year: str = "2026-02"):
        """
        初期化
        
        Args:
            month_year: 最適化対象月 (例: "2026-02")
        """
        self.month_year = month_year
        self.year, self.month = map(int, month_year.split('-'))
        
        # OR-Tools初期化
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # 決定変数: shift[staff_id, date] = 勤務区分
        self.shift = {}
        
        # データ保持
        self.staff_list = []
        self.rules = {}
        self.request_holidays = {}
        self.dates = []
        
        # 制約マネージャー
        self.constraint_manager: Optional[ConstraintManager] = None
        
        # 結果保存
        self.solve_time = 0.0
        self.solve_status = ""
        self.violations = []
        
    def load_data(self) -> None:
        """プロジェクトデータの読み込み"""
        try:
            print(f"[INFO] {self.month_year} のシフト最適化を開始...")
            
            # スタッフ・ルール・希望休み読み込み
            self.staff_list = load_project_staff()
            self.staff_list = [s for s in self.staff_list if s.staff_class != "看護師"]
            self._sort_staff_list_for_generation()
            self.rules = load_project_rules()
            self.request_holidays = load_project_request_holidays(self.month_year)
            
            # 対象月の日付リスト作成
            self._generate_dates()
            
            print(f"[INFO] データ読み込み完了:")
            print(f"   - スタッフ: {len(self.staff_list)}名")
            print(f"   - 施設ルール: {len(self.rules['facility_rules'])}個") 
            print(f"   - 個人ルール: {len(self.rules['personal_rules'])}個")
            print(f"   - 人間関係ルール: {len(self.rules['relationship_rules'])}個")
            print(f"   - 対象日数: {len(self.dates)}日")
            
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
            print("[INFO] 最適化モデル構築中...")
            
            # 1. 決定変数作成
            self._create_variables()
            
            # 2. 制約マネージャー初期化
            self.constraint_manager = ConstraintManager(
                self.model, self.shift, self.staff_list, 
                self.rules, self.request_holidays, self.dates
            )
            
            # 3. 制約追加
            self._add_constraints()
            
            # 4. 目的関数構築
            self._build_objective()
            
            print("[OK] モデル構築完了")
            
        except Exception as e:
            raise Exception(f"モデル構築エラー: {e}")
    
    def _create_variables(self) -> None:
        """決定変数 shift[staff_id, date] の作成"""
        print("   - 決定変数作成中...")
        
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
                
        print(f"   - 決定変数 {len(self.shift)}個 作成完了")
        
    def _add_constraints(self) -> None:
        """全制約の追加"""
        print("   - 制約追加中...")
        
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
        
        print("   - 制約追加完了")
        
    def _build_objective(self) -> None:
        """目的関数の構築"""
        print("   - 目的関数構築中...")
        
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
            
        print("   - 目的関数構築完了")
        
    def solve(self) -> ShiftResult:
        """
        最適化実行
        
        Returns:
            ShiftResult: 最適化結果（ステータス・シフト・違反情報等）
        """
        try:
            print("[RUN] 最適化実行中...")
            
            # タイムアウト設定（60秒）
            self.solver.parameters.max_time_in_seconds = 60
            
            # 最適化実行
            start_time = time.time()
            status = self.solver.Solve(self.model)
            end_time = time.time()
            
            self.solve_time = end_time - start_time
            
            # ステータス判定
            if status == cp_model.OPTIMAL:
                self.solve_status = "OPTIMAL"
                print(f"[OK] 最適解発見！ ({self.solve_time:.2f}秒)")
            elif status == cp_model.FEASIBLE:
                self.solve_status = "FEASIBLE"
                print(f"[WARN] 実行可能解発見 ({self.solve_time:.2f}秒)")
            elif status == cp_model.INFEASIBLE:
                self.solve_status = "INFEASIBLE"
                print(f"[ERROR] 実行不可能 ({self.solve_time:.2f}秒)")
                # 空の結果を返す
                return ShiftResult(
                    month=self.month_year,
                    shifts={},
                    violations=[],
                    solver_time=self.solve_time,
                    solver_status=self.solve_status
                )
            else:
                self.solve_status = "UNKNOWN"
                print(f"❓ 解不明 ({self.solve_time:.2f}秒)")
                # 空の結果を返す
                return ShiftResult(
                    month=self.month_year,
                    shifts={},
                    violations=[],
                    solver_time=self.solve_time,
                    solver_status=self.solve_status
                )
                
            # 結果抽出
            result = self._extract_solution()
            return result
            
        except Exception as e:
            raise Exception(f"最適化実行エラー: {e}")
            
    def _extract_solution(self) -> ShiftResult:
        """最適化結果の抽出"""
        print("📋 結果抽出中...")
        
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
            solver_status=self.solve_status
        )
        
        print(f"[INFO] 結果抽出完了:")
        print(f"   - シフト割当: {len(shifts)}件")
        print(f"   - 制約違反: {len(self.violations)}件")
        
        return result
        
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
            print(f"[ERROR] 最適化エラー: {e}")
            raise
