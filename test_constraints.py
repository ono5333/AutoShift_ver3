# FR014/FR016制約追加の簡単テスト
import sys
sys.path.append('.')

print("=== FR014/FR016制約追加テスト ===")

from optimizer.constraints import ConstraintManager
from ortools.sat.python import cp_model

# 簡単なテスト: 制約追加メソッドが存在するか確認
print("1. FR014メソッド確認:")
print(f"   hasattr: {hasattr(ConstraintManager, '_add_fr014_bath_staff_assignment')}")

print("2. FR016メソッド確認:")  
print(f"   hasattr: {hasattr(ConstraintManager, '_add_fr016_caregiver_workdays_balance')}")

print("3. ソースコードでの制約呼び出し確認:")
import inspect
source = inspect.getsource(ConstraintManager.add_facility_constraints)
has_fr014 = "_add_fr014_bath_staff_assignment" in source
has_fr016 = "_add_fr016_caregiver_workdays_balance" in source

print(f"   FR014呼び出し: {has_fr014}")
print(f"   FR016呼び出し: {has_fr016}")

if has_fr014 and has_fr016:
    print("✅ FR014/FR016制約の追加が完了しています")
else:
    print("❌ 制約追加に問題があります")

print("=== テスト完了 ===")