#!/usr/bin/env python3
"""
PR005制約（山田志保里の日曜日固定休）のテストスクリプト
"""

import sys
from pathlib import Path
from datetime import datetime, date
import calendar

# プロジェクトルートをPythonパスに追加
sys.path.append(str(Path(__file__).parent))

from optimizer.solver import ShiftOptimizer

def test_pr005_constraint():
    """PR005制約のテスト - 山田志保里の日曜日固定休"""
    print("=== PR005制約テスト ===")
    print("対象: 山田志保里の日曜日固定休制約")
    
    # 2026年2月で最適化テスト（希望休ファイルが存在する）
    month_year = "2026-02"
    
    print(f"\n最適化実行中: {month_year}")
    
    # ShiftOptimizerを初期化
    optimizer = ShiftOptimizer(month_year)
    
    # 最適化実行
    result = optimizer.optimize()
    
    if not result:
        print("❌ 最適化結果がありません")
        return
    
    print(f"✅ 最適化完了: {len(result.shifts)} 件のシフト結果")
    print(f"📊 ソルバー状態: {result.solver_status}")
    print(f"⏰ 実行時間: {result.solver_time:.2f}秒")
    
    # 山田志保里のIDを特定
    yamada_id = None
    for staff in optimizer.staff_list:
        if "山田志保里" in staff.name:
            yamada_id = staff.id
            break
    
    if yamada_id is None:
        print("❌ 山田志保里が見つかりません")
        return
    
    print(f"📋 山田志保里のスケジュール確認 (ID: {yamada_id})")
    
    # 2026年2月の日曜日を確認
    year = 2026
    month = 2
    sundays = []
    
    # 全日程から日曜日を抽出
    for (staff_id, target_date), shift_type in result.shifts.items():
        if staff_id == yamada_id and target_date.weekday() == 6:  # 日曜日
            sundays.append(target_date)
    
    sundays = sorted(set(sundays))  # 重複排除とソート
    print(f"対象期間の日曜日: {[s.strftime('%Y-%m-%d') for s in sundays]}")
    
    # 山田志保里の日曜日シフト確認
    sunday_violations = []
    for sunday in sundays:
        if (yamada_id, sunday) in result.shifts:
            shift_type = result.shifts[(yamada_id, sunday)]
            # ShiftTypeのvalueを取得して比較
            from models import ShiftType
            rest_shift_types = [
                ShiftType.PUBLIC_HOLIDAY.value,
                ShiftType.REQUEST_HOLIDAY.value,
                ShiftType.PAID_HOLIDAY.value
            ]
            
            if shift_type not in rest_shift_types:
                sunday_violations.append((sunday, shift_type))
                print(f"❌ {sunday.strftime('%Y-%m-%d')} (日): {ShiftType(shift_type).name} - 制約違反!")
            else:
                print(f"✅ {sunday.strftime('%Y-%m-%d')} (日): {ShiftType(shift_type).name} - OK")
    
    # 結果サマリー
    print(f"\n=== PR005制約テスト結果 ===")
    print(f"日曜日総数: {len(sundays)}")
    print(f"制約違反: {len(sunday_violations)}")
    
    if len(sunday_violations) == 0:
        print("🎉 PR005制約は正常に動作しています!")
    else:
        print(f"⚠️  {len(sunday_violations)} 件の制約違反があります:")
        for sunday, shift_type in sunday_violations:
            print(f"   - {sunday.strftime('%Y-%m-%d')} (日): {shift_type}")

if __name__ == "__main__":
    test_pr005_constraint()