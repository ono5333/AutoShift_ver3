"""
AutoShift - OR-Tools制約マネージャー
2026年2月9日

役割:
- CONSTRAINT_DESIGN.mdの15ルール制約実装
- ランクA/B/C別の制約処理
- 違反情報の追跡と報告
"""

from ortools.sat.python import cp_model
from datetime import date, datetime
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
                 rules: Dict, request_holidays: Dict, dates: List[date]):
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
        
        # スタッフID→Staffオブジェクトのマッピング
        self.staff_by_id = {staff.id: staff for staff in staff_list}
        
        # ペナルティ変数（ランクB制約違反用）
        self.penalty_vars = []
        
        # 重み変数（ランクC制約用）
        self.weight_vars = []
        
        # 違反追跡
        self.constraint_violations = []
        
        print(f"🔗 制約マネージャー初期化完了")
        
    def add_facility_constraints(self) -> None:
        """施設ルール制約（FR001-FR016）の追加（簡易版）"""
        print("   📋 施設ルール制約追加中...")
        
        try:
            # FR001: 夜勤は毎日2名配置 (ランクA)  
            self._add_fr001_night_shift_daily_2_staff()
            
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
            
            # FR013: 連続勤務の上限 (ランクA)
            self._add_fr013_max_consecutive_days()
            
            # FR005: 2月の公休 (ランクA)
            self._add_fr005_february_holidays()
            
            # FR015: 勤務日数の計算 (ランクB)
            self._add_fr015_work_days_calculation()
            
            # 複雑な制約は一時的にスキップ（型不整合エラー修正まで）
            # TODO: FR014,FR016を修正後に再有効化
            # - FR014: お風呂担当の配置 (ランクB) - 型不整合修正が必要
            # - FR016: 介護士の勤務日数平均化 (ランクC) - 型不整合修正が必要
            # - FR004,006-007: その他月別公休日数制約
            
            print(f"   ✅ 施設ルール制約 9個 追加完了（安定版）")
            
        except Exception as e:
            raise Exception(f"施設ルール制約追加エラー: {e}")
    
    def _add_fr001_night_shift_daily_2_staff(self) -> None:
        """FR001: 夜勤は毎日2名配置 (ランクA)"""
        for target_date in self.dates:
            night_shift_bool_vars = []
            for staff in self.staff_list:
                bool_var = self.model.NewBoolVar(f"is_night_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(bool_var.Not())
                night_shift_bool_vars.append(bool_var)
            self.model.Add(sum(night_shift_bool_vars) == 2)
            
    def _add_fr002_day_shift_daily_3_staff(self) -> None:
        """FR002: 日勤は毎日3名以上配置 (ランクA)"""
        for target_date in self.dates:
            day_shift_bool_vars = []
            for staff in self.staff_list:
                bool_var = self.model.NewBoolVar(f"is_day_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(bool_var.Not())
                day_shift_bool_vars.append(bool_var)
            self.model.Add(sum(day_shift_bool_vars) >= 3)
            
    def _add_fr003_bath_staff_mon_thu(self) -> None:
        """FR003: 月木のお風呂配置 (ランクA)"""
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
                    self.model.Add(sum(bath_staff_bool_vars) >= 1)
                
    def _add_fr004_to_fr007_monthly_holidays(self) -> None:
        """FR004-FR007: 月別公休日数制約（簡易版）"""
        # 月別公休日数取得
        month_holiday_days = self._get_monthly_holiday_days()
        
        if not month_holiday_days:
            return
            
        for staff in self.staff_list:
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
            self.model.Add(sum(all_holiday_flags) == month_holiday_days)
                
    def _get_monthly_holiday_days(self) -> Optional[int]:
        """現在の月に対応する公休日数を取得"""
        current_month = self.dates[0].month
        
        # FR004-FR007の定義
        holiday_rules = {
            1: 12,  # 1月
            2: 8,   # 2月
            12: 11  # 12月
        }
        
        # 3-11月は9日
        if 3 <= current_month <= 11:
            return 9
        else:
            return holiday_rules.get(current_month)
            
    def _add_fr008_request_holiday_limit(self) -> None:
        """FR008: 希望休申請上限 (月3日以内) (ランクA)"""
        for staff in self.staff_list:
            request_holiday_bool_vars = []
            for target_date in self.dates:
                bool_var = self.model.NewBoolVar(f"req_hol_{staff.id}_{target_date.day}")
                self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.REQUEST_HOLIDAY.value).OnlyEnforceIf(bool_var.Not())
                request_holiday_bool_vars.append(bool_var)
            self.model.Add(sum(request_holiday_bool_vars) <= 3)
            
    def _add_fr011_caregiver_in_day_shift(self) -> None:
        """FR011: 日勤に介護士配置 (ランクA)"""
        for target_date in self.dates:
            caregiver_day_bool_vars = []
            for staff in self.staff_list:
                if staff.staff_class == "介護士":
                    bool_var = self.model.NewBoolVar(f"caregiver_day_{staff.id}_{target_date.day}")
                    self.model.Add(self.shift[(staff.id, target_date)] == ShiftType.DAY.value).OnlyEnforceIf(bool_var)
                    self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.DAY.value).OnlyEnforceIf(bool_var.Not())
                    caregiver_day_bool_vars.append(bool_var)
            if caregiver_day_bool_vars:
                self.model.Add(sum(caregiver_day_bool_vars) >= 1)
            
    def _add_fr012_night_shift_off_required(self) -> None:
        """FR012: 夜勤明けは必須 (ランクA) - 希望休優先版"""
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
                    self.model.Add(self.shift[(staff.id, target_date)] != ShiftType.NIGHT.value)
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
                self.model.AddImplication(night_today, night_off_tomorrow)
                
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
                    self.model.AddImplication(night_off_tomorrow, night_today)
                
    def _add_fr013_max_consecutive_days(self) -> None:
        """FR013: 連続勤務の上限 (最大6日) (ランクA)"""
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
                self.model.Add(sum(work_flags) <= 6)
                
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
        total_days = len(self.dates)  # 2026年2月は28日
        expected_work_days = total_days - 8  # FR005で公休数は8日
        
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
            
            self.penalty_vars.extend([penalty_over, penalty_under])
                
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
                    self.penalty_vars.append(penalty_var)
                

            
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
                
                if not all([rule_id, constraint_type, staff_id]):
                    continue
                    
                if constraint_type == 'no_night_shift':
                    # PR001-PR004: 夜勤不可
                    self._add_no_night_shift_constraint(staff_id)
                    implemented_count += 1
                    print(f"      - {rule_id}: {staff_name} 夜勤不可")
                    
                elif constraint_type == 'max_night_shifts':
                    # PR006-PR008: 夜勤回数上限
                    max_count = rule.get('max_count', 5)
                    self._add_max_night_shifts_constraint(staff_id, max_count)
                    implemented_count += 1
                    print(f"      - {rule_id}: {staff_name} 夜勤回数上限{max_count}回")
                    
                elif constraint_type == 'day_off_after_night_shift':
                    # PR009: 夜勤明けは公休
                    self._add_day_off_after_night_shift_constraint(staff_id)
                    implemented_count += 1
                    print(f"      - {rule_id}: {staff_name} 夜勤明けは公休")
                    
                elif constraint_type == 'fixed_day_off':
                    # PR005: 固定休日
                    day_of_week = rule.get('day_of_week', 0)  # 0=日曜日
                    self._add_fixed_day_off_constraint(staff_id, day_of_week)
                    implemented_count += 1
                    weekdays = ['日', '月', '火', '水', '木', '金', '土']
                    day_name = weekdays[day_of_week] if 0 <= day_of_week <= 6 else '不明'
                    print(f"      - {rule_id}: {staff_name} {day_name}曜日固定休")
                
                # 複雑な制約は一時的にスキップ
                # TODO: 段階的に追加
                    
            print(f"   ✅ 個人ルール制約 {implemented_count}個 追加完了")
            
        except Exception as e:
            raise Exception(f"個人ルール制約追加エラー: {e}")
            
    def _add_no_night_shift_constraint(self, staff_id: int) -> None:
        """夜勤不可制約"""
        for target_date in self.dates:
            if (staff_id, target_date) in self.shift:
                self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.NIGHT.value)
                
    def _add_fixed_day_off_constraint(self, staff_id: int, day_of_week: int) -> None:
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
                    self.model.AddAllowedAssignments([self.shift[(staff_id, target_date)]], 
                                                   [[shift] for shift in rest_shifts])
                                                   
    def _add_max_night_shifts_constraint(self, staff_id: int, max_count: int) -> None:
        """夜勤回数上限制約"""
        night_shift_bool_vars = []
        for target_date in self.dates:
            if (staff_id, target_date) in self.shift:
                bool_var = self.model.NewBoolVar(f"max_night_{staff_id}_{target_date.day}")
                self.model.Add(self.shift[(staff_id, target_date)] == ShiftType.NIGHT.value).OnlyEnforceIf(bool_var)
                self.model.Add(self.shift[(staff_id, target_date)] != ShiftType.NIGHT.value).OnlyEnforceIf(bool_var.Not())
                night_shift_bool_vars.append(bool_var)
        if night_shift_bool_vars:
            self.model.Add(sum(night_shift_bool_vars) <= max_count)
        
    def _add_day_off_after_night_shift_constraint(self, staff_id: int) -> None:
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
                
                # 制約: 夜勤 → 翌日夜勤明け → 翌々日公休
                self.model.AddImplication(night_today, night_off_tomorrow)
                self.model.AddImplication(night_off_tomorrow, public_holiday_day_after)
                
                # 特別なケース: 夜勤明けの日に希望休・有給がある場合の考慮
                # 希望休制約が最優先なので、希望休がある日は公休制約を緩和
                
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
                
                if not all([rule_id, constraint_type, staff_ids]) or len(staff_ids) != 2:
                    continue
                
                staff_id1, staff_id2 = staff_ids[0], staff_ids[1]
                
                if constraint_type == 'cannot_work_together' and shift_type == '夜':
                    # RR001: 同日夜勤不可制約を実装
                    self._add_cannot_work_together_night(staff_id1, staff_id2)
                    implemented_count += 1
                    staff1_name = rule.get('staff_names', [f'スタッフ{staff_id1}', f'スタッフ{staff_id2}'])[0]
                    staff2_name = rule.get('staff_names', [f'スタッフ{staff_id1}', f'スタッフ{staff_id2}'])[1]
                    print(f"      - {rule_id}: {staff1_name} & {staff2_name} 同日夜勤不可")
                        
            print(f"   ✅ 人間関係ルール制約 {implemented_count}個 追加完了")
            
        except Exception as e:
            raise Exception(f"人間関係ルール制約追加エラー: {e}")
            
    def _add_cannot_work_together_night(self, staff_id1: int, staff_id2: int) -> None:
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
            
            # 制約: 同日に両方が夜勤になることを禁止
            self.model.Add(night1_var + night2_var <= 1)
            
    def add_request_holiday_constraints(self) -> None:
        """希望休み制約の追加 - 厳密実装"""
        print("   📅 希望休み制約追加中...")
        
        try:
            staff_requests = self.request_holidays.get('staff_requests', [])
            request_count = 0
            applied_requests = []
            
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
                        else:
                            print(f"      ⚠️ 不明な希望休タイプ: {request_type}")
                            continue
                        
                        request_count += 1
                        applied_requests.append(f"{staff_name} {request_date.strftime('%m/%d')} [{request_type}]")
                    else:
                        print(f"      ⚠️ 対象外日付: {staff_name} - {request_date}")
                        
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
        
        # ランクB制約の違反チェック
        for penalty_var in self.penalty_vars:
            if solver.Value(penalty_var) > 0:
                violations.append({
                    'type': 'RankB',
                    'penalty': solver.Value(penalty_var),
                    'description': f'ランクB制約違反'
                })
                
        # ランクC制約の重みチェック  
        for weight_var in self.weight_vars:
            if solver.Value(weight_var) > 0:
                violations.append({
                    'type': 'RankC',
                    'weight': solver.Value(weight_var),
                    'description': f'ランクC制約非最適'
                })
                
        return violations