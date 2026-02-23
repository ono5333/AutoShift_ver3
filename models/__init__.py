"""
AutoShift - データモデル層
2026年2月9日
"""

from enum import Enum
from dataclasses import dataclass
from datetime import date
from typing import List, Dict, Optional

# ====================
# 列挙型定義
# ====================

class ShiftType(Enum):
    """勤務区分"""
    DAY = 0                # 日勤
    NIGHT = 1              # 夜勤
    NIGHT_SHIFT_OFF = 2    # 夜勤明け
    PUBLIC_HOLIDAY = 3     # 公休
    REQUEST_HOLIDAY = 4    # 希望休
    PAID_HOLIDAY = 5       # 有給

class RuleRank(Enum):
    """ルール優先度"""
    A = 1  # 絶対順守
    B = 2  # 基本順守
    C = 3  # 努力目標

class StaffClass(Enum):
    """職種分類"""
    CAREGIVER = "介護士"
    JUNIOR_CAREGIVER = "初級介護士"
    BATH_STAFF = "お風呂"

# ====================
# データクラス
# ====================

@dataclass
class Staff:
    """スタッフ情報"""
    id: int
    name: str
    staff_class: str  # "介護士" / "初級介護士" / "お風呂"
    employment_type: str = "正社員"  # "正社員" / "パート"
    
    def is_caregiver(self) -> bool:
        return self.staff_class == "介護士"
    
    def is_bath_staff(self) -> bool:
        return self.staff_class == "お風呂"

@dataclass
class Rule:
    """ルール情報"""
    id: str
    rank: str  # "A" / "B" / "C"
    title: str
    description: str
    rule_type: str  # "facility" / "personal" / "relationship"

@dataclass
class RequestHoliday:
    """希望休・有給情報"""
    staff_id: int
    date: str  # "2026-02-01"
    request_type: str  # "希" / "有"

@dataclass
class Shift:
    """シフト情報（単一）"""
    staff_id: int
    date: date
    shift_type: ShiftType

@dataclass
class ShiftResult:
    """シフト最適化結果"""
    month: str
    shifts: Dict  # {(staff_id, date): ShiftType}
    violations: List[Dict]  # [(staff_id, date, rank, rule_id, description)]
    solver_time: float
    solver_status: str  # "OPTIMAL" / "FEASIBLE" / "INFEASIBLE"

# ====================
# エクスポート
# ====================

__all__ = [
    'ShiftType',
    'RuleRank',
    'StaffClass',
    'Staff',
    'Rule',
    'RequestHoliday',
    'Shift',
    'ShiftResult'
]
