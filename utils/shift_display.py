"""
AutoShift - シフト結果表示ユーティリティ
2026年2月9日

役割:
- シフト結果の視覚的表示
- 勤務統計レポート
- 制約違反詳細表示
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from datetime import date
import calendar

try:
    from models import ShiftType, Staff, ShiftResult
except ImportError:
    from ..models import ShiftType, Staff, ShiftResult


class ShiftDisplayManager:
    """
    シフト結果表示管理クラス
    """
    
    def __init__(self):
        self.shift_type_names = {
            ShiftType.DAY: "日",
            ShiftType.NIGHT: "夜", 
            ShiftType.NIGHT_SHIFT_OFF: "明",
            ShiftType.PUBLIC_HOLIDAY: "休",
            ShiftType.REQUEST_HOLIDAY: "希",
            ShiftType.PAID_HOLIDAY: "有"
        }
        
    def display_shift_table(self, result: ShiftResult, staff_list: List[Staff], 
                          dates: List[date]) -> str:
        """
        シフト表を表形式で表示
        
        Args:
            result: 最適化結果
            staff_list: スタッフリスト 
            dates: 対象日付リスト
            
        Returns:
            str: 表示用文字列
        """
        print("\n" + "="*80)
        print("🗓️  AutoShift シフト表")
        print("="*80)
        
        # ヘッダー作成（日付）
        header = ["スタッフ名", "職種"] + [f"{d.month}/{d.day}({calendar.day_abbr[d.weekday()]})" for d in dates]
        
        # データ作成
        rows = []
        for staff in staff_list:
            row = [staff.name, staff.staff_class]
            for target_date in dates:
                shift_value = result.shifts.get((staff.id, target_date), 0)
                shift_type = ShiftType(shift_value)
                row.append(self.shift_type_names[shift_type])
            rows.append(row)
            
        # pandas DataFrameで表示
        df = pd.DataFrame(rows, columns=header)
        
        # 表示設定
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        pd.set_option('display.max_colwidth', 12)
        
        print(df.to_string(index=False))
        print("="*80)
        
        return df.to_string(index=False)
        
    def display_staff_statistics(self, result: ShiftResult, staff_list: List[Staff], 
                                dates: List[date]) -> str:
        """
        スタッフ別勤務統計を表示
        
        Args:
            result: 最適化結果
            staff_list: スタッフリスト
            dates: 対象日付リスト
            
        Returns:
            str: 統計表示文字列
        """
        print("\n" + "="*60)
        print("📊 スタッフ別勤務統計")
        print("="*60)
        
        stats_data = []
        for staff in staff_list:
            stats = {
                'スタッフ名': staff.name,
                '職種': staff.staff_class,
                '日勤': 0,
                '夜勤': 0, 
                '夜勤明': 0,
                '公休': 0,
                '希望休': 0,
                '有給': 0,
                '総勤務日': 0
            }
            
            for target_date in dates:
                shift_value = result.shifts.get((staff.id, target_date), 0)
                shift_type = ShiftType(shift_value)
                
                if shift_type == ShiftType.DAY:
                    stats['日勤'] += 1
                    stats['総勤務日'] += 1
                elif shift_type == ShiftType.NIGHT:
                    stats['夜勤'] += 1
                    stats['総勤務日'] += 1
                elif shift_type == ShiftType.NIGHT_SHIFT_OFF:
                    stats['夜勤明'] += 1
                    stats['総勤務日'] += 1
                elif shift_type == ShiftType.PUBLIC_HOLIDAY:
                    stats['公休'] += 1
                elif shift_type == ShiftType.REQUEST_HOLIDAY:
                    stats['希望休'] += 1
                elif shift_type == ShiftType.PAID_HOLIDAY:
                    stats['有給'] += 1
                    
            stats_data.append(stats)
            
        # DataFrame作成・表示
        df = pd.DataFrame(stats_data)
        print(df.to_string(index=False))
        
        # 合計統計
        print(f"\n📈 全体統計:")
        print(f"   日勤総数: {df['日勤'].sum()}回")
        print(f"   夜勤総数: {df['夜勤'].sum()}回")
        print(f"   夜勤明総数: {df['夜勤明'].sum()}回")
        print(f"   公休総数: {df['公休'].sum()}日")
        print(f"   希望休総数: {df['希望休'].sum()}日")
        print(f"   有給総数: {df['有給'].sum()}日")
        print("="*60)
        
        return df.to_string(index=False)
        
    def display_violations(self, result: ShiftResult) -> str:
        """
        制約違反情報を表示
        
        Args:
            result: 最適化結果
            
        Returns:
            str: 違反情報表示文字列
        """
        print("\n" + "="*50)
        print("⚠️  制約違反情報")
        print("="*50)
        
        if not result.violations:
            print("🎉 制約違反は発見されませんでした！")
            print("="*50)
            return "制約違反なし"
            
        for i, violation in enumerate(result.violations, 1):
            print(f"{i}. {violation.get('description', '不明な違反')}")
            if 'penalty' in violation:
                print(f"   ペナルティ: {violation['penalty']}")
            if 'weight' in violation:
                print(f"   重み: {violation['weight']}")
            print()
            
        print("="*50)
        return f"制約違反 {len(result.violations)}件"
        
    def display_daily_assignment(self, result: ShiftResult, staff_list: List[Staff], 
                               dates: List[date]) -> str:
        """
        日別配置状況を表示
        
        Args:
            result: 最適化結果
            staff_list: スタッフリスト
            dates: 対象日付リスト
            
        Returns:
            str: 日別配置表示文字列
        """
        print("\n" + "="*70)
        print("📅 日別配置状況")
        print("="*70)
        
        for target_date in dates[:7]:  # 最初の1週間のみ表示
            print(f"\n🗓️  {target_date.strftime('%Y年%m月%d日')} ({calendar.day_name[target_date.weekday()]})")
            print("-" * 50)
            
            day_assignments = {'日勤': [], '夜勤': [], '夜勤明': [], '公休': [], '希望休': [], '有給': []}
            
            for staff in staff_list:
                shift_value = result.shifts.get((staff.id, target_date), 0)
                shift_type = ShiftType(shift_value)
                shift_name = self.shift_type_names[shift_type]
                day_assignments[shift_name].append(f"{staff.name}({staff.staff_class})")
                
            for shift_name, staff_names in day_assignments.items():
                if staff_names:
                    print(f"   {shift_name}: {', '.join(staff_names)}")
                    
        print("="*70)
        return "日別配置表示完了"
        
    def export_to_csv(self, result: ShiftResult, staff_list: List[Staff], 
                     dates: List[date], filename: Optional[str] = None) -> str:
        """
        シフト結果をCSVファイルにエクスポート（グリッド形式・統計統合）
        
        Args:
            result: 最適化結果
            staff_list: スタッフリスト 
            dates: 対象日付リスト
            filename: 出力ファイル名（Noneの場合自動生成）
            
        Returns:
            str: 出力ファイルパス
        """
        if filename is None:
            month_str = dates[0].strftime('%Y_%m')
            filename = f"autoshift_result_{month_str}.csv"
            
        # === 1. ヘッダー作成 ===
        # 日付列
        date_headers = [target_date.strftime('%m/%d') for target_date in dates]
        # 統計列
        stat_headers = ['日勤回数', '夜勤回数', '夜勤明け回数', '公休回数', '有給回数', '希望休回数', '総勤務日数']
        # 全ヘッダー
        headers = ['スタッフID', 'スタッフ名', '職種'] + date_headers + stat_headers
        
        # === 2. スタッフデータ行作成 ===
        data_rows = []
        
        for staff in staff_list:
            row = [staff.id, staff.name, staff.staff_class]
            
            # 各日のシフト + 統計カウンタ
            stats_count = {'日': 0, '夜': 0, '明': 0, '休': 0, '有': 0, '希': 0}
            
            # 各日のシフト
            for target_date in dates:
                shift_value = result.shifts.get((staff.id, target_date), 0)
                shift_type = ShiftType(shift_value)
                shift_name = self.shift_type_names[shift_type]
                row.append(shift_name)
                
                # 統計カウント
                if shift_name in stats_count:
                    stats_count[shift_name] += 1
            
            # 個人統計を行の右側に追加
            row.extend([
                stats_count['日'],      # 日勤回数
                stats_count['夜'],      # 夜勤回数  
                stats_count['明'],      # 夜勤明け回数
                stats_count['休'],      # 公休回数
                stats_count['有'],      # 有給回数
                stats_count['希'],      # 希望休回数
                stats_count['日'] + stats_count['夜']  # 総勤務日数
            ])
            
            data_rows.append(row)
        
        # === 3. 日別統計行作成 ===
        # 全体合計行
        daily_totals_row = ['', '日別合計', '']  # スタッフID, 名前, 職種は空白
        
        # 各シフトタイプ別の詳細統計行
        daily_day_row = ['', '日勤者数', '']
        daily_night_row = ['', '夜勤者数', '']
        daily_off_row = ['', '夜勤明け者数', '']
        daily_holiday_row = ['', '公休者数', '']
        daily_paid_row = ['', '有給者数', '']
        daily_request_row = ['', '希望休者数', '']
        
        for target_date in dates:
            daily_count = {'日': 0, '夜': 0, '明': 0, '休': 0, '有': 0, '希': 0}
            
            for staff in staff_list:
                shift_value = result.shifts.get((staff.id, target_date), 0)
                shift_type = ShiftType(shift_value)  
                shift_name = self.shift_type_names[shift_type]
                if shift_name in daily_count:
                    daily_count[shift_name] += 1
            
            # 各統計行に値を追加
            daily_totals_row.append(str(sum(daily_count.values())))  # 総人数
            daily_day_row.append(str(daily_count['日']))              # 日勤者数
            daily_night_row.append(str(daily_count['夜']))            # 夜勤者数
            daily_off_row.append(str(daily_count['明']))              # 夜勤明け者数
            daily_holiday_row.append(str(daily_count['休']))          # 公休者数
            daily_paid_row.append(str(daily_count['有']))             # 有給者数
            daily_request_row.append(str(daily_count['希']))          # 希望休者数
        
        # 統計列の合計計算
        daily_stats_totals = [0, 0, 0, 0, 0, 0, 0]  # 統計列の合計用
        for i in range(len(stat_headers)):
            if i < 6:  # 日勤〜希望休の合計
                daily_stats_totals[i] = sum(row[3 + len(dates) + i] for row in data_rows)
            else:  # 総勤務日数の合計
                daily_stats_totals[i] = sum(row[3 + len(dates) + i] for row in data_rows)
        
        # 各統計行に統計列を追加
        daily_totals_row.extend([str(stat) for stat in daily_stats_totals])
        daily_day_row.extend([str(daily_stats_totals[0]), '', '', '', '', '', str(daily_stats_totals[0])])
        daily_night_row.extend(['', str(daily_stats_totals[1]), '', '', '', '', str(daily_stats_totals[1])])
        daily_off_row.extend(['', '', str(daily_stats_totals[2]), '', '', '', ''])
        daily_holiday_row.extend(['', '', '', str(daily_stats_totals[3]), '', '', ''])
        daily_paid_row.extend(['', '', '', '', str(daily_stats_totals[4]), '', ''])
        daily_request_row.extend(['', '', '', '', '', str(daily_stats_totals[5]), ''])
        
        # === 4. CSV出力 ===
        data = []
        
        # ヘッダー追加
        data.append(headers)
        
        # スタッフデータ追加
        data.extend(data_rows)
        
        # 日別統計行追加（詳細）
        data.append(daily_totals_row)      # 日別合計
        data.append(daily_day_row)         # 日勤者数
        data.append(daily_night_row)       # 夜勤者数
        data.append(daily_off_row)         # 夜勤明け者数
        data.append(daily_holiday_row)     # 公休者数
        data.append(daily_paid_row)        # 有給者数
        data.append(daily_request_row)     # 希望休者数
        
        # 全体統計行追加
        summary_row = ['', '全体統計', f'スタッフ{len(staff_list)}名×{len(dates)}日']
        summary_row.extend([''] * len(dates))  # 日付列は空白
        # 統計列を文字列に変換して追加
        summary_row.extend([
            str(sum(row[3 + len(dates)] for row in data_rows)),      # 総日勤回数
            str(sum(row[3 + len(dates) + 1] for row in data_rows)),  # 総夜勤回数
            str(sum(row[3 + len(dates) + 2] for row in data_rows)),  # 総夜勤明け回数
            str(sum(row[3 + len(dates) + 3] for row in data_rows)),  # 総公休回数
            str(sum(row[3 + len(dates) + 4] for row in data_rows)),  # 総有給回数
            str(sum(row[3 + len(dates) + 5] for row in data_rows)),  # 総希望休回数
            str(sum(row[3 + len(dates) + 6] for row in data_rows))   # 総勤務日数
        ])
        data.append(summary_row)
        
        # DataFrame作成・保存
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, header=False, encoding='utf-8-sig')
        
        print(f"📁 CSV出力完了（グリッド形式・統計統合): {filename}")
        return filename
    
    def generate_shift_table_data(self, result: ShiftResult, staff_list: List[Staff], 
                                 dates: List[date]) -> Dict[str, Any]:
        """
        シフト表データをWeb表示用辞書として生成
        
        Args:
            result: 最適化結果
            staff_list: スタッフリスト 
            dates: 対象日付リスト
            
        Returns:
            Dict[str, Any]: Web表示用シフトデータ
        """
        # ヘッダー作成（日付）
        headers = [f"{d.month}/{d.day}" for d in dates]
        
        # データ作成 - JavaScript期待形式に合わせる
        rows = []
        for staff in staff_list:
            # 各日のシフトをdaysオブジェクトに格納
            days = {}
            for target_date in dates:
                day_num = target_date.day
                shift_value = result.shifts.get((staff.id, target_date), 0)
                shift_type = ShiftType(shift_value)
                days[day_num] = self.shift_type_names[shift_type]
            
            row = {
                'staff_name': staff.name,
                'staff_class': staff.staff_class,
                'days': days
            }
            rows.append(row)
        
        return {
            'headers': headers,
            'rows': rows,  # JavaScript期待のキー名に変更
            'total_days': len(dates),
            'total_staff': len(staff_list)
        }
    
    def generate_statistics_data(self, result: ShiftResult, staff_list: List[Staff], 
                               dates: List[date]) -> Dict[str, Any]:
        """
        統計データをWeb表示用辞書として生成
        
        Args:
            result: 最適化結果  
            staff_list: スタッフリスト
            dates: 対象日付リスト
            
        Returns:
            Dict[str, Any]: Web表示用統計データ
        """
        stats_data = []
        total_stats = {shift_type.name: 0 for shift_type in ShiftType}
        
        for staff in staff_list:
            staff_stats = {
                'staff_name': staff.name,
                'staff_class': staff.staff_class,
                'shifts': {shift_type.name: 0 for shift_type in ShiftType}
            }
            
            # 各日のシフトを集計
            for target_date in dates:
                shift_value = result.shifts.get((staff.id, target_date), 0)
                shift_type = ShiftType(shift_value)
                staff_stats['shifts'][shift_type.name] += 1
                total_stats[shift_type.name] += 1
            
            # 勤務日数計算（日勤・夜勤の合計）
            staff_stats['work_days'] = (staff_stats['shifts']['DAY'] + 
                                      staff_stats['shifts']['NIGHT'])
            staff_stats['total_days'] = len(dates)
            staff_stats['work_ratio'] = round(staff_stats['work_days'] / len(dates) * 100, 1)
            
            stats_data.append(staff_stats)
        
        return {
            'staff_statistics': stats_data,
            'total_statistics': total_stats,
            'summary': {
                'total_staff': len(staff_list),
                'total_days': len(dates),
                'total_shifts': sum(total_stats.values())
            }
        }