# 実装進捗ガイド - 別PCでの作業指示

**現在の完成状態：** (2026-02-09 18:00前)
- ✅ DESIGN.md（全体設計）
- ✅ CONSTRAINT_DESIGN.md（OR-Tools制約設計）
- ✅ data/staff_list.yml（スタッフマスタ）
- ✅ data/rules.yml（ルール一覧）
- ✅ data/request_holidays_2026_02.yml（希望休み）
- ✅ convert_csv_to_yaml.py（CSV変換スクリプト）

---

## 別PCでの実装順序

### Phase 1: 基本モデル層 (優先度：高)

**ファイル:**
- [ ] models/__init__.py
- [ ] models/shift.py - ShiftType, Staff, Rule, Shift クラス定義
- [ ] config.py - 設定値、パス定義
- [ ] utils/yaml_handler.py - YAML読み書きユーティリティ

**実装内容:**
- Enum定義（勤務区分）
- dataclassまたはdataclassでモデル定義
- YAMLローダー実装

---

### Phase 2: 最適化エンジン (優先度：高)

**ファイル:**
- [ ] optimizer/__init__.py
- [ ] optimizer/solver.py - OR-Tools CP-SAT初期化
- [ ] optimizer/constraints.py - CONSTRAINT_DESIGN.mdに基づいた制約実装

**実装内容:**
- CpModel() インスタンス化
- shift[staff_id, date] 変数定義
- CONSTRAINT_DESIGN.mdの15ルール実装
- 目的関数構築

**重要:** FR001～FR016, PR001～PR010, RR001 の制約はすべてここ

---

### Phase 3: Flask基本フレーム (優先度：中)

**ファイル:**
- [ ] app.py - Flaskアプリエントリ
- [ ] routes/__init__.py
- [ ] routes/shift_generation.py - POST /api/generate_shift

**実装内容:**
- Flask初期化
- エラーハンドリング
- JSON レスポンス

---

### Phase 4: UI画面 (優先度：低)

**ファイル:**
- [ ] templates/base.html
- [ ] templates/shift_result.html
- [ ] static/css/style.css
- [ ] static/js/grid.js

**実装内容:**
- Gridコンポーネント
- 色分け表示ロジック
- APIコール

---

## 各フェーズの詳細実装ガイド

### Phase 1 詳細

#### models/shift.py の必須クラス

```python
from enum import Enum
from dataclasses import dataclass
from datetime import date

class ShiftType(Enum):
    DAY = 0                # 日勤
    NIGHT = 1              # 夜勤
    NIGHT_SHIFT_OFF = 2    # 夜勤明け
    PUBLIC_HOLIDAY = 3     # 公休
    REQUEST_HOLIDAY = 4    # 希望休
    PAID_HOLIDAY = 5       # 有給

@dataclass
class Staff:
    id: int
    name: str
    class: str  # 介護士 / 初級介護士 / お風呂

@dataclass
class Shift:
    staff_id: int
    date: date
    shift_type: ShiftType

@dataclass
class ShiftResult:
    shifts: dict  # {(staff_id, date): ShiftType}
    violations: list  # [(staff_id, date, rank, rule_id, description)]
    solver_time: float
```

#### utils/yaml_handler.py

```python
import yaml
from pathlib import Path

def load_staff_list(path):
    """staff_list.yml を読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return [Staff(**s) for s in data['staff']]

def load_rules(path):
    """rules.yml を読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    # Ruleモデルへ変換
    return data['rules']

def load_request_holidays(path):
    """request_holidays_2026_02.yml を読み込む"""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data  # staff_requests を返す
```

---

### Phase 2 詳細

#### optimizer/solver.py の基本構造

```python
from ortools.sat.python import cp_model
from datetime import datetime, timedelta
import yaml

class ShiftOptimizer:
    def __init__(self, month_year="2026-02"):
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.month_year = month_year
        self.shift = {}  # {(staff_id, date): variable}
        
    def build_model(self, staff_list, rules, request_holidays):
        """モデル構築メイン"""
        # 変数定義
        self._create_variables(staff_list)
        
        # 制約追加
        self._add_facility_constraints(rules)
        self._add_personal_constraints(staff_list, rules)
        self._add_request_holiday_constraints(request_holidays)
        
        # 目的関数
        self._build_objective()
        
    def _create_variables(self, staff_list):
        """shift[staff_id, date] 変数定義"""
        # 実装: CONSTRAINT_DESIGN.md参照
        pass
    
    def _add_facility_constraints(self, rules):
        """施設ルール制約（FR001-FR016）"""
        # 実装: CONSTRAINT_DESIGN.md参照
        pass
    
    def _add_personal_constraints(self, staff_list, rules):
        """個人ルール制約（PR001-PR010）"""
        # 実装: CONSTRAINT_DESIGN.md参照
        pass
    
    def _build_objective(self):
        """目的関数構築"""
        # 実装: CONSTRAINT_DESIGN.md参照
        pass
    
    def solve(self):
        """最適化実行"""
        status = self.solver.Solve(self.model)
        return status, self._extract_solution()
    
    def _extract_solution(self):
        """結果抽出"""
        result = {}
        for (staff_id, date), var in self.shift.items():
            result[(staff_id, date)] = self.solver.Value(var)
        return result
```

---

### Phase 3 詳細

#### app.py の基本フレーム

```python
from flask import Flask, jsonify, request
from pathlib import Path
import json

app = Flask(__name__)

@app.route('/api/generate_shift', methods=['POST'])
def generate_shift():
    """シフト自動作成エンドポイント"""
    try:
        data = request.json
        month = data.get('month', '2026-02')
        
        # 最適化実行
        optimizer = ShiftOptimizer(month)
        # ...最適化処理
        
        return jsonify({
            'status': 'success',
            'shifts': result,
            'violations': violations
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

---

## 別PCでの続行手順

1. このファイルと CONSTRAINT_DESIGN.md を読む
2. Phase 1 から実装開始
3. 各ファイルのコメント部分に「# 実装: CONSTRAINT_DESIGN.md参照」と書いてあるのは、そのMDを見ながら実装
4. テスト実行時：`python app.py` → http://localhost:5000

---

## 依存パッケージ

別PCで必要：

```
Flask==2.3.0
ortools==9.8.0
PyYAML==6.0
```

セットアップ：
```bash
pip install -r requirements.txt
```

---

## 時間見積もり

- Phase 1: 1-2時間
- Phase 2: 2-3時間（CONSTRAINT_DESIGN.mdで詳細化）
- Phase 3-4: 2-3時間

合計：5-8時間で完成可能
