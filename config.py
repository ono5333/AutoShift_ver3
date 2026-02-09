"""
AutoShift - 設定ファイル
"""

from pathlib import Path

# プロジェクトルート
BASE_DIR = Path(__file__).parent

# データディレクトリ
DATA_DIR = BASE_DIR / 'data'

# ファイルパス
STAFF_LIST_FILE = DATA_DIR / 'staff_list.yml'
RULES_FILE = DATA_DIR / 'rules.yml'

# 月別希望休ファイル（テンプレート）
REQUEST_HOLIDAYS_TEMPLATE = DATA_DIR / 'request_holidays_{year}_{month:02d}.yml'

# 2月用
REQUEST_HOLIDAYS_202602 = DATA_DIR / 'request_holidays_2026_02.yml'

# OR-Tools ソルバー設定
SOLVER_CONFIG = {
    'max_time_in_seconds': 60.0,
    'num_workers': 4,
    'log_search_progress': False
}

# 勤務区分
SHIFT_TYPES = {
    '日': 0,      # 日勤
    '夜': 1,      # 夜勤
    '明': 2,      # 夜勤明け
    '休': 3,      # 公休
    '希': 4,      # 希望休
    '有': 5       # 有給
}

# 職種分類
STAFF_CLASSES = {
    '介護士': 'caregiver',
    '初級介護士': 'junior_caregiver',
    'お風呂': 'bath_staff'
}

# ルール優先度
RULE_RANKS = {
    'A': 1,  # 絶対順守（ハード制約）
    'B': 2,  # 基本順守（ソフト制約）
    'C': 3   # 努力目標（目的関数）
}

# 色設定（違反表示用）
VIOLATION_COLORS = {
    'A': '#FF6B6B',  # 赤
    'B': '#FFB3BA'   # ピンク
}

# Flask設定
FLASK_CONFIG = {
    'DEBUG': True,
    'PORT': 5000,
    'HOST': '127.0.0.1'
}
