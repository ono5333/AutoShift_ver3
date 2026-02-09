# AutoShift - シフト自動化ツール

**プロジェクト名：** AutoShift_ver3  
**開発期間：** 2026年2月9日～  
**技術スタック：** Python / Flask / OR-Tools 9.8  

---

## プロジェクト概要

介護施設のシフト管理を自動化するWebアプリケーション。  
OR-Tools（Google Optimization Tools）を使用して、複雑なルール制約下での最適なシフト配置を自動生成します。

### コア機能

- ✅ **シフト自動作成** - OR-Tools最適化による月次シフト自動生成
- 🔴 **ルール管理画面** - 施設固有ルールの設定・編集
- 🔴 **希望休入力画面** - スタッフの希望休・有給申請入力
- 🔴 **シフト表示画面** - 生成されたシフトを表示、違反を色分け表示

---

## 完成状態（2026-02-09 18:00時点）

### ✅ 完成ファイル

**設計書：**
- DESIGN.md - 全体システム設計
- CONSTRAINT_DESIGN.md - OR-Tools制約モデル詳細
- NEXT_STEPS.md - 別PC作業ガイド

**データファイル：**
- data/staff_list.yml - スタッフ15名のマスタ
- data/rules.yml - 施設ルール16個 + 個人ルール10個 + 人間関係1個
- data/request_holidays_2026_02.yml - 2月の希望休・有給データ

**Pythonコード：**
- config.py - 設定ファイル
- models/__init__.py - データモデル（ShiftType, Staff, Rule等）
- app.py - Flaskアプリケーション基本フレーム
- requirements.txt - 依存パッケージ

**ユーティリティ：**
- convert_csv_to_yaml.py - CSV→YAMLコンバーター

### 🔴 未完成ファイル

**最適化エンジン（要実装）：**
- optimizer/solver.py - OR-Tools制約実装
- optimizer/constraints.py - ルール定義

**UI層（要実装）：**
- templates/facility_rules.html
- templates/request_holidays.html
- templates/shift_result.html
- static/css/style.css
- static/js/grid.js

**ユーティリティ（要実装）：**
- utils/yaml_handler.py - YAML読み書き
- routes/shift_generation.py - API実装

---

## ディレクトリ構成

```
AutoShift_ver3/
├── DESIGN.md                      ✅ 全体設計書
├── CONSTRAINT_DESIGN.md           ✅ 制約モデル設計
├── NEXT_STEPS.md                  ✅ 別PC作業ガイド
├── README.md                      ✅ このファイル
├── config.py                      ✅ 設定
├── app.py                         ✅ Flaskアプリ
├── requirements.txt               ✅ パッケージ
├── convert_csv_to_yaml.py         ✅ CSV変換スクリプト
│
├── data/
│   ├── staff_list.yml             ✅ スタッフマスタ
│   ├── rules.yml                  ✅ ルール定義
│   └── request_holidays_2026_02.yml ✅ 希望休・有給
│
├── models/
│   ├── __init__.py                ✅ データモデル
│   ├── shift.py                   🔴 未実装
│   └── constraint.py              🔴 未実装
│
├── optimizer/
│   ├── __init__.py                🔴 未実装
│   ├── solver.py                  🔴 未実装（最優先）
│   └── constraints.py             🔴 未実装（最優先）
│
├── routes/
│   ├── __init__.py                🔴 未実装
│   ├── facility_rules.py          🔴 未実装
│   ├── request_holidays.py        🔴 未実装
│   └── shift_result.py            🔴 未実装
│
├── utils/
│   ├── __init__.py                🔴 未実装
│   ├── yaml_handler.py            🔴 未実装（高優先）
│   └── validators.py              🔴 未実装
│
├── templates/
│   ├── base.html                  🔴 未実装
│   ├── facility_rules.html        🔴 未実装
│   ├── request_holidays.html      🔴 未実装
│   └── shift_result.html          🔴 未実装
│
└── static/
    ├── css/
    │   └── style.css              🔴 未実装
    └── js/
        ├── grid.js                🔴 未実装
        └── api.js                 🔴 未実装
```

---

## セットアップ手順

### 1. 環境構築

```bash
# 仮想環境作成
python -m venv venv

# 仮想環境有効化
venv\Scripts\activate  # Windows

# パッケージインストール
pip install -r requirements.txt
```

### 2. データファイル確認

```bash
# YAMLファイルが正しく配置されているか確認
ls data/
```

### 3. Flaskアプリ起動

```bash
python app.py
```

アクセス: http://localhost:5000

---

## 別PCでの作業指示

### 最優先（今すぐ実装）

1. **optimizer/solver.py** - ShiftOptimizer クラス実装
   - CONSTRAINT_DESIGN.md を参照
   - 変数定義、制約追加、目的関数構築
   - 推定時間：2-3時間

2. **optimizer/constraints.py** - ルール制約実装
   - FR001～FR016（施設ルール）
   - PR001～PR010（個人ルール）
   - RR001（人間関係ルール）
   - 推定時間：2-3時間

3. **utils/yaml_handler.py** - YAML読み書き
   - load_staff_list()
   - load_rules()
   - load_request_holidays()
   - 推定時間：1時間

### 次優先（その後）

4. **routes/shift_generation.py** - API実装
5. **templates/ + static/** - UI実装

### 参照文書

- **DESIGN.md** - 全体設計（概要・スキーマ）
- **CONSTRAINT_DESIGN.md** - 各ルールの実装方法（詳細）
- **NEXT_STEPS.md** - 実装フェーズガイド

---

## 実装チェックリスト

### Phase 1: 基本モデル層
- [x] models/__init__.py
- [ ] models/shift.py
- [x] utils/__init__.py
- [ ] utils/yaml_handler.py

### Phase 2: 最適化エンジン（最優先）
- [ ] optimizer/__init__.py
- [ ] optimizer/solver.py ⭐
- [ ] optimizer/constraints.py ⭐

### Phase 3: Flask API
- [ ] routes/__init__.py
- [ ] routes/shift_generation.py

### Phase 4: UI画面
- [ ] templates/base.html
- [ ] templates/shift_result.html
- [ ] static/css/style.css
- [ ] static/js/grid.js

---

## テスト実行

### 1. モデル層テスト

```bash
python -c "from models import Staff, ShiftType; print('Models OK')"
```

### 2. YAML読み込みテスト

```bash
python convert_csv_to_yaml.py
```

### 3. Flask起動テスト

```bash
python app.py
# http://localhost:5000 にアクセス
```

---

## 困ったときの参考

### OR-Tools の使用例

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()
x = model.NewIntVar(0, 10, 'x')
model.Add(x > 5)
solver = cp_model.CpSolver()
status = solver.Solve(model)
```

### YAML読み込み

```python
import yaml
with open('file.yml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
```

---

## サポート

- **チャット履歴：** このセッションのチャット全体を参照
- **設計書：** DESIGN.md + CONSTRAINT_DESIGN.md
- **実装ガイド：** NEXT_STEPS.md

---

**Last Updated:** 2026-02-09 18:00  
**Status:** 🟡 開発中（Phase 2実装段階）