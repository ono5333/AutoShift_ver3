# AutoShift - OR-Tools制約モデル設計書

**作成日：** 2026年2月9日  
**対象：** OR-Tools 9.8を使用した最適化エンジン実装  
**言語：** Python 3.10+

---

## 1. OR-Toolsモデルの全体構造

### 1.1 変数定義

**決定変数：** スタッフ i の日付 d における勤務区分 s

```
shift[staff_id, date] = 勤務区分（離散変数）
```

**定義域：**
- `staff_id` : 1-15（スタッフID）
- `date` : 2026-02-01 から 2026-02-28（日付）
- 勤務区分 s : {日勤, 夜勤, 夜勤明け, 公休, 希望休, 有給}

### 1.2 制約体系

| ランク | 制約種 | OR-Tools実装 | 優先度 |
|--------|--------|------------|--------|
| A | Hard Constraint | AddLinearConstraint() | 必ず満たす |
| B | Medium Constraint | 違反ペナルティ | 目的関数で最小化 |
| C | Soft Constraint | 目的関数の重み | 目的関数で最適化 |

---

## 2. 施設ルール制約（FR001-FR016）

### FR001: 夜勤は毎日2名配置 ✅ ランクA (Hard)

**制約内容：**  
毎日、夜勤シフト（「夜」）を持つスタッフが正確に2名

**OR-Tools実装：**

```python
for date in all_dates:
    night_shift_count = sum(
        shift[s, date] == ShiftType.NIGHT 
        for s in staff_ids
    )
    model.Add(night_shift_count == 2)
```

**違反時の処理：**
- ハード制約のため違反不可
- 満たせない場合は、可能な限り2に近い数を目指す（目的関数で調整）

---

### FR002: 日勤は毎日3名以上配置 ✅ ランクA (Hard)

**制約内容：**  
毎日、日勤シフト（「日」）を持つスタッフが3名以上

**OR-Tools実装：**

```python
for date in all_dates:
    day_shift_count = sum(
        shift[s, date] == ShiftType.DAY 
        for s in staff_ids
    )
    model.Add(day_shift_count >= 3)
```

---

### FR003: 月木のお風呂配置 ✅ ランクA (Hard)

**制約内容：**
- 月曜日・木曜日は「日勤」＋2名以上
- 月曜日・木曜日には「お風呂」職種が1名以上配置

**OR-Tools実装：**

```python
for date in all_dates:
    if date.weekday() in [0, 3]:  # 月=0, 木=3
        # 日勤3名確保（FR002と合わせて）
        day_count = sum(shift[s, date] == ShiftType.DAY for s in staff_ids)
        model.Add(day_count >= 3)
        
        # お風呂1名以上
        bath_count = sum(
            shift[s, date] == ShiftType.DAY 
            for s in staff_ids 
            if staff[s].class == "お風呂"
        )
        model.Add(bath_count >= 1)
```

---

### FR004-FR007: 月別公休数 ✅ ランクA/B (Hard/Medium)

**制約内容：**
- 1月：12日 (ランクB)
- 2月：8日 (ランクA)
- 3月～11月：9日 (ランクA)
- 12月：11日 (ランクB)

**OR-Tools実装（2月例）：**

```python
# 各スタッフの公休日数を計算
for staff_id in staff_ids:
    public_days = sum(
        shift[staff_id, date] in [ShiftType.PUBLIC_HOLIDAY, ShiftType.REQUEST_HOLIDAY]
        for date in all_dates_feb
    )
    model.Add(public_days == 8)  # 2月は8日
```

**ランク対応：**
- ランクA (2月)：ハード制約
- ランクB (1月/12月)：ソフト制約（違反ペナルティ付き）

---

### FR008: 希望休申請上限 ✅ ランクA (Hard)

**制約内容：**  
希望休申請は1スタッフあたり月3日以内

**OR-Tools実装：**

```python
for staff_id in staff_ids:
    request_count = len(staff_requests[staff_id])  # CSV/YAMLから取得
    if request_count > 3:
        print(f"警告: {staff_id}の希望休が3日を超えています")
    # YAMLの時点でチェック済みなので制約は不要
```

