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
        シフト結果をCSVファイルにエクスポート
        
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
            
        # データ作成
        data = []
        for staff in staff_list:
            row = {
                'スタッフID': staff.id,
                'スタッフ名': staff.name,
                '職種': staff.staff_class
            }
            for target_date in dates:
                date_str = target_date.strftime('%m/%d')
                shift_value = result.shifts.get((staff.id, target_date), 0)
                shift_type = ShiftType(shift_value)
                row[date_str] = self.shift_type_names[shift_type]
            data.append(row)
            
        # CSV出力
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"📁 CSV出力完了: {filename}")
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