"""
AutoShift - OR-Tools制約マネージャー
2026年2月9日

役割:
- CONSTRAINT_DESIGN.mdの15ルール制約実装
- ランクA/B/C別の制約処理
- 違反情報の追跡と報告
"""

from ortools.sat.python import cp_model
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
import calendar

try:
    from models import ShiftType, Staff
except ImportError:
    from ..models import ShiftType, Staff


class ConstraintManager:
    """
    制約条件管理クラス
    CONSTRAINT_DESIGN.mdのルール実装
    """
    
    def __init__(self, model: cp_model.CpModel, shift: Dict, staff_list: List[Staff], 
                 rules: Dict, request_holidays: Dict, dates: List[date], carryover: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            model: CP-SATモデル
            shift: 決定変数辞書 {(staff_id, date): variable}
            staff_list: スタッフリスト
            rules: ルール辞書（facility_rules, personal_rules, relationship_rules）
            request_holidays: 希望休み辞書
            dates: 対象日付リスト
        """
        self.model = model
        self.shift = shift
        self.staff_list = staff_list
        self.rules = rules
        self.request_holidays = request_holidays
        self.dates = dates
        self.carryover = carryover or {}
        
        # スタッフID→Staffオブジェクトのマッピング
        self.staff_by_id = {staff.id: staff for staff in staff_list}
        
        # ペナルティ変数（ランクB制約違反用）
        self.penalty_vars = []
        
        # 重み変数（ランクC制約用）
        self.weight_vars = []
        
        # 違反追跡（penalty_var, staff_id, date, constraint_name, description）
        self.constraint_violations = []

        # 祝日計算キャッシュ
        self._holiday_cache: Dict[int, set] = {}
        self._rank_var_seq = 0
        
        print(f"🔗 制約マネージャー初期化完了")
        
    def add_facility_constraints(self) -> None:
        """施設ルール制約（FR001-FR016）の追加（簡易版）"""
        print("   📋 施設ルール制約追加中...")
        
        try:
            # 前月末引継ぎ制約（最優先）
            self._add_month_end_carryover_constraints()

            # FR001: 夜勤は毎日2名配置 (ランクA)  
            self._add_fr001_night_shift_daily_2_staff()

            # FR023: スタッフ夜勤回数の月上限 (ランクA)
            self._add_fr023_global_max_night_shifts()
            
            # FR002: 日勤は毎日3名以上配置 (ランクA)
            self._add_fr002_day_shift_daily_3_staff()
            
            # FR003: 月木のお風呂配置 (ランクA)
            self._add_fr003_bath_staff_mon_thu()
            
            # FR008: 希望休申請上限 (ランクA)
            self._add_fr008_request_holiday_limit()
            
            # FR011: 日勤に介護士配置 (ランクA)
            self._add_fr011_caregiver_in_day_shift()
            
            # FR012: 夜勤明けは必須 (ランクA)
            self._add_fr012_night_shift_off_required()

            # FR022: 夜→明 サイクル連続上限 (ランクA)
            self._add_fr022_max_consecutive_night_off_cycles()
            
            # FR013: 連続勤務の上限 (ランクA)
            self._add_fr013_max_consecutive_days()

            # FR026: 6連勤相当の禁止 (ランクB)
            self._add_fr026_max_consecutive_equivalent_work_days()
            
            # FR004-FR007: 月別公休 (ランクA)
            self._add_fr004_to_fr007_monthly_holidays()
            
            # FR015: 勤務日数の計算 (ランクB)
            self._add_fr015_work_days_calculation()
            
            # FR017: 公休の前後配置最適化 (ランクC)
            self._add_fr017_holiday_adjacent_optimization()

            # FR020: 日勤人数の平準化 (ランクC)
            self._add_fr020_day_shift_balance_optimization()

            # FR021: 夜勤回数の平準化 (ランクC)
            self._add_fr021_night_shift_balance_optimization()
            
            # FR018: 連休制限&2連休促進 (ランクB)
            self._add_fr018_max_consecutive_holidays()

            # FR024: 夜→明の後の日勤禁止 (ランクB)
            self._add_fr024_no_day_after_night_off()

            # FR025: 夜勤優先抑制（ランクB）
            self._add_fr025_night_shift_priority_reduction()
            
            # 複雑な制約は一時的にスキップ（型不整合エラー修正まで）
            # TODO: FR014,FR016を修正後に再有効化
            # - FR014: お風呂担当の配置 (ランクB) - 型不整合修正が必要
            # - FR016: 介護士の勤務日数平均化 (ランクC) - 型不整合修正が必要
            # - FR005: 2月限定実装（FR004-FR007統合版に置換済み）
            
            print(f"   ✅ 施設ルール制約 11個 追加完了（安定版）")
            
        except Exception as e:
            raise Exception(f"施設ルール制約追加エラー: {e}")

    def _add_month_end_carryover_constraints(self) -> None:
        """前月末引継ぎ:
        - 前月末が夜勤のスタッフは当月1日を夜勤明けにする
        - 前月末が夜勤明けのスタッフは当月1日の日勤を禁止
        """
        if not self.dates:
            return

        prev_month_last_shifts = self.carryover.get('prev_month_last_shifts', {})
        parsed_prev_shifts: Dict[int, str] = {}
        if isinstance(prev_month_last_shifts, dict):
            for sid, shift_label in prev_month_last_shifts.items():
                try:
                    parsed_prev_shifts[int(sid)] = str(shift_label)
                except (TypeError, ValueError):
                    continue

        night_staff_ids = self.carryover.get('night_staff_ids', [])
        if isinstance(night_staff_ids, list):
            for staff_id in night_staff_ids:
                try:
                    parsed_prev_shifts[int(staff_id)] = '夜'
                except (TypeError, ValueError):
                    continue

        first_date = self.dates[0]
        for staff in self.staff_list:
            staff_id = staff.id
            prev_shift = parsed_prev_shifts.get(staff_id)
            if (staff_id, first_date) not in self.shift:
                continue
            if prev_shift == '夜':
                self.model.Add(self.shift[(staff_id, first_date)] == ShiftType.NIGHT_SHIFT_OFF.value)
            else:
                # 月初1日の「明」は、前月末が「夜」のスタッフ以外は禁止
                self.model.Add(self.shift[(staff_id, first_date)] != ShiftType.NIGHT_SHIFT_OFF.value)
            if prev_shift == '明':
                self.model.Add(self.shift[(staff_id, first_date)] != ShiftType.DAY.value)
    
    def _add_fr001_night_shift_daily_2_staff(self) -> None:
        """FR001: 夜勤は毎日2名配置 (ランクA)"""
        rule = self._get_facility_rule("FR001")
        rank = self._normalize_rank(rule.get('rank', 'A') if rule else 'A')
        weight = self._get_rule_weight(rule, 1)
        for target_date in self.dates:
            night_shift_bool_vars = []
            for staff in self.staff_list:
                bool_var = self.model.NewBoolVar(f"is_night_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(bool_var.Not())
                night_shift_bool_vars.append(bool_var)
            total_night = sum(night_shift_bool_vars)
            if rank == 'A':
                self.model.Add(total_night == 2)
            else:
                over = self.model.NewIntVar(0, len(self.staff_list), f"fr001_over_{target_date.day}")
                under = self.model.NewIntVar(0, len(self.staff_list), f"fr001_under_{target_date.day}")
                self.model.Add(total_night - 2 <= over)
                self.model.Add(2 - total_night <= under)
                self._add_ranked_int_violation(over, rank, "FR001", "夜勤人数超過", None, target_date, weight)
                self._add_ranked_int_violation(under, rank, "FR001", "夜勤人数不足", None, target_date, weight)
            
    def _add_fr002_day_shift_daily_3_staff(self) -> None:
        """FR002: 日勤は毎日3名以上配置 (ランクA)"""
        rule = self._get_facility_rule("FR002")
        rank = self._normalize_rank(rule.get('rank', 'A') if rule else 'A')
        weight = self._get_rule_weight(rule, 1)
        for target_date in self.dates:
            day_shift_bool_vars = []
            for staff in self.staff_list:
                bool_var = self.model.NewBoolVar(f"is_day_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(bool_var.Not())
                day_shift_bool_vars.append(bool_var)
            total_day = sum(day_shift_bool_vars)
            if rank == 'A':
                self.model.Add(total_day >= 3)
            else:
                shortage = self.model.NewIntVar(0, len(self.staff_list), f"fr002_short_{target_date.day}")
                self.model.Add(3 - total_day <= shortage)
                self._add_ranked_int_violation(shortage, rank, "FR002", "日勤人数不足", None, target_date, weight)

    def _add_fr023_global_max_night_shifts(self) -> None:
        """FR023: 全スタッフの夜勤回数を月上限以内にする (ランクA)"""
        rule = self._get_facility_rule("FR023", "global_max_night_shifts")
        if rule is None:
            return

        max_count = int(rule.get('max_count', 7))
        rank = self._normalize_rank(rule.get('rank', 'A'))
        weight = self._get_rule_weight(rule, 1)
        if max_count < 0:
            return

        print(f"      - FR023: 夜勤回数は月{max_count}回まで")

        for staff in self.staff_list:
            night_shift_bool_vars = []
            for target_date in self.dates:
                bool_var = self.model.NewBoolVar(f"fr023_night_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(bool_var.Not())
                night_shift_bool_vars.append(bool_var)
            total_night = sum(night_shift_bool_vars)
            if rank == 'A':
                self.model.Add(total_night <= max_count)
            else:
                over = self.model.NewIntVar(0, len(self.dates), f"fr023_over_{staff.id}")
                self.model.Add(total_night - max_count <= over)
                self._add_ranked_int_violation(
                    over, rank, "FR023", f"{staff.name} 夜勤回数上限超過", staff.id, None, weight
                )
            
    def _add_fr003_bath_staff_mon_thu(self) -> None:
        """FR003: 月木のお風呂配置 (ランクA)"""
        rule = self._get_facility_rule("FR003")
        rank = self._normalize_rank(rule.get('rank', 'A') if rule else 'A')
        weight = self._get_rule_weight(rule, 1)
        for target_date in self.dates:
            # 月曜日(0)・木曜日(3)のチェック
            if target_date.weekday() in [0, 3]:
                # お風呂スタッフが日勤に1名以上
                bath_staff_bool_vars = []
                for staff in self.staff_list:
                    if staff.staff_class == "お風呂":
                        bool_var = self.model.NewBoolVar(f"bath_day_{staff.id}_{target_date.day}")
                        self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(bool_var)
                        self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(bool_var.Not())
                        bath_staff_bool_vars.append(bool_var)
                if bath_staff_bool_vars:
                    total_bath = sum(bath_staff_bool_vars)
                    if rank == 'A':
                        self.model.Add(total_bath >= 1)
                    else:
                        shortage = self.model.NewIntVar(0, 1, f"fr003_short_{target_date.day}")
                        self.model.Add(1 - total_bath <= shortage)
                        self._add_ranked_int_violation(
                            shortage, rank, "FR003", "お風呂担当不足", None, target_date, weight
                        )
                
    def _add_fr004_to_fr007_monthly_holidays(self) -> None:
        """FR004-FR007: 月別公休日数制約（簡易版）"""
        # 月別公休日数とrank取得
        month_holiday_days = self._get_monthly_holiday_days()
        if month_holiday_days is None:
            return
        rank = 'A'
        weight = 1
        weight = 1
        current_month = self.dates[0].month if self.dates else None
        for rule in self.rules.get('facility_rules', []):
            if 'days' not in rule:
                continue
            month_value = rule.get('month')
            matched = (
                isinstance(month_value, int) and month_value == current_month
            ) or (
                isinstance(month_value, list) and current_month in month_value
            )
            if matched:
                rank = self._normalize_rank(rule.get('rank', 'A'))
                weight = self._get_rule_weight(rule, 1)
                break
        
        for staff in self.staff_list:
            # FR006(3-11月)は正社員のみに適用
            if current_month is not None and 3 <= current_month <= 11:
                if getattr(staff, "employment_type", "正社員") != "正社員":
                    continue

            # 各日について公休フラグを作成
            public_holiday_flags = []
            request_holiday_flags = []
            
            for target_date in self.dates:
                # 公休フラグ
                pub_flag = self.model.NewBoolVar(f"pub_flag_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(pub_flag)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(pub_flag.Not())
                public_holiday_flags.append(pub_flag)
                
                # 希望休フラグ
                req_flag = self.model.NewBoolVar(f"req_flag_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(req_flag)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(req_flag.Not())
                request_holiday_flags.append(req_flag)
            
            # 公休+希望休の合計が指定日数
            all_holiday_flags = public_holiday_flags + request_holiday_flags
            total_holidays = sum(all_holiday_flags)
            if rank == 'A':
                self.model.Add(total_holidays == month_holiday_days)
            else:
                over = self.model.NewIntVar(0, len(self.dates), f"fr004_over_{staff.id}")
                under = self.model.NewIntVar(0, len(self.dates), f"fr004_under_{staff.id}")
                self.model.Add(total_holidays - month_holiday_days <= over)
                self.model.Add(month_holiday_days - total_holidays <= under)
                self._add_ranked_int_violation(
                    over, rank, "FR004-7", f"{staff.name} 公休数超過", staff.id, None, weight
                )
                self._add_ranked_int_violation(
                    under, rank, "FR004-7", f"{staff.name} 公休数不足", staff.id, None, weight
                )
                
    def _get_monthly_holiday_days(self) -> Optional[int]:
        """現在の月に対応する公休日数をfacility_rules定義から取得"""
        if not self.dates:
            return None

        current_month = self.dates[0].month
        for rule in self.rules.get('facility_rules', []):
            if 'days' not in rule:
                continue
            month_value = rule.get('month')
            if isinstance(month_value, int) and month_value == current_month:
                return rule.get('days')
            if isinstance(month_value, list) and current_month in month_value:
                return rule.get('days')
        return None
            
    def _add_fr008_request_holiday_limit(self) -> None:
        """FR008: 希望休申請上限 (月3日以内) (ランクA)"""
        facility_rules = self.rules.get('facility_rules', [])
        max_requests = 3
        exempt_classes = set()
        rank = 'A'

        for rule in facility_rules:
            if rule.get('id') == 'FR008' and 'max_requests' in rule:
                max_requests = rule.get('max_requests', 3)
            if rule.get('id') == 'FR008':
                rank = self._normalize_rank(rule.get('rank', 'A'))
                weight = self._get_rule_weight(rule, 1)
            if rule.get('constraint_type') == 'request_limit_exempt_class':
                staff_class = rule.get('staff_class')
                if staff_class:
                    exempt_classes.add(staff_class)

        for staff in self.staff_list:
            if staff.staff_class in exempt_classes:
                continue

            request_holiday_bool_vars = []
            for target_date in self.dates:
                bool_var = self.model.NewBoolVar(f"req_hol_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(bool_var.Not())
                request_holiday_bool_vars.append(bool_var)
            total_req = sum(request_holiday_bool_vars)
            if rank == 'A':
                self.model.Add(total_req <= max_requests)
            else:
                over = self.model.NewIntVar(0, len(self.dates), f"fr008_over_{staff.id}")
                self.model.Add(total_req - max_requests <= over)
                self._add_ranked_int_violation(
                    over, rank, "FR008", f"{staff.name} 希望休上限超過", staff.id, None, weight
                )
            
    def _add_fr011_caregiver_in_day_shift(self) -> None:
        """FR011: 日勤に介護士配置 (ランクA)"""
        rule = self._get_facility_rule("FR011")
        rank = self._normalize_rank(rule.get('rank', 'A') if rule else 'A')
        weight = self._get_rule_weight(rule, 1)
        for target_date in self.dates:
            caregiver_day_bool_vars = []
            for staff in self.staff_list:
                if staff.staff_class == "介護士":
                    bool_var = self.model.NewBoolVar(f"caregiver_day_{staff.id}_{target_date.day}")
                    self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(bool_var)
                    self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(bool_var.Not())
                    caregiver_day_bool_vars.append(bool_var)
            if caregiver_day_bool_vars:
                total = sum(caregiver_day_bool_vars)
                if rank == 'A':
                    self.model.Add(total >= 1)
                else:
                    shortage = self.model.NewIntVar(0, 1, f"fr011_short_{target_date.day}")
                    self.model.Add(1 - total <= shortage)
                    self._add_ranked_int_violation(
                        shortage, rank, "FR011", "日勤介護士不足", None, target_date, weight
                    )
            
    def _add_fr012_night_shift_off_required(self) -> None:
        """FR012: 夜勤明けは必須 (ランクA) - 希望休優先版"""
        rule = self._get_facility_rule("FR012")
        rank = self._normalize_rank(rule.get('rank', 'A') if rule else 'A')
        weight = self._get_rule_weight(rule, 1)
        for staff in self.staff_list:
            for i, target_date in enumerate(self.dates[:-1]):  # 最終日は除外
                next_date = self.dates[i + 1]
                
                # 翌日に希望休や有給がある場合は夜勤を回避
                has_request_holiday_tomorrow = False
                staff_requests = self.request_holidays.get('staff_requests', [])
                
                for staff_req in staff_requests:
                    if staff_req.get('staff_id') == staff.id:
                        for request in staff_req.get('requests', []):
                            request_date_str = request.get('date')
                            if request_date_str:
                                try:
                                    from datetime import datetime
                                    request_date = datetime.strptime(request_date_str, '%Y-%m-%d').date()
                                    if request_date == next_date and request.get('type') in ['希', '有']:
                                        has_request_holiday_tomorrow = True
                                        break
                                except:
                                    pass
                    if has_request_holiday_tomorrow:
                        break
                
                # 翌日に希望休がある場合は今日夜勤を禁止
                if has_request_holiday_tomorrow:
                    if rank == 'A':
                        self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value)
                    else:
                        is_night = self.model.NewBoolVar(f"fr012_req_prev_night_{staff.id}_{target_date.day}")
                        self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(is_night)
                        self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(is_night.Not())
                        self._add_ranked_bool_violation(
                            is_night, rank, "FR012",
                            f"{staff.name} 希望休前日の夜勤違反",
                            staff_id=staff.id, target_date=target_date, c_weight=weight
                        )
                    continue
                
                # 通常のFR012制約: 夜勤→翌日夜勤明け
                night_today = self.model.NewBoolVar(f"night_today_{staff.id}_{target_date.day}")
                night_off_tomorrow = self.model.NewBoolVar(f"night_off_tomorrow_{staff.id}_{next_date.day}")
                
                # 夜勤の判定
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(night_today)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(night_today.Not())
                
                # 夜勤明けの判定  
                self.model.Add(self.shift[(staff.id, next_date)] == ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(night_off_tomorrow)
                self.model.Add(self.shift[(staff.id, next_date)] != ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(night_off_tomorrow.Not())
                
                # 制約: 夜勤 → 翌日夜勤明け（希望休がない場合のみ）
                if rank == 'A':
                    self.model.AddImplication(night_today, night_off_tomorrow)
                else:
                    viol = self.model.NewBoolVar(f"fr012_viol_no_off_{staff.id}_{target_date.day}")
                    self.model.AddBoolAnd([night_today, night_off_tomorrow.Not()]).OnlyEnforceIf(viol)
                    self.model.AddBoolOr([night_today.Not(), night_off_tomorrow]).OnlyEnforceIf(viol.Not())
                    self._add_ranked_bool_violation(
                        viol, rank, "FR012",
                        f"{staff.name} 夜勤翌日明け違反",
                        staff_id=staff.id, target_date=next_date, c_weight=weight
                    )
                
                # 逆制約: 夜勤明け → 前日夜勤（夜勤明けは前日夜勤がある場合のみ）
                # ただし、希望休制約が最優先
                yesterday_has_request = False
                for staff_req in staff_requests:
                    if staff_req.get('staff_id') == staff.id:
                        for request in staff_req.get('requests', []):
                            request_date_str = request.get('date')
                            if request_date_str:
                                try:
                                    request_date = datetime.strptime(request_date_str, '%Y-%m-%d').date()
                                    if request_date == next_date and request.get('type') in ['希', '有']:
                                        yesterday_has_request = True
                                        break
                                except:
                                    pass
                        if yesterday_has_request:
                            break
                
                # 翌日に希望休がない場合のみ、夜勤明けは前日夜勤を要求
                if not yesterday_has_request:
                    if rank == 'A':
                        self.model.AddImplication(night_off_tomorrow, night_today)
                    else:
                        viol2 = self.model.NewBoolVar(f"fr012_viol_no_prev_night_{staff.id}_{next_date.day}")
                        self.model.AddBoolAnd([night_off_tomorrow, night_today.Not()]).OnlyEnforceIf(viol2)
                        self.model.AddBoolOr([night_off_tomorrow.Not(), night_today]).OnlyEnforceIf(viol2.Not())
                        self._add_ranked_bool_violation(
                            viol2, rank, "FR012",
                            f"{staff.name} 夜勤明け前日夜勤違反",
                            staff_id=staff.id, target_date=next_date, c_weight=weight
                        )
                
    def _add_fr013_max_consecutive_days(self) -> None:
        """FR013: 連続勤務の上限 (最大6日) (ランクA)"""
        rule = self._get_facility_rule("FR013")
        rank = self._normalize_rank(rule.get('rank', 'A') if rule else 'A')
        weight = self._get_rule_weight(rule, 1)
        for staff in self.staff_list:
            for i in range(len(self.dates) - 6):  # 7日連続をチェック
                work_flags = []
                
                for j in range(7):  # 7日間
                    target_date = self.dates[i + j]
                    work_flag = self.model.NewBoolVar(f"consecutive_work_{staff.id}_{target_date.day}_{i}_{j}")
                    
                    # 個別のシフトタイプbolean変数を作成
                    is_day = self.model.NewBoolVar(f"consec_day_{staff.id}_{target_date.day}_{i}_{j}")
                    is_night = self.model.NewBoolVar(f"consec_night_{staff.id}_{target_date.day}_{i}_{j}")
                    is_night_off = self.model.NewBoolVar(f"consec_night_off_{staff.id}_{target_date.day}_{i}_{j}")
                    
                    # シフトタイプ判定
                    self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(is_day)
                    self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(is_day.Not())
                    
                    self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(is_night)
                    self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(is_night.Not())
                    
                    self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_night_off)
                    self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_night_off.Not())
                    
                    # work_flag = is_day OR is_night OR is_night_off の関係を設定
                    self.model.AddImplication(is_day, work_flag)
                    self.model.AddImplication(is_night, work_flag)  
                    self.model.AddImplication(is_night_off, work_flag)
                    
                    work_flags.append(work_flag)
                
                # 7日連続勤務を禁止（最大6日まで）
                if rank == 'A':
                    self.model.Add(sum(work_flags) <= 6)
                else:
                    all_work = self.model.NewBoolVar(f"fr013_violation_{staff.id}_{self.dates[i].day}")
                    self.model.AddBoolAnd(work_flags).OnlyEnforceIf(all_work)
                    self.model.AddBoolOr([w.Not() for w in work_flags]).OnlyEnforceIf(all_work.Not())
                    self._add_ranked_bool_violation(
                        all_work, rank, "FR013",
                        f"{staff.name} 7日連続勤務違反",
                        staff_id=staff.id, target_date=self.dates[i + 6], c_weight=weight
                    )

    def _add_fr022_max_consecutive_night_off_cycles(self) -> None:
        """FR022: 夜→明 サイクルの連続回数上限 (ランクA)"""
        rule = self._get_facility_rule("FR022", "max_consecutive_night_off_cycles")
        if rule is None:
            return

        max_cycles = int(rule.get('max_cycles', 2))
        rank = self._normalize_rank(rule.get('rank', 'A'))
        weight = self._get_rule_weight(rule, 1)
        if max_cycles < 1:
            return

        print(f"      - FR022: 夜→明 サイクル連続上限{max_cycles}回")

        # 上限を超える(max_cycles + 1)サイクルの連続パターンを禁止する
        pattern_len = 2 * (max_cycles + 1)
        if len(self.dates) < pattern_len:
            return

        for staff in self.staff_list:
            for i in range(len(self.dates) - pattern_len + 1):
                expected_flags = []
                for j in range(pattern_len):
                    target_date = self.dates[i + j]
                    expect_night = (j % 2 == 0)
                    flag = self.model.NewBoolVar(f"fr022_match_{staff.id}_{target_date.day}_{i}_{j}")
                    if expect_night:
                        self.model.Add(
                            self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value
                        ).OnlyEnforceIf(flag)
                        self.model.Add(
                            self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value
                        ).OnlyEnforceIf(flag.Not())
                    else:
                        self.model.Add(
                            self.shift[(staff.id, target_date)] == ShiftType.NIGHT_SHIFT_OFF.value
                        ).OnlyEnforceIf(flag)
                        self.model.Add(
                            self.shift[(staff.id, target_date)] != ShiftType.NIGHT_SHIFT_OFF.value
                        ).OnlyEnforceIf(flag.Not())
                    expected_flags.append(flag)

                # すべて一致（= 上限超過パターン）は禁止
                if rank == 'A':
                    self.model.AddBoolOr([f.Not() for f in expected_flags])
                else:
                    violation = self.model.NewBoolVar(f"fr022_violation_{staff.id}_{self.dates[i].day}")
                    self.model.AddBoolAnd(expected_flags).OnlyEnforceIf(violation)
                    self.model.AddBoolOr([f.Not() for f in expected_flags]).OnlyEnforceIf(violation.Not())
                    self._add_ranked_bool_violation(
                        violation, rank, "FR022",
                        f"{staff.name} 夜→明サイクル連続超過",
                        staff_id=staff.id, target_date=self.dates[i + pattern_len - 1], c_weight=weight
                    )
                
    def _add_fr005_february_holidays(self) -> None:
        """FR005: 2月の公休数は8日 - 公休+希望休=8日（有給は別枠）(ランクA)"""
        # 2026年2月の場合のみ適用
        if not self.dates or self.dates[0].month != 2:
            return
            
        for staff in self.staff_list:
            # 申請済み希望休数をカウント
            applied_request_holidays = 0
            staff_requests = self.request_holidays.get('staff_requests', [])
            
            for staff_req in staff_requests:
                if staff_req.get('staff_id') == staff.id:
                    for request in staff_req.get('requests', []):
                        if request.get('type') == '希':
                            # 希望休申請がある日付をカウント
                            request_date_str = request.get('date')
                            if request_date_str:
                                try:
                                    request_date = datetime.strptime(request_date_str, '%Y-%m-%d').date()
                                    if request_date in self.dates:
                                        applied_request_holidays += 1
                                except:
                                    pass
                    break
            
            # 公休数 = 8 - 希望休申請数
            required_public_holidays = 8 - applied_request_holidays
            
            if required_public_holidays > 0:
                public_holiday_flags = []
                
                for target_date in self.dates:
                    # 申請済み希望休・有給の日は除外
                    is_applied_date = False
                    for staff_req in staff_requests:
                        if staff_req.get('staff_id') == staff.id:
                            for request in staff_req.get('requests', []):
                                request_date_str = request.get('date')
                                if request_date_str:
                                    try:
                                        request_date = datetime.strptime(request_date_str, '%Y-%m-%d').date()
                                        if request_date == target_date:
                                            is_applied_date = True
                                            break
                                    except:
                                        pass
                            if is_applied_date:
                                break
                    
                    if not is_applied_date:
                        # 申請のない日のみ公休候補
                        public_holiday_flag = self.model.NewBoolVar(f"force_public_{staff.id}_{target_date.day}")
                        self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(public_holiday_flag)
                        self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(public_holiday_flag.Not())
                        public_holiday_flags.append(public_holiday_flag)
                
                # 公休数を制約
                if public_holiday_flags:
                    self.model.Add(sum(public_holiday_flags) == required_public_holidays)
            
    def _add_fr015_work_days_calculation(self) -> None:
        """FR015: 勤務日数の計算 - 月の日数 - 公休数の日数分勤務を割り当てる (ランクB)"""
        rule = self._get_facility_rule("FR015")
        rank = self._normalize_rank(rule.get('rank', 'B') if rule else 'B')
        weight = self._get_rule_weight(rule, 1)
        total_days = len(self.dates)
        month_holiday_days = self._get_monthly_holiday_days()
        if month_holiday_days is None:
            return
        expected_work_days = total_days - month_holiday_days
        
        for staff in self.staff_list:
            work_flags = []
            
            for target_date in self.dates:
                # 勤務日フラグ（日勤、夜勤、夜勤明けのいずれか）
                work_flag = self.model.NewBoolVar(f"fr015_work_{staff.id}_{target_date.day}")
                
                # シフトタイプbool変数を作成
                is_day = self.model.NewBoolVar(f"fr015_day_{staff.id}_{target_date.day}")
                is_night = self.model.NewBoolVar(f"fr015_night_{staff.id}_{target_date.day}")
                is_night_off = self.model.NewBoolVar(f"fr015_night_off_{staff.id}_{target_date.day}")
                
                # シフトタイプ判定
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(is_day)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(is_day.Not())
                
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(is_night)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(is_night.Not())
                
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_night_off)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_night_off.Not())
                
                # work_flag = is_day OR is_night OR is_night_off（OR制約）
                self.model.AddBoolOr([is_day, is_night, is_night_off]).OnlyEnforceIf(work_flag)
                self.model.AddImplication(work_flag.Not(), is_day.Not())
                self.model.AddImplication(work_flag.Not(), is_night.Not())
                self.model.AddImplication(work_flag.Not(), is_night_off.Not())
                
                work_flags.append(work_flag)
            
            # ランクBなのでペナルティ変数を使用（厳密制約でない）
            penalty_over = self.model.NewIntVar(0, total_days, f"fr015_penalty_over_{staff.id}")
            penalty_under = self.model.NewIntVar(0, total_days, f"fr015_penalty_under_{staff.id}")
            
            self.model.Add(sum(work_flags) - expected_work_days <= penalty_over)
            self.model.Add(expected_work_days - sum(work_flags) <= penalty_under)
            
            self._add_ranked_int_violation(
                penalty_over, rank, "FR015", f"{staff.name}の勤務日数制約違反（超過）",
                staff.id, None, weight
            )
            self._add_ranked_int_violation(
                penalty_under, rank, "FR015", f"{staff.name}の勤務日数制約違反（不足）",
                staff.id, None, weight
            )
                
    def _add_fr014_bath_staff_assignment(self) -> None:
        """FR014: お風呂担当の配置 (ランクB)"""
        # ランクB制約: ペナルティ変数使用
        for target_date in self.dates:
            if target_date.weekday() in [0, 3]:  # 月・木
                bath_staff_vars = []
                for staff in self.staff_list:
                    if staff.staff_class == "お風呂":
                        # Boolean変数を作成してからvarsに追加
                        is_bath_day = self.model.NewBoolVar(f"bath_{staff.id}_{target_date.strftime('%m%d')}")
                        self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(is_bath_day)
                        self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(is_bath_day.Not())
                        bath_staff_vars.append(is_bath_day)
                
                if bath_staff_vars:  # お風呂スタッフが存在する場合
                    # ペナルティ変数: お風呂スタッフが0名の場合に1
                    penalty_var = self.model.NewIntVar(0, 1, f"penalty_bath_{target_date.strftime('%m%d')}")
                    self.model.Add(sum(bath_staff_vars) + penalty_var >= 1)
                    # 詳細情報付きでペナルティ制約を記録
                    self._add_penalty_constraint(penalty_var, None, target_date, "FR014",
                                               f"{target_date.strftime('%m月%d日')}のお風呂担当不足")
                

            
    def _add_fr016_caregiver_workdays_balance(self) -> None:
        """FR016: 介護士の勤務日数平均化 (ランクC)"""
        # 介護士のみを対象
        caregivers = [staff for staff in self.staff_list if staff.staff_class == "介護士"]
        
        if len(caregivers) < 2:
            return  # 介護士が1名以下の場合はスキップ
            
        # 各介護士の勤務日数を計算
        caregiver_workdays = []
        for staff in caregivers:
            work_day_flags = []
            for target_date in self.dates:
                work_flag = self.model.NewBoolVar(f"caregiver_work_{staff.id}_{target_date.day}")
                
                # 各勤務タイプのBoolean変数を作成
                is_day = self.model.NewBoolVar(f"is_day_{staff.id}_{target_date.day}")
                is_night = self.model.NewBoolVar(f"is_night_{staff.id}_{target_date.day}")
                is_night_off = self.model.NewBoolVar(f"is_night_off_{staff.id}_{target_date.day}")
                
                # 各勤務タイプの条件設定
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(is_day)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(is_day.Not())
                
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(is_night)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(is_night.Not())
                
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_night_off)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_night_off.Not())
                
                # 勤務フラグ設定: いずれかの勤務タイプの場合
                self.model.Add(work_flag >= is_day)
                self.model.Add(work_flag >= is_night)
                self.model.Add(work_flag >= is_night_off)
                self.model.Add(work_flag <= is_day + is_night + is_night_off)
                
                work_day_flags.append(work_flag)
            
            caregiver_workdays.append(sum(work_day_flags))
            
        # 勤務日数の分散を最小化（重み変数）
        for i in range(len(caregivers)):
            for j in range(i + 1, len(caregivers)):
                diff_var = self.model.NewIntVar(0, len(self.dates), f"workday_diff_{i}_{j}")
                self.model.AddAbsEquality(diff_var, caregiver_workdays[i] - caregiver_workdays[j])
                self.weight_vars.append(diff_var)
                
    def add_personal_constraints(self) -> None:
        """個人ルール制約（PR001-PR010）の追加"""
        print("   👤 個人ルール制約追加中...")
        
        try:
            personal_rules = self.rules.get('personal_rules', [])
            implemented_count = 0
            
            for rule in personal_rules:
                rule_id = rule.get('id')
                constraint_type = rule.get('constraint_type')
                staff_id = rule.get('staff_id')
                staff_name = rule.get('staff_name', f'スタッフ{staff_id}')
                rank = self._normalize_rank(rule.get('rank', 'A'))
                rule_weight = self._get_rule_weight(rule, 1)
                
                if not all([rule_id, constraint_type, staff_id]):
                    continue
                    
                if constraint_type == 'no_night_shift':
                    # PR001-PR004: 夜勤不可
                    self._add_no_night_shift_constraint(staff_id, rule_id, rank, rule_weight)
                    implemented_count += 1
                    print(f"      - {rule_id}: {staff_name} 夜勤不可 (Rank {rank})")
                    
                elif constraint_type == 'max_night_shifts':
                    # PR006-PR008: 夜勤回数上限
                    max_count = rule.get('max_count', 5)
                    self._add_max_night_shifts_constraint(staff_id, max_count, rule_id, rank, rule_weight)
                    implemented_count += 1
                    print(f"      - {rule_id}: {staff_name} 夜勤回数上限{max_count}回 (Rank {rank})")
                    
                elif constraint_type == 'day_off_after_night_shift':
                    # PR009: 夜勤明けは公休
                    self._add_day_off_after_night_shift_constraint(staff_id, rule_id, rank, rule_weight)
                    implemented_count += 1
                    print(f"      - {rule_id}: {staff_name} 夜勤明けは公休 (Rank {rank})")
                    
                elif constraint_type == 'fixed_day_off':
                    # PR005: 固定休日
                    day_of_week = rule.get('day_of_week', 0)  # 0=日曜日
                    self._add_fixed_day_off_constraint(staff_id, day_of_week, rule_id, rank, rule_weight)
                    implemented_count += 1
                    weekdays = ['日', '月', '火', '水', '木', '金', '土']
                    day_name = weekdays[day_of_week] if 0 <= day_of_week <= 6 else '不明'
                    print(f"      - {rule_id}: {staff_name} {day_name}曜日固定休 (Rank {rank})")

                elif constraint_type == 'fixed_public_holiday_off':
                    # 恒久休み: 勤務系シフトは不可、休暇系シフトのみ許可
                    self._add_fixed_public_holiday_off_constraint(staff_id, rule_id, rank, rule_weight)
                    implemented_count += 1
                    print(f"      - {rule_id}: {staff_name} 祝日休み固定 (Rank {rank})")

                elif constraint_type == 'max_consecutive_day_shifts':
                    # 日勤連続上限（ランクB）
                    max_count = rule.get('max_count', 2)
                    self._add_max_consecutive_day_shifts_constraint(staff_id, max_count, rule_id, rank, rule_weight)
                    implemented_count += 1
                    print(f"      - {rule_id}: {staff_name} 日勤連続上限{max_count}日 (Rank {rank})")
                
                # 複雑な制約は一時的にスキップ
                # TODO: 段階的に追加
                    
            print(f"   ✅ 個人ルール制約 {implemented_count}個 追加完了")
            
        except Exception as e:
            raise Exception(f"個人ルール制約追加エラー: {e}")
            
    def _add_no_night_shift_constraint(
        self, staff_id: int, rule_id: str = "PR", rank: str = "A", c_weight: int = 1
    ) -> None:
        """夜勤不可制約"""
        for target_date in self.dates:
            if (staff_id, target_date) in self.shift:
                if rank == 'A':
                    self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.NIGHT.value)
                else:
                    is_night = self.model.NewBoolVar(f"{rule_id}_no_night_{staff_id}_{target_date.day}")
                    self.model.Add(self.shift[(staff_id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(is_night)
                    self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(is_night.Not())
                    self._add_ranked_bool_violation(
                        is_night, rank, rule_id,
                        f"スタッフ{staff_id} 夜勤不可違反",
                        staff_id=staff_id, target_date=target_date, c_weight=c_weight
                    )
                
    def _add_fixed_day_off_constraint(
        self, staff_id: int, day_of_week: int, rule_id: str = "PR", rank: str = "A", c_weight: int = 1
    ) -> None:
        """固定休日制約 (day_of_week: 0=日, 1=月, ..., 6=土)"""
        for target_date in self.dates:
            if target_date.weekday() == (day_of_week - 1) % 7:  # Python weekday調整
                if (staff_id, target_date) in self.shift:
                    # 休日系のみ許可
                    rest_shifts = [
                        ShiftType.PUBLIC_HOLIDAY.value,
                        ShiftType.REQUEST_HOLIDAY.value, 
                        ShiftType.PAID_HOLIDAY.value
                    ]
                    if rank == 'A':
                        self.model.AddAllowedAssignments([self.shift[(staff_id, target_date)]],
                                                       [[shift] for shift in rest_shifts])
                    else:
                        work_flag = self._create_work_flag(staff_id, target_date, f"{rule_id}_fixed_day_off")
                        self._add_ranked_bool_violation(
                            work_flag, rank, rule_id,
                            f"スタッフ{staff_id} 固定休日違反",
                            staff_id=staff_id, target_date=target_date, c_weight=c_weight
                        )

    def _add_fixed_public_holiday_off_constraint(
        self, staff_id: int, rule_id: str = "PR", rank: str = "A", c_weight: int = 1
    ) -> None:
        """祝日のみ休暇系シフトに限定（非祝日は制約しない）"""
        rest_shifts = [
            ShiftType.PUBLIC_HOLIDAY.value,
            ShiftType.REQUEST_HOLIDAY.value,
            ShiftType.PAID_HOLIDAY.value
        ]
        for target_date in self.dates:
            if not self._is_japanese_public_holiday(target_date):
                continue
            if (staff_id, target_date) in self.shift:
                if rank == 'A':
                    self.model.AddAllowedAssignments(
                        [self.shift[(staff_id, target_date)]],
                        [[shift] for shift in rest_shifts]
                    )
                else:
                    work_flag = self._create_work_flag(staff_id, target_date, f"{rule_id}_fixed_holiday_off")
                    self._add_ranked_bool_violation(
                        work_flag, rank, rule_id,
                        f"スタッフ{staff_id} 祝日休み固定違反",
                        staff_id=staff_id, target_date=target_date, c_weight=c_weight
                    )

    def _is_japanese_public_holiday(self, target_date: date) -> bool:
        """対象日が日本の祝日かを返す（振替休日・国民の休日を含む）"""
        year_holidays = self._holiday_cache.get(target_date.year)
        if year_holidays is None:
            year_holidays = self._build_japanese_holiday_set(target_date.year)
            self._holiday_cache[target_date.year] = year_holidays
        return target_date in year_holidays

    def _build_japanese_holiday_set(self, year: int) -> set:
        holidays = set()

        # 固定祝日
        holidays.add(date(year, 1, 1))    # 元日
        holidays.add(date(year, 2, 11))   # 建国記念の日
        holidays.add(date(year, 2, 23))   # 天皇誕生日
        holidays.add(date(year, 4, 29))   # 昭和の日
        holidays.add(date(year, 5, 3))    # 憲法記念日
        holidays.add(date(year, 5, 4))    # みどりの日
        holidays.add(date(year, 5, 5))    # こどもの日
        holidays.add(date(year, 8, 11))   # 山の日
        holidays.add(date(year, 11, 3))   # 文化の日
        holidays.add(date(year, 11, 23))  # 勤労感謝の日

        # ハッピーマンデー
        holidays.add(self._nth_weekday_of_month(year, 1, 0, 2))   # 成人の日: 1月第2月曜
        holidays.add(self._nth_weekday_of_month(year, 7, 0, 3))   # 海の日: 7月第3月曜
        holidays.add(self._nth_weekday_of_month(year, 9, 0, 3))   # 敬老の日: 9月第3月曜
        holidays.add(self._nth_weekday_of_month(year, 10, 0, 2))  # スポーツの日: 10月第2月曜

        # 春分・秋分
        holidays.add(date(year, 3, self._vernal_equinox_day(year)))
        holidays.add(date(year, 9, self._autumn_equinox_day(year)))

        # 振替休日
        extra_substitute = set()
        for h in sorted(holidays):
            if h.weekday() == 6:  # 日曜
                substitute = h + timedelta(days=1)
                while substitute in holidays:
                    substitute += timedelta(days=1)
                extra_substitute.add(substitute)
        holidays |= extra_substitute

        # 国民の休日（祝日に挟まれた平日）
        start = date(year, 1, 2)
        end = date(year, 12, 30)
        d = start
        extra_citizen = set()
        while d <= end:
            if d not in holidays and (d - timedelta(days=1)) in holidays and (d + timedelta(days=1)) in holidays:
                extra_citizen.add(d)
            d += timedelta(days=1)
        holidays |= extra_citizen

        return holidays

    @staticmethod
    def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
        """month内の第n weekday(0=月曜)の日付を返す"""
        first = date(year, month, 1)
        offset = (weekday - first.weekday()) % 7
        return first + timedelta(days=offset + (n - 1) * 7)

    @staticmethod
    def _vernal_equinox_day(year: int) -> int:
        """1980-2099年向け近似式"""
        return int(20.8431 + 0.242194 * (year - 1980) - int((year - 1980) / 4))

    @staticmethod
    def _autumn_equinox_day(year: int) -> int:
        """1980-2099年向け近似式"""
        return int(23.2488 + 0.242194 * (year - 1980) - int((year - 1980) / 4))
                                                   
    def _add_max_night_shifts_constraint(
        self, staff_id: int, max_count: int, rule_id: str = "PR", rank: str = "A", c_weight: int = 1
    ) -> None:
        """夜勤回数上限制約"""
        night_shift_bool_vars = []
        for target_date in self.dates:
            if (staff_id, target_date) in self.shift:
                bool_var = self.model.NewBoolVar(f"max_night_{staff_id}_{target_date.day}")
                self.model.Add(self.shift[(staff_id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(bool_var.Not())
                night_shift_bool_vars.append(bool_var)
        if night_shift_bool_vars:
            if rank == 'A':
                self.model.Add(sum(night_shift_bool_vars) <= max_count)
            else:
                over_var = self.model.NewIntVar(0, len(night_shift_bool_vars), f"{rule_id}_max_night_over_{staff_id}")
                self.model.Add(sum(night_shift_bool_vars) - max_count <= over_var)
                self.model.Add(over_var >= 0)
                self._add_ranked_int_violation(
                    over_var, rank, rule_id, f"スタッフ{staff_id} 夜勤回数上限超過",
                    staff_id=staff_id, target_date=None, c_weight=c_weight
                )
        
    def _add_day_off_after_night_shift_constraint(
        self, staff_id: int, rule_id: str = "PR", rank: str = "A", c_weight: int = 1
    ) -> None:
        """夜勤明けは公休制約 - OR-Tools CP-SAT対応版"""
        for i, target_date in enumerate(self.dates[:-2]):  # 後2日を除外
            if i + 2 < len(self.dates):
                next_date = self.dates[i + 1]
                day_after_next = self.dates[i + 2]
                
                # Boolean変数を明示的に作成
                night_today = self.model.NewBoolVar(f"pr009_night_{staff_id}_{target_date.day}")
                night_off_tomorrow = self.model.NewBoolVar(f"pr009_night_off_{staff_id}_{next_date.day}")
                public_holiday_day_after = self.model.NewBoolVar(f"pr009_public_{staff_id}_{day_after_next.day}")
                
                # 夜勤フラグの設定
                self.model.Add(self.shift[(staff_id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(night_today)
                self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(night_today.Not())
                
                # 夜勤明けフラグの設定
                self.model.Add(self.shift[(staff_id, next_date)] == ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(night_off_tomorrow)
                self.model.Add(self.shift[(staff_id, next_date)] != ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(night_off_tomorrow.Not())
                
                # 公休フラグの設定
                self.model.Add(self.shift[(staff_id, day_after_next)] == ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(public_holiday_day_after)
                self.model.Add(self.shift[(staff_id, day_after_next)] != ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(public_holiday_day_after.Not())
                
                if rank == 'A':
                    # 制約: 夜勤 → 翌日夜勤明け → 翌々日公休
                    self.model.AddImplication(night_today, night_off_tomorrow)
                    self.model.AddImplication(night_off_tomorrow, public_holiday_day_after)
                else:
                    v1 = self.model.NewBoolVar(f"{rule_id}_viol_1_{staff_id}_{target_date.day}")
                    self.model.AddBoolAnd([night_today, night_off_tomorrow.Not()]).OnlyEnforceIf(v1)
                    self.model.AddBoolOr([night_today.Not(), night_off_tomorrow]).OnlyEnforceIf(v1.Not())
                    self._add_ranked_bool_violation(
                        v1, rank, rule_id,
                        f"スタッフ{staff_id} 夜勤→夜勤明け違反",
                        staff_id=staff_id, target_date=target_date, c_weight=c_weight
                    )

                    v2 = self.model.NewBoolVar(f"{rule_id}_viol_2_{staff_id}_{next_date.day}")
                    self.model.AddBoolAnd([night_off_tomorrow, public_holiday_day_after.Not()]).OnlyEnforceIf(v2)
                    self.model.AddBoolOr([night_off_tomorrow.Not(), public_holiday_day_after]).OnlyEnforceIf(v2.Not())
                    self._add_ranked_bool_violation(
                        v2, rank, rule_id,
                        f"スタッフ{staff_id} 夜勤明け→公休違反",
                        staff_id=staff_id, target_date=next_date, c_weight=c_weight
                    )
                
                # 特別なケース: 夜勤明けの日に希望休・有給がある場合の考慮
                # 希望休制約が最優先なので、希望休がある日は公休制約を緩和

    def _add_max_consecutive_day_shifts_constraint(
        self, staff_id: int, max_count: int, rule_id: str = "PR019", rank: str = "B", c_weight: int = 1
    ) -> None:
        """日勤連続上限制約（ランクB）"""
        if max_count < 1:
            return
        window_size = max_count + 1
        if len(self.dates) < window_size:
            return

        staff = self.staff_by_id.get(staff_id)
        staff_name = staff.name if staff else f"スタッフ{staff_id}"

        for i in range(len(self.dates) - window_size + 1):
            window_dates = self.dates[i:i + window_size]
            is_day_vars = []

            for target_date in window_dates:
                is_day = self.model.NewBoolVar(f"pr019_is_day_{staff_id}_{target_date.day}_{i}")
                self.model.Add(self.shift[(staff_id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(is_day)
                self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(is_day.Not())
                is_day_vars.append(is_day)

            violation = self.model.NewBoolVar(
                f"{rule_id}_violation_{staff_id}_{window_dates[0].day}_{window_dates[-1].day}"
            )
            self.model.AddBoolAnd(is_day_vars).OnlyEnforceIf(violation)
            self.model.AddBoolOr([v.Not() for v in is_day_vars]).OnlyEnforceIf(violation.Not())
            if rank == 'A':
                self.model.AddBoolOr([v.Not() for v in is_day_vars])
            else:
                self._add_ranked_bool_violation(
                    violation, rank, rule_id,
                    f"{staff_name}の日勤連続{window_size}日違反（上限{max_count}日）",
                    staff_id=staff_id, target_date=window_dates[-1], c_weight=c_weight
                )
                
    def add_relationship_constraints(self) -> None:
        """人間関係ルール制約（RR001）の追加"""
        print("   👥 人間関係ルール制約追加中...")
        
        try:
            relationship_rules = self.rules.get('relationship_rules', [])
            implemented_count = 0
            
            for rule in relationship_rules:
                rule_id = rule.get('id')
                constraint_type = rule.get('constraint_type')
                staff_ids = rule.get('staff_ids', [])
                shift_type = rule.get('shift_type')
                rank = self._normalize_rank(rule.get('rank', 'A'))
                rule_weight = self._get_rule_weight(rule, 1)
                
                if not all([rule_id, constraint_type, staff_ids]) or len(staff_ids) != 2:
                    continue
                
                staff_id1, staff_id2 = staff_ids[0], staff_ids[1]
                
                if constraint_type == 'cannot_work_together' and shift_type == '夜':
                    if staff_id1 not in self.staff_by_id or staff_id2 not in self.staff_by_id:
                        continue
                    # RR001: 同日夜勤不可制約を実装
                    self._add_cannot_work_together_night(staff_id1, staff_id2, rule_id, rank, rule_weight)
                    implemented_count += 1
                    staff1_name = rule.get('staff_names', [f'スタッフ{staff_id1}', f'スタッフ{staff_id2}'])[0]
                    staff2_name = rule.get('staff_names', [f'スタッフ{staff_id1}', f'スタッフ{staff_id2}'])[1]
                    print(f"      - {rule_id}: {staff1_name} & {staff2_name} 同日夜勤不可 (Rank {rank})")
                        
            print(f"   ✅ 人間関係ルール制約 {implemented_count}個 追加完了")
            
        except Exception as e:
            raise Exception(f"人間関係ルール制約追加エラー: {e}")
            
    def _add_cannot_work_together_night(
        self, staff_id1: int, staff_id2: int, rule_id: str = "RR001", rank: str = "A", c_weight: int = 1
    ) -> None:
        """同日夜勤不可制約 - OR-Tools CP-SAT対応版"""
        for target_date in self.dates:
            # 各スタッフの夜勤フラグを明示的にboolean変数として作成
            night1_var = self.model.NewBoolVar(f"night_{staff_id1}_{target_date.day}")
            night2_var = self.model.NewBoolVar(f"night_{staff_id2}_{target_date.day}")
            
            # 夜勤フラグの設定
            self.model.Add(self.shift[(staff_id1, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(night1_var)
            self.model.Add(self.shift[(staff_id1, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(night1_var.Not())
            
            self.model.Add(self.shift[(staff_id2, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(night2_var)
            self.model.Add(self.shift[(staff_id2, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(night2_var.Not())
            
            if rank == 'A':
                # 制約: 同日に両方が夜勤になることを禁止
                self.model.Add(night1_var + night2_var <= 1)
            else:
                both_night = self.model.NewBoolVar(f"{rule_id}_both_night_{staff_id1}_{staff_id2}_{target_date.day}")
                self.model.AddBoolAnd([night1_var, night2_var]).OnlyEnforceIf(both_night)
                self.model.AddBoolOr([night1_var.Not(), night2_var.Not()]).OnlyEnforceIf(both_night.Not())
                self._add_ranked_bool_violation(
                    both_night, rank, rule_id,
                    f"スタッフ{staff_id1}と{staff_id2}の同日夜勤違反",
                    staff_id=None, target_date=target_date, c_weight=c_weight
                )
            
    def add_request_holiday_constraints(self) -> None:
        """希望休み制約の追加 - 厳密実装"""
        print("   📅 希望休み制約追加中...")
        
        try:
            staff_requests = self.request_holidays.get('staff_requests', [])
            request_count = 0
            applied_requests = []
            paid_request_dates_by_staff: Dict[int, set] = {}
            
            for staff_req in staff_requests:
                staff_id = staff_req.get('staff_id')
                staff_name = staff_req.get('staff_name', f'スタッフ{staff_id}')
                requests = staff_req.get('requests', [])
                
                for request in requests:
                    request_date_str = request.get('date') 
                    request_type = request.get('type')
                    
                    if not all([request_date_str, request_type, staff_id]):
                        print(f"      ⚠️ 不完全な希望休データ: {staff_name} - {request}")
                        continue
                        
                    # 日付解析
                    try:
                        request_date = datetime.strptime(request_date_str, '%Y-%m-%d').date()
                    except ValueError as e:
                        print(f"      ❌ 日付解析エラー: {request_date_str} - {e}")
                        continue
                    
                    if request_date in self.dates and (staff_id, request_date) in self.shift:
                        if request_type == '希':
                            # 希望休（ランクA制約 - 絶対遵守）
                            self.model.Add(self.shift[(staff_id, request_date)] == ShiftType.REQUEST_HOLIDAY.value)
                        elif request_type == '有':
                            # 有給（ランクA制約 - 絶対遵守）
                            self.model.Add(self.shift[(staff_id, request_date)] == ShiftType.PAID_HOLIDAY.value)
                            paid_request_dates_by_staff.setdefault(staff_id, set()).add(request_date)
                        elif request_type == '日':
                            # 日勤指定（ランクA制約 - 絶対遵守）
                            self.model.Add(self.shift[(staff_id, request_date)] == ShiftType.DAY.value)
                        elif request_type == '夜':
                            # 夜勤指定（ランクA制約 - 絶対遵守）
                            self.model.Add(self.shift[(staff_id, request_date)] == ShiftType.NIGHT.value)
                        elif request_type == '明':
                            # 夜勤明け指定（ランクA制約 - 絶対遵守）
                            self.model.Add(self.shift[(staff_id, request_date)] == ShiftType.NIGHT_SHIFT_OFF.value)
                        elif request_type == '休':
                            # 公休指定（ランクA制約 - 絶対遵守）
                            self.model.Add(self.shift[(staff_id, request_date)] == ShiftType.PUBLIC_HOLIDAY.value)
                        else:
                            print(f"      ⚠️ 不明な希望休タイプ: {request_type}")
                            continue
                        
                        request_count += 1
                        applied_requests.append(f"{staff_name} {request_date.strftime('%m/%d')} [{request_type}]")
                    else:
                        print(f"      ⚠️ 対象外日付: {staff_name} - {request_date}")

            # 有給は申請された日付以外には割り当てない
            for staff in self.staff_list:
                requested_paid_dates = paid_request_dates_by_staff.get(staff.id, set())
                for target_date in self.dates:
                    if target_date not in requested_paid_dates:
                        self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.PAID_HOLIDAY.value)
                        
            print(f"   ✅ 希望休み制約 {request_count}件 追加完了:")
            for req in applied_requests:
                print(f"      - {req}")
            
        except Exception as e:
            raise Exception(f"希望休み制約追加エラー: {e}")
            
    def get_rank_b_penalties(self) -> List:
        """ランクB制約のペナルティ変数リストを返す"""
        return self.penalty_vars
        
    def get_rank_c_weights(self) -> List:
        """ランクC制約の重み変数リストを返す"""  
        return self.weight_vars
        
    def get_violations(self, solver: cp_model.CpSolver) -> List[Dict]:
        """制約違反情報を取得"""
        violations = []
        
        # 詳細な違反情報を記録した制約をチェック
        for penalty_var, staff_id, target_date, constraint_name, description in self.constraint_violations:
            if solver.Value(penalty_var) > 0:
                staff_obj = self.staff_by_id.get(staff_id) if staff_id is not None else None
                violations.append({
                    'type': 'RankB',
                    'rank': 'B',
                    'rule_id': constraint_name,
                    'constraint_name': constraint_name,
                    'staff_id': staff_id,
                    'staff_name': staff_obj.name if staff_obj else None,
                    'date': target_date.strftime('%Y-%m-%d') if target_date else None,
                    'detail': description,
                    'message': description,
                    'penalty': solver.Value(penalty_var)
                })
        
        # 従来のペナルティ変数（詳細情報がないもの）
        recorded_penalty_ids = {id(penalty_var) for penalty_var, _, _, _, _ in self.constraint_violations}
        for penalty_var in self.penalty_vars:
            if id(penalty_var) not in recorded_penalty_ids and solver.Value(penalty_var) > 0:
                violations.append({
                    'type': 'RankB',
                    'rank': 'B',
                    'rule_id': 'Unknown',
                    'constraint_name': 'Unknown',
                    'staff_id': None,
                    'staff_name': None,
                    'date': None,
                    'detail': 'ランクB制約違反',
                    'message': 'ランクB制約違反',
                    'penalty': solver.Value(penalty_var)
                })
                
        # ランクC制約の重みチェック  
        for weight_var in self.weight_vars:
            if solver.Value(weight_var) > 0:
                violations.append({
                    'type': 'RankC',
                    'rank': 'C',
                    'rule_id': 'RankC',
                    'staff_id': None,
                    'staff_name': None,
                    'date': None,
                    'detail': 'ランクC制約非最適',
                    'message': 'ランクC制約非最適',
                    'constraint_name': 'RankC',
                    'weight': solver.Value(weight_var)
                })
                
        return violations
    
    def _add_penalty_constraint(self, penalty_var, staff_id=None, target_date=None, 
                               constraint_name="Unknown", description="制約違反"):
        """ペナルティ制約と違反情報を記録"""
        self.penalty_vars.append(penalty_var)
        self.constraint_violations.append((penalty_var, staff_id, target_date, constraint_name, description))

    def _get_facility_rule(self, rule_id: str, constraint_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        for rule in self.rules.get('facility_rules', []):
            if rule.get('id') == rule_id:
                return rule
            if constraint_type and rule.get('constraint_type') == constraint_type:
                return rule
        return None

    @staticmethod
    def _get_rule_weight(rule: Optional[Dict[str, Any]], default: int = 1) -> int:
        if not rule:
            return default
        try:
            return max(1, int(rule.get('weight', default)))
        except Exception:
            return default

    @staticmethod
    def _normalize_rank(rank: Any) -> str:
        value = str(rank).upper() if rank is not None else "A"
        if value not in ("A", "B", "C"):
            return "A"
        return value

    def _add_ranked_bool_violation(
        self,
        violation_bool: cp_model.IntVar,
        rank: str,
        constraint_name: str,
        description: str,
        staff_id: Optional[int] = None,
        target_date: Optional[date] = None,
        c_weight: int = 1,
    ) -> None:
        """rankに応じて違反boolをハード/ペナルティ/重みへ変換する。"""
        self._add_ranked_int_violation(
            violation_bool, rank, constraint_name, description,
            staff_id=staff_id, target_date=target_date, c_weight=c_weight
        )

    def _add_ranked_int_violation(
        self,
        violation_amount: cp_model.IntVar,
        rank: str,
        constraint_name: str,
        description: str,
        staff_id: Optional[int] = None,
        target_date: Optional[date] = None,
        c_weight: int = 1,
    ) -> None:
        """rankに応じて違反量(int var)をハード/ペナルティ/重みへ変換する。"""
        normalized_rank = self._normalize_rank(rank)
        if normalized_rank == "A":
            self.model.Add(violation_amount == 0)
            return

        self._rank_var_seq += 1
        seq = self._rank_var_seq
        weight = max(1, int(c_weight))
        domain = violation_amount.Proto().domain
        ub = domain[-1] if domain else 1000
        weighted_ub = max(1, ub * weight)
        weighted_var = self.model.NewIntVar(
            0, weighted_ub,
            f"weighted_{constraint_name}_{staff_id or 'all'}_{target_date.day if target_date else 'm'}_{seq}"
        )
        self.model.Add(weighted_var == violation_amount * weight)

        if normalized_rank == "B":
            self._add_penalty_constraint(weighted_var, staff_id, target_date, constraint_name, description)
            return

        # Rank C
        self.weight_vars.append(weighted_var)

    def _create_work_flag(self, staff_id: int, target_date: date, prefix: str) -> cp_model.IntVar:
        """勤務系( 日/夜/明 )のいずれかなら1のフラグを返す。"""
        is_day = self.model.NewBoolVar(f"{prefix}_day_{staff_id}_{target_date.day}")
        is_night = self.model.NewBoolVar(f"{prefix}_night_{staff_id}_{target_date.day}")
        is_night_off = self.model.NewBoolVar(f"{prefix}_nightoff_{staff_id}_{target_date.day}")
        work_flag = self.model.NewBoolVar(f"{prefix}_work_{staff_id}_{target_date.day}")

        self.model.Add(self.shift[(staff_id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(is_day)
        self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(is_day.Not())
        self.model.Add(self.shift[(staff_id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(is_night)
        self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(is_night.Not())
        self.model.Add(self.shift[(staff_id, target_date)] == ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_night_off)
        self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_night_off.Not())

        self.model.AddBoolOr([is_day, is_night, is_night_off]).OnlyEnforceIf(work_flag)
        self.model.AddBoolAnd([is_day.Not(), is_night.Not(), is_night_off.Not()]).OnlyEnforceIf(work_flag.Not())
        return work_flag
    
    def _add_fr017_holiday_adjacent_optimization(self) -> None:
        """FR017: 公休の前後配置最適化 (ランクC)"""
        rule = self._get_facility_rule("FR017", "holiday_adjacent_optimization")
        weight = self._get_rule_weight(rule, 1)
        print("      - FR017: 公休の前後配置最適化")
        
        for staff in self.staff_list:
            for i, target_date in enumerate(self.dates):
                if i == 0 or i == len(self.dates) - 1:
                    continue  # 月初・月末はスキップ
                
                prev_date = self.dates[i - 1]
                next_date = self.dates[i + 1]
                
                # 公休の判定
                holiday_var = self.model.NewBoolVar(f"holiday_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(holiday_var)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(holiday_var.Not())
                
                # 前日の希望休・有給の判定
                prev_special_var = self.model.NewBoolVar(f"prev_special_{staff.id}_{target_date.day}")
                prev_is_request = self.model.NewBoolVar(f"prev_request_{staff.id}_{target_date.day}")
                prev_is_paid = self.model.NewBoolVar(f"prev_paid_{staff.id}_{target_date.day}")
                
                self.model.Add(self.shift[(staff.id, prev_date)] == ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(prev_is_request)
                self.model.Add(self.shift[(staff.id, prev_date)] != ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(prev_is_request.Not())
                self.model.Add(self.shift[(staff.id, prev_date)] == ShiftType.PAID_HOLIDAY.value).OnlyEnforceIf(prev_is_paid)
                self.model.Add(self.shift[(staff.id, prev_date)] != ShiftType.PAID_HOLIDAY.value).OnlyEnforceIf(prev_is_paid.Not())
                
                self.model.AddBoolOr([prev_is_request, prev_is_paid]).OnlyEnforceIf(prev_special_var)
                self.model.AddBoolAnd([prev_is_request.Not(), prev_is_paid.Not()]).OnlyEnforceIf(prev_special_var.Not())
                
                # 翌日の希望休・有給の判定
                next_special_var = self.model.NewBoolVar(f"next_special_{staff.id}_{target_date.day}")
                next_is_request = self.model.NewBoolVar(f"next_request_{staff.id}_{target_date.day}")
                next_is_paid = self.model.NewBoolVar(f"next_paid_{staff.id}_{target_date.day}")
                
                self.model.Add(self.shift[(staff.id, next_date)] == ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(next_is_request)
                self.model.Add(self.shift[(staff.id, next_date)] != ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(next_is_request.Not())
                self.model.Add(self.shift[(staff.id, next_date)] == ShiftType.PAID_HOLIDAY.value).OnlyEnforceIf(next_is_paid)
                self.model.Add(self.shift[(staff.id, next_date)] != ShiftType.PAID_HOLIDAY.value).OnlyEnforceIf(next_is_paid.Not())
                
                self.model.AddBoolOr([next_is_request, next_is_paid]).OnlyEnforceIf(next_special_var)
                self.model.AddBoolAnd([next_is_request.Not(), next_is_paid.Not()]).OnlyEnforceIf(next_special_var.Not())
                
                # 前後どちらかに希望休・有給がある場合の優遇
                adjacent_special_var = self.model.NewBoolVar(f"adjacent_special_{staff.id}_{target_date.day}")
                self.model.AddBoolOr([prev_special_var, next_special_var]).OnlyEnforceIf(adjacent_special_var)
                self.model.AddBoolAnd([prev_special_var.Not(), next_special_var.Not()]).OnlyEnforceIf(adjacent_special_var.Not())
                
                # 公休で前後に特別休暇がない場合の重み変数（小さいほど良い）
                weight_var = self.model.NewIntVar(0, 1, f"weight_fr017_{staff.id}_{target_date.day}")
                optimization_var = self.model.NewBoolVar(f"optimize_fr017_{staff.id}_{target_date.day}")
                
                # 公休 AND 前後に特別休暇がない場合
                self.model.AddBoolAnd([holiday_var, adjacent_special_var.Not()]).OnlyEnforceIf(optimization_var)
                self.model.AddBoolOr([holiday_var.Not(), adjacent_special_var]).OnlyEnforceIf(optimization_var.Not())
                
                self.model.Add(weight_var == 1).OnlyEnforceIf(optimization_var)
                self.model.Add(weight_var == 0).OnlyEnforceIf(optimization_var.Not())
                
                if weight == 1:
                    self.weight_vars.append(weight_var)
                else:
                    weighted = self.model.NewIntVar(0, weight, f"weight_fr017_{staff.id}_{target_date.day}")
                    self.model.Add(weighted == weight_var * weight)
                    self.weight_vars.append(weighted)

    def _add_fr018_max_consecutive_holidays(self) -> None:
        """FR018: 連休制限と2連休促進 (ランクB)"""
        rule = self._get_facility_rule("FR018", "max_consecutive_rest_days")
        rank = self._normalize_rank(rule.get('rank', 'B') if rule else 'B')
        weight = self._get_rule_weight(rule, 1)
        print("      - FR018: 連休制限と2連休促進")
        
        for staff in self.staff_list:
            # 3連休以上の禁止（ランクB制約）
            for i in range(len(self.dates) - 2):  # 3日連続をチェック
                dates_triplet = self.dates[i:i+3]
                
                # 3日連続で休み（公休・希望休・有給）の判定
                rest_vars = []
                for date in dates_triplet:
                    rest_var = self.model.NewBoolVar(f"rest_{staff.id}_{date.day}_fr018")
                    
                    # 休みの種類を判定
                    is_public = self.model.NewBoolVar(f"public_{staff.id}_{date.day}_fr018")
                    is_request = self.model.NewBoolVar(f"request_{staff.id}_{date.day}_fr018")
                    is_paid = self.model.NewBoolVar(f"paid_{staff.id}_{date.day}_fr018")
                    
                    self.model.Add(self.shift[(staff.id, date)] == ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(is_public)
                    self.model.Add(self.shift[(staff.id, date)] != ShiftType.PUBLIC_HOLIDAY.value).OnlyEnforceIf(is_public.Not())
                    self.model.Add(self.shift[(staff.id, date)] == ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(is_request)
                    self.model.Add(self.shift[(staff.id, date)] != ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(is_request.Not())
                    self.model.Add(self.shift[(staff.id, date)] == ShiftType.PAID_HOLIDAY.value).OnlyEnforceIf(is_paid)
                    self.model.Add(self.shift[(staff.id, date)] != ShiftType.PAID_HOLIDAY.value).OnlyEnforceIf(is_paid.Not())
                    
                    # いずれかの休み
                    self.model.AddBoolOr([is_public, is_request, is_paid]).OnlyEnforceIf(rest_var)
                    self.model.AddBoolAnd([is_public.Not(), is_request.Not(), is_paid.Not()]).OnlyEnforceIf(rest_var.Not())
                    
                    rest_vars.append(rest_var)
                
                # 3日連続休みを禁止（ランクB制約）
                consecutive_3_rest = self.model.NewBoolVar(f"consec3_rest_{staff.id}_{dates_triplet[0].day}")
                self.model.AddBoolAnd(rest_vars).OnlyEnforceIf(consecutive_3_rest)
                self.model.AddBoolOr([var.Not() for var in rest_vars]).OnlyEnforceIf(consecutive_3_rest.Not())
                
                # 3連休違反時のペナルティ変数
                penalty_var = self.model.NewIntVar(0, 1000, f"penalty_fr018_{staff.id}_{dates_triplet[0].day}")
                self.model.Add(penalty_var == 1000).OnlyEnforceIf(consecutive_3_rest)
                self.model.Add(penalty_var == 0).OnlyEnforceIf(consecutive_3_rest.Not())
                
                self._add_ranked_int_violation(
                    penalty_var, rank, "FR018",
                    f"{staff.name}の{dates_triplet[0].day}-{dates_triplet[2].day}日に3連休が発生",
                    staff.id, dates_triplet[1], weight
                )

    def _add_fr020_day_shift_balance_optimization(self) -> None:
        """FR020: 日勤人数の平準化 (ランクC)"""
        facility_rules = self.rules.get('facility_rules', [])
        fr020_rule = None
        for rule in facility_rules:
            if rule.get('id') == 'FR020':
                fr020_rule = rule
                break

        # ルール未定義時は何もしない（明示的に有効化された場合のみ適用）
        if fr020_rule is None:
            return

        print("      - FR020: 日勤人数の平準化")
        weight = int(fr020_rule.get('weight', 10))
        target_classes = set(fr020_rule.get('target_classes', ['介護士', '初級介護士']))
        target_staff = [s for s in self.staff_list if s.staff_class in target_classes]

        day_counts = []
        max_staff = len(target_staff)
        if max_staff == 0 or not self.dates:
            return

        for target_date in self.dates:
            day_flags = []
            for staff in target_staff:
                is_day = self.model.NewBoolVar(f"fr020_is_day_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(is_day)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(is_day.Not())
                day_flags.append(is_day)

            day_count = self.model.NewIntVar(0, max_staff, f"fr020_day_count_{target_date.day}")
            self.model.Add(day_count == sum(day_flags))
            day_counts.append(day_count)

        if len(day_counts) < 2:
            return

        max_day_count = self.model.NewIntVar(0, max_staff, "fr020_max_day_count")
        min_day_count = self.model.NewIntVar(0, max_staff, "fr020_min_day_count")
        day_count_range = self.model.NewIntVar(0, max_staff, "fr020_day_count_range")

        self.model.AddMaxEquality(max_day_count, day_counts)
        self.model.AddMinEquality(min_day_count, day_counts)
        self.model.Add(day_count_range == max_day_count - min_day_count)

        # 目的関数で最小化するため、重み付きで追加
        self.weight_vars.append(day_count_range * weight)

    def _add_fr021_night_shift_balance_optimization(self) -> None:
        """FR021: 夜勤回数の平準化 (ランクC)"""
        facility_rules = self.rules.get('facility_rules', [])
        personal_rules = self.rules.get('personal_rules', [])
        fr021_rule = None
        for rule in facility_rules:
            if rule.get('id') == 'FR021':
                fr021_rule = rule
                break

        # ルール未定義時は何もしない（明示的に有効化された場合のみ適用）
        if fr021_rule is None:
            return

        print("      - FR021: 夜勤回数の平準化")
        weight = int(fr021_rule.get('weight', 10))

        # 夜勤不可(PR no_night_shift)スタッフを対象外にする
        no_night_staff_ids = {
            rule.get('staff_id')
            for rule in personal_rules
            if rule.get('constraint_type') == 'no_night_shift' and rule.get('staff_id') is not None
        }
        target_staff = [s for s in self.staff_list if s.id not in no_night_staff_ids]

        if len(target_staff) < 2 or not self.dates:
            return

        total_nights = len(self.dates) * 2  # FR001: 毎日夜勤2名
        max_night_upper = total_nights
        night_counts = []

        for staff in target_staff:
            night_flags = []
            for target_date in self.dates:
                is_night = self.model.NewBoolVar(f"fr021_is_night_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(is_night)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(is_night.Not())
                night_flags.append(is_night)

            night_count = self.model.NewIntVar(0, max_night_upper, f"fr021_night_count_{staff.id}")
            self.model.Add(night_count == sum(night_flags))
            night_counts.append(night_count)

        max_night_count = self.model.NewIntVar(0, max_night_upper, "fr021_max_night_count")
        min_night_count = self.model.NewIntVar(0, max_night_upper, "fr021_min_night_count")
        night_count_range = self.model.NewIntVar(0, max_night_upper, "fr021_night_count_range")

        self.model.AddMaxEquality(max_night_count, night_counts)
        self.model.AddMinEquality(min_night_count, night_counts)
        self.model.Add(night_count_range == max_night_count - min_night_count)

        # 目的関数で最小化するため、重み付きで追加
        self.weight_vars.append(night_count_range * weight)

    def _add_fr024_no_day_after_night_off(self) -> None:
        """FR024: 夜勤明け(明) の次日に 日勤 を禁止"""
        rule = self._get_facility_rule("FR024", "no_day_after_night_off")
        if rule is None:
            return

        rank = self._normalize_rank(rule.get('rank', 'B'))
        weight = self._get_rule_weight(rule, 1)
        print("      - FR024: 明けの後の日勤禁止")

        if len(self.dates) < 2:
            return

        for staff in self.staff_list:
            for i in range(len(self.dates) - 1):
                d1 = self.dates[i]
                d2 = self.dates[i + 1]

                is_off = self.model.NewBoolVar(f"fr024_off_{staff.id}_{d2.day}_{i}")
                is_day = self.model.NewBoolVar(f"fr024_day_{staff.id}_{d2.day}_{i}")

                self.model.Add(self.shift[(staff.id, d1)] == ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_off)
                self.model.Add(self.shift[(staff.id, d1)] != ShiftType.NIGHT_SHIFT_OFF.value).OnlyEnforceIf(is_off.Not())
                self.model.Add(self.shift[(staff.id, d2)] == ShiftType.DAY.value).OnlyEnforceIf(is_day)
                self.model.Add(self.shift[(staff.id, d2)] != ShiftType.DAY.value).OnlyEnforceIf(is_day.Not())

                violation = self.model.NewBoolVar(f"fr024_violation_{staff.id}_{d2.day}_{i}")
                self.model.AddBoolAnd([is_off, is_day]).OnlyEnforceIf(violation)
                self.model.AddBoolOr([is_off.Not(), is_day.Not()]).OnlyEnforceIf(violation.Not())

                self._add_ranked_bool_violation(
                    violation, rank, "FR024",
                    f"{staff.name} の 明→日 パターン違反",
                    staff_id=staff.id, target_date=d2, c_weight=weight
                )

    def _add_fr025_night_shift_priority_reduction(self) -> None:
        """FR025: 夜勤均等化時の優先抑制（Rank B推奨）"""
        rule = self._get_facility_rule("FR025", "night_shift_priority_reduction")
        if rule is None:
            return

        rank = self._normalize_rank(rule.get('rank', 'B'))
        weight = self._get_rule_weight(rule, 1)

        high_ids = set(rule.get('high_priority_staff_ids', []))
        medium_ids = set(rule.get('medium_priority_staff_ids', []))
        high_penalty = max(1, int(rule.get('high_priority_penalty', 3)))
        medium_penalty = max(1, int(rule.get('medium_priority_penalty', 2)))
        other_penalty = max(1, int(rule.get('other_penalty', 1)))

        print("      - FR025: 夜勤優先抑制")

        for staff in self.staff_list:
            if staff.id in high_ids:
                coeff = high_penalty
            elif staff.id in medium_ids:
                coeff = medium_penalty
            else:
                coeff = other_penalty

            for target_date in self.dates:
                is_night = self.model.NewBoolVar(f"fr025_night_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(is_night)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(is_night.Not())

                weighted_night = self.model.NewIntVar(0, coeff, f"fr025_weighted_{staff.id}_{target_date.day}")
                self.model.Add(weighted_night == is_night * coeff)

                self._add_ranked_int_violation(
                    weighted_night,
                    rank,
                    "FR025",
                    f"{staff.name} の夜勤優先抑制違反",
                    staff_id=staff.id,
                    target_date=target_date,
                    c_weight=weight
                )

    def _add_fr026_max_consecutive_equivalent_work_days(self) -> None:
        """FR026: 日/夜/明 を勤務として数えた連勤上限（6連勤相当禁止）"""
        rule = self._get_facility_rule("FR026", "max_consecutive_equivalent_work_days")
        if rule is None:
            return

        rank = self._normalize_rank(rule.get('rank', 'B'))
        weight = self._get_rule_weight(rule, 1)
        max_equivalent_days = int(rule.get('max_equivalent_days', 5))
        if max_equivalent_days < 1:
            return

        # max=5 の場合、6日すべて勤務(日/夜/明)の窓を違反とする
        window_size = max_equivalent_days + 1
        if len(self.dates) < window_size:
            return

        print(f"      - FR026: {window_size}連勤相当禁止（日/夜/明ベース）")

        for staff in self.staff_list:
            for i in range(len(self.dates) - window_size + 1):
                work_flags = []
                for j in range(window_size):
                    target_date = self.dates[i + j]
                    work_flags.append(
                        self._create_work_flag(
                            staff.id,
                            target_date,
                            f"fr026_{staff.id}_{i}_{j}"
                        )
                    )

                violation = self.model.NewBoolVar(f"fr026_violation_{staff.id}_{i}")
                self.model.AddBoolAnd(work_flags).OnlyEnforceIf(violation)
                self.model.AddBoolOr([f.Not() for f in work_flags]).OnlyEnforceIf(violation.Not())

                if rank == 'A':
                    self.model.AddBoolOr([f.Not() for f in work_flags])
                else:
                    self._add_ranked_bool_violation(
                        violation,
                        rank,
                        "FR026",
                        f"{staff.name} の{window_size}連勤相当違反",
                        staff_id=staff.id,
                        target_date=self.dates[i + window_size - 1],
                        c_weight=weight
                    )