**注記：** YAMLデータ入力時にすでに制限されているため、制約は形式的

---

### FR009-FR010: 希望休・有給の扱い ✅ ランクA (Hard/Logic)

**制約内容：**
- 希望休：公休日数に含める
- 有給：公休日数に含めない（別計）

**OR-Tools実装：**

```python
for staff_id in staff_ids:
    # 公休日数の計算
    public_days = sum(
        shift[staff_id, date] in [ShiftType.PUBLIC_HOLIDAY, ShiftType.REQUEST_HOLIDAY]
        for date in all_dates
    )
    
    # 有給は別途カウント
    paid_days = sum(
        shift[staff_id, date] == ShiftType.PAID_HOLIDAY
        for date in all_dates
    )
    
    # 月別公休数に合わせる
    model.Add(public_days == expected_public_days[month])
```

---

### FR011: 日勤に介護士配置 ✅ ランクA (Hard)

**制約内容：**  
日勤には1名以上の「介護士」が必ず配置

**OR-Tools実装：**

```python
caregivers = [s for s in staff_ids if staff[s].class == "介護士"]

for date in all_dates:
    day_shift_caregivers = sum(
        shift[s, date] == ShiftType.DAY 
        for s in caregivers
    )
    model.Add(day_shift_caregivers >= 1)
```

---

### FR012: 夜勤明けは必須 ✅ ランクA (Hard)

**制約内容：**  
夜勤[夜]の次の日は必ず夜勤明け[明]とする

**OR-Tools実装：**

```python
for staff_id in staff_ids:
    for i, date in enumerate(all_dates[:-1]):
        next_date = all_dates[i + 1]
        
        # 今日が夜勤なら
        is_night = (shift[staff_id, date] == ShiftType.NIGHT)
        
        # 明日は夜勤明けにする
        is_next_day_off = (shift[staff_id, next_date] == ShiftType.NIGHT_SHIFT_OFF)
        
        # 論理制約: 夜勤なら → 翌日は明
        model.Add(is_night.OnlyEnforceIf(is_next_day_off))
```

**月跨ぎの対応：**
- 月末が「夜」の場合、次の月初が「明」になる前提で処理
- 月末「夜」で終了する場合、月初要件として「明」は不要

---

### FR013: 連続勤務の上限 ✅ ランクA (Hard)

**制約内容：**  
日勤の連続勤務は最大6日とする

**OR-Tools実装：**

```python
for staff_id in staff_ids:
    for i in range(len(all_dates) - 6):
        # 7日連続日勤チェック
        consecutive_days = sum(
            shift[staff_id, all_dates[i+j]] == ShiftType.DAY 
            for j in range(7)
        )
        model.Add(consecutive_days <= 6)  # 最大6日
```

---

### FR014: お風呂担当の配置 ✅ ランクB (Medium)

**制約内容：**  
月曜日・木曜日に「お風呂」職種を1名以上配置

**OR-Tools実装：**

```python
bath_staff = [s for s in staff_ids if staff[s].class == "お風呂"]

for date in all_dates:
    if date.weekday() in [0, 3]:  # 月=0, 木=3
        bath_count = sum(
            shift[s, date] == ShiftType.DAY 
            for s in bath_staff
        )
        model.Add(bath_count >= 1)
```

**ランク対応：** ソフト制約（違反ペナルティ付き）

---

### FR015: 勤務日数の計算 ✅ ランクB (Logic)

**制約内容：**  
月の日数 - 公休数 = 勤務日数

**OR-Tools実装：**

```python
for staff_id in staff_ids:
    total_days = len(all_dates)  # 28日
    public_days = sum(
        shift[staff_id, date] in [ShiftType.PUBLIC_HOLIDAY, ShiftType.REQUEST_HOLIDAY]
        for date in all_dates
    )
    working_days = sum(
        shift[staff_id, date] in [ShiftType.DAY, ShiftType.NIGHT, ShiftType.NIGHT_SHIFT_OFF]
        for date in all_dates
    )
    
    model.Add(working_days == total_days - public_days)
```

---

### FR016: 介護士の勤務日数平均化 ✅ ランクC (Soft)

**制約内容：**  
「介護士」の勤務日数をできるだけ平均化

**OR-Tools実装（目的関数で処理）：**

```python
caregivers = [s for s in staff_ids if staff[s].class == "介護士"]
working_days_per_caregiver = {}

for s in caregivers:
    working_days_per_caregiver[s] = sum(
        shift[s, date] in [ShiftType.DAY, ShiftType.NIGHT, ShiftType.NIGHT_SHIFT_OFF]
        for date in all_dates
    )

# 目的関数で分散を最小化
avg_working_days = sum(working_days_per_caregiver.values()) / len(caregivers)
variance_penalty = sum(
    abs(working_days_per_caregiver[s] - avg_working_days)
    for s in caregivers
)
```

---

## 3. 個人ルール制約（PR001-PR010）

### PR001-PR004: 夜勤不可 ✅ ランクA (Hard)

**対象スタッフ：**
- 山田志保里 (ID=1)
- 本庄正昇 (ID=11)
- タンダ (ID=12)
- メイガー (ID=13)

**OR-Tools実装：**

```python
no_night_staff = [1, 11, 12, 13]

for staff_id in no_night_staff:
    for date in all_dates:
        model.Add(shift[staff_id, date] != ShiftType.NIGHT)
```

---

### PR005: 日曜日は固定休 ✅ ランクB (Medium)

**対象：** 山田志保里 (ID=1)

**OR-Tools実装：**

```python
staff_id = 1

for date in all_dates:
    if date.weekday() == 6:  # 日曜日
        model.Add(
            shift[staff_id, date] in [ShiftType.PUBLIC_HOLIDAY, ShiftType.REQUEST_HOLIDAY]
        )
```

---

### PR006-PR008: 夜勤回数上限 ✅ ランクA (Hard)

**対象・上限：**
- 近藤由香利 (ID=4)：5回
- ソー (ID=9)：6回
- 田中賢輝 (ID=10)：6回

**OR-Tools実装：**

```python
night_shift_limits = {
    4: 5,
    9: 6,
    10: 6
}

for staff_id, max_count in night_shift_limits.items():
    night_count = sum(
        shift[staff_id, date] == ShiftType.NIGHT
        for date in all_dates
    )
    model.Add(night_count <= max_count)
```

---

### PR009: 夜勤明けは公休 ✅ ランクA (Hard)

**対象：** 田中賢輝 (ID=10)

**OR-Tools実装：**

```python
staff_id = 10

for i in range(len(all_dates) - 1):
    date = all_dates[i]
    next_date = all_dates[i + 1]
    
    # 今日が夜勤明けなら
    is_night_shift_off = (shift[staff_id, date] == ShiftType.NIGHT_SHIFT_OFF)
    
    # 明日は公休
    is_next_day_holiday = (
        shift[staff_id, next_date] in [ShiftType.PUBLIC_HOLIDAY, ShiftType.REQUEST_HOLIDAY]
    )
    
    model.Add(is_night_shift_off.OnlyEnforceIf(is_next_day_holiday))
```

---

## 4. 人間関係ルール（RR001）

### RR001: 同日夜勤不可 ✅ ランクA (Hard)

**対象：** 田中賢輝 (ID=10) と 斎藤明音 (ID=6)

**制約内容：**  
この2名は同日に夜勤に入ることはできない

**OR-Tools実装：**

```python
staff_a, staff_b = 10, 6

for date in all_dates:
    # 同日夜勤を禁止
    is_a_night = (shift[staff_a, date] == ShiftType.NIGHT)
    is_b_night = (shift[staff_b, date] == ShiftType.NIGHT)
    
    # 同時に夜勤になるのを禁止
    model.Add(is_a_night + is_b_night <= 1)
```

---

## 5. 希望休制約

### 希望休の優先度 ✅ ランクA (Hard)

**制約内容：**  
YAMLの `request_holidays_2026_02.yml` に記載された希望休・有給は、可能な限り尊重

**OR-Tools実装：**

```python
for staff_id in staff_ids:
    for request in staff_requests[staff_id]:
        date = request['date']
        request_type = request['type']
        
        if request_type == '希':  # 希望休
            # 希望休を優先
            model.Add(
                shift[staff_id, date] == ShiftType.REQUEST_HOLIDAY
            )
        elif request_type == '有':  # 有給
            # 有給を優先
            model.Add(
                shift[staff_id, date] == ShiftType.PAID_HOLIDAY
            )
```

**違反時の優先度：**
- ランクA制約 > 希望休
- 全体のランクA制約を満たすため、やむを得ず希望休を破ることもある

---

## 6. 目的関数（Objective）

### 6.1 目的関数の構成

```
最小化: 
  ペナルティ_ランクB + ペナルティ_ランクC + 分散ペナルティ
```

### 6.2 ランクB違反ペナルティ

| ルール | ペナルティ重み |
|--------|-------------|
| FR004 (1月公休) | 100 |
| FR007 (12月公休) | 100 |
| FR014 (お風呂配置) | 50 |
| PR005 (日曜休) | 80 |

### 6.3 ランクC最適化

| ルール | 重み |
|--------|------|
| FR016 (介護士平均化) | 10 |

### 6.4 実装例

```python
def build_objective(model, shift, staff_ids, all_dates):
    objective = 0
    
    # ランクB違反ペナルティ
    # 1月公休不足時のペナルティ（今は2月なので不要）
    
    # ランクC最適化（介護士の勤務日数平均化）
    caregivers = [s for s in staff_ids if staff[s].class == "介護士"]
    if caregivers:
        working_days = []
        for s in caregivers:
            days = sum(
                shift[s, date] in [ShiftType.DAY, ShiftType.NIGHT, ShiftType.NIGHT_SHIFT_OFF]
                for date in all_dates
            )
            working_days.append(days)
        
        avg_days = sum(working_days) / len(caregivers)
        variance = sum((d - avg_days) ** 2 for d in working_days)
        objective += 10 * variance
    
    model.Minimize(objective)
```

---

## 7. 勤務区分の定義

```python
class ShiftType(Enum):
    DAY = 0              # 日勤
    NIGHT = 1            # 夜勤
    NIGHT_SHIFT_OFF = 2  # 夜勤明け
    PUBLIC_HOLIDAY = 3   # 公休
    REQUEST_HOLIDAY = 4  # 希望休
    PAID_HOLIDAY = 5     # 有給
```

---

## 8. ソルバー設定

### 8.1 CP-SAT Solverの設定

```python
from ortools.sat.python import cp_model

model = cp_model.CpModel()
solver = cp_model.CpSolver()

# ソルバーパラメータ
solver.parameters.max_time_in_seconds = 60.0  # タイムアウト60秒
solver.parameters.num_workers = 4  # マルチスレッド化

status = solver.Solve(model)
```

### 8.2 結果の解釈

| Status | 意味 |
|--------|------|
| OPTIMAL | 最適解が見つかった |
| FEASIBLE | 可行解が見つかった（最適でない） |
| INFEASIBLE | 解が見つからない |
| MODEL_INVALID | モデルが無効 |

---

## 9. 違反の可視化ルール

### 9.1 ルール違反の検出

実装後、以下のルールを画面に色分け表示：

```python
def check_violations(shift_result, staff_id, date):
    violations = []
    
    # ランクA違反をチェック
    if is_rank_a_violation(shift_result, staff_id, date):
        violations.append(('A', rule_id, description))
    
    # ランクB違反をチェック
    if is_rank_b_violation(shift_result, staff_id, date):
        violations.append(('B', rule_id, description))
    
    return violations
```

### 9.2 色分け表示

| 違反ランク | セル背景色 |
|-----------|----------|
| A | 赤 (#FF6B6B) |
| B | ピンク (#FFB3BA) |
| 通常 | 白 (#FFFFFF) |

---

## 10. 実装チェックリスト

- [ ] 変数定義（shift[staff_id, date]）
- [ ] ランクA制約実装（11個）
- [ ] ランクB制約実装（3個）
- [ ] ランクC制約実装（1個）
- [ ] 目的関数構築
- [ ] ソルバー実行
- [ ] 結果検証
- [ ] 違反検出ロジック
- [ ] 違反の色分け表示

---

**次：Python実装フェーズ → models/ および optimizer/ ディレクトリにコード作成開始**
