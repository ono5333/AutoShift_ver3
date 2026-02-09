# AutoShift シフト自動化ツール - システム設計書

**作成日：** 2026年2月9日  
**プロジェクト名：** AutoShift_ver3  
**技術スタック：** Python 3.10+ / Flask / OR-Tools 9.8

---

## 1. プロジェクト概要

介護施設のシフト管理を自動化するツール。  
施設ルール + 個人ルール + 希望休を制約条件として、OR-Tools（Google Optimization Tools）で最適なシフト自動作成を実現。

---

## 2. 技術スタック（確定）

| 項目 | 選択 |
|------|------|
| バックエンド | Python 3.10+ |
| Webフレームワーク | Flask |
| 最適化エンジン | OR-Tools 9.8 |
| フロントエンド | HTML5 / CSS3 / JavaScript |
| データ保持 | YAML |
| 環境 | ローカルオンプレミス（localhost:5000） |
| 展開形態 | ブラウザ画面 |

---

## 3. データ構造定義（YMLスキーマ）

### 3.1 スタッフ一覧 (`staff_list.yml`)

**用途：** スタッフマスタ。基本固定。  
**更新頻度：** 低い（追加時のみ、後で機能化）  
**構造：**

```yaml
staff:
  - id: 1
    name: "山田志保里"
    class: "介護士"
  - id: 2
    name: "佐藤美幸"
    class: "介護士"
  - id: 3
    name: "田中茂子"
    class: "介護士"
  - id: 4
    name: "近藤由香利"
    class: "介護士"
  - id: 5
    name: "福島瑞穂"
    class: "介護士"
  - id: 6
    name: "斎藤明音"
    class: "介護士"
  - id: 7
    name: "是枝久枝"
    class: "介護士"
  - id: 8
    name: "木村洋二"
    class: "介護士"
  - id: 9
    name: "ソー"
    class: "初級介護士"
  - id: 10
    name: "田中賢輝"
    class: "介護士"
  - id: 11
    name: "本庄正昇"
    class: "初級介護士"
  - id: 12
    name: "タンダ"
    class: "初級介護士"
  - id: 13
    name: "メイガー"
    class: "初級介護士"
  - id: 14
    name: "大野正恵"
    class: "お風呂"
  - id: 15
    name: "大上迫"
    class: "お風呂"
```

---

### 3.2 希望休み一覧 (`request_holidays_{YYYY}_{MM}.yml`)

**用途：** 月ごとの希望休・有給入力。  
**更新頻度：** 月ごと（新規作成）  
**ファイル名例：** `request_holidays_2026_02.yml`  
**構造：**

```yaml
month: "2026-02"
staff_requests:
  - staff_id: 1
    staff_name: "山田志保里"
    requests:
      - date: "2026-02-03"
        type: "希"  # 希:希望休, 有:有給
      - date: "2026-02-10"
        type: "希"
      - date: "2026-02-17"
        type: "有"
  - staff_id: 2
    staff_name: "佐藤美幸"
    requests: []
  # ... 全15名分
```

**type の値：**
- `希` ：希望休（公休日数に含まれる）
- `有` ：有給（公休日数に含まれない）
- 空白：申請なし

---

### 3.3 ルール一覧 (`rules.yml`)

**用途：** 施設ルール、個人ルール、人間関係制約。  
**更新頻度：** 基本固定（管理画面で編集可能）  
**構造：**

```yaml
rules:
  facility_rules:
    - id: "FR001"
      rank: "A"
      title: "夜勤は毎日2名配置"
      description: "毎日22時以降の夜勤シフトには必ず2名のスタッフを配置する"
    - id: "FR002"
      rank: "A"
      title: "日勤は毎日3名以上配置"
      description: "毎日日勤シフトには3名以上のスタッフを配置する"
    - id: "FR003"
      rank: "A"
      title: "月木のお風呂配置"
      description: "月曜日・木曜日は日勤+2名配置+お風呂1名"
    - id: "FR004"
      rank: "B"
      title: "1月の公休"
      description: "1月の公休数は12日"
      month: 1
      days: 12
    - id: "FR005"
      rank: "A"
      title: "2月の公休"
      description: "2月の公休数は8日"
      month: 2
      days: 8
    - id: "FR006"
      rank: "A"
      title: "3月～11月の公休"
      description: "3月～11月の公休数は9日"
      month: [3, 4, 5, 6, 7, 8, 9, 10, 11]
      days: 9
    - id: "FR007"
      rank: "B"
      title: "12月の公休"
      description: "12月の公休数は11日"
      month: 12
      days: 11
    - id: "FR008"
      rank: "A"
      title: "希望休申請上限"
      description: "希望休は各月3日以内に限定"
      max_requests: 3
    - id: "FR009"
      rank: "A"
      title: "希望休は公休に含まれる"
      description: "希望休は公休を指定できる制度なので日数としては公休数に含まれる"
    - id: "FR010"
      rank: "A"
      title: "有給は別計"
      description: "有給は公休・希望休とは別に取得するものなので公休数には含めない"
    - id: "FR011"
      rank: "A"
      title: "日勤に介護士配置"
      description: "日勤には1名以上の『介護士』が必ず配置されること"
    - id: "FR012"
      rank: "A"
      title: "夜勤明けは必須"
      description: "夜勤[夜]の次の日は必ず夜勤明け[明]とする"
    - id: "FR013"
      rank: "A"
      title: "連続勤務の上限"
      description: "日勤の連続勤務は最大6日とする"
      max_consecutive_days: 6
    - id: "FR014"
      rank: "B"
      title: "お風呂担当の配置"
      description: "『お風呂担当』は月と木に1名以上配置する"
      days: [1, 4]  # 1=月, 4=木
    - id: "FR015"
      rank: "B"
      title: "勤務日数の計算"
      description: "月の日数 - 公休数の日数分勤務を割り当てる"
    - id: "FR016"
      rank: "C"
      title: "介護士の勤務日数平均化"
      description: "『介護士』の勤務日数を平均化する"

  personal_rules:
    - id: "PR001"
      rank: "A"
      staff_id: 1
      staff_name: "山田志保里"
      title: "夜勤不可"
      description: "夜勤に入ることはできない"
      constraint_type: "no_night_shift"
    - id: "PR002"
      rank: "A"
      staff_id: 11
      staff_name: "本庄正昇"
      title: "夜勤不可"
      constraint_type: "no_night_shift"
    - id: "PR003"
      rank: "A"
      staff_id: 12
      staff_name: "タンダ"
      title: "夜勤不可"
      constraint_type: "no_night_shift"
    - id: "PR004"
      rank: "A"
      staff_id: 13
      staff_name: "メイガー"
      title: "夜勤不可"
      constraint_type: "no_night_shift"
    - id: "PR005"
      rank: "B"
      staff_id: 1
      staff_name: "山田志保里"
      title: "日曜日は固定休"
      description: "日曜日は必ず休みとする"
      constraint_type: "fixed_day_off"
      day_of_week: 0  # 0=日, 1=月, ..., 6=土
    - id: "PR006"
      rank: "A"
      staff_id: 4
      staff_name: "近藤由香利"
      title: "夜勤回数上限"
      description: "夜勤回数は月5回まで"
      constraint_type: "max_night_shifts"
      max_count: 5
    - id: "PR007"
      rank: "A"
      staff_id: 9
      staff_name: "ソー"
      title: "夜勤回数上限"
      description: "夜勤回数は月6回まで"
      constraint_type: "max_night_shifts"
      max_count: 6
    - id: "PR008"
      rank: "A"
      staff_id: 10
      staff_name: "田中賢輝"
      title: "夜勤回数上限"
      description: "夜勤回数は月6回まで"
      constraint_type: "max_night_shifts"
      max_count: 6
    - id: "PR009"
      rank: "A"
      staff_id: 10
      staff_name: "田中賢輝"
      title: "夜勤明けは公休"
      description: "夜勤明け[明]の次の日は必ず公休[休]とする"
      constraint_type: "day_off_after_night_shift"
    - id: "PR010"
      rank: "A"
      staff_id: 1
      staff_name: "山田志保里"
      title: "備考"
      description: "その他備考があればここに記入"

  relationship_rules:
    - id: "RR001"
      rank: "A"
      staff_ids: [10, 6]
      staff_names: ["田中賢輝", "斎藤明音"]
      title: "同日夜勤不可"
      description: "この2名は同日に夜勤に入ることはできない"
      constraint_type: "cannot_work_together"
      shift_type: "夜"
```

---

## 4. 勤務区分（マスタ定義）

| 区分 | コード | 説明 |
|------|--------|------|
| 日勤 | 日 | 8:00-17:00 |
| 夜勤 | 夜 | 22:00-翌8:00 |
| 夜勤明け | 明 | 翌日9:00-17:00（夜勤の翌日のみ） |
| 公休 | 休 | 休み |
| 希望休 | 希 | 希望による休み（公休に含まれる） |
| 有給 | 有 | 有給休暇（公休に含まれない） |

---

## 5. ルール優先度とランク定義

### ランク定義

| ランク | 名称 | 定義 | OR-Tools対応 |
|--------|------|------|-----------|
| A | 絶対順守 | 必ず守る | Hard Constraint（違反不可） |
| B | 基本順守 | 基本的に守る | Medium Constraint（ペナルティ付き） |
| C | 努力目標 | 可能なら調整 | Soft Constraint（目的関数の重み） |

### 制約解釈

- **ランクA：** ハード制約。違反不可。ただし全ルール同時達成不可な場合は、できるだけ満たす。
- **ランクB：** ソフト制約。ランクAを守った上で、違反ペナルティを付けて最小化。
- **ランクC：** 目的関数に組み込み、ランクA/Bを守った上で最適化。

---

## 6. 月跨ぎ処理仕様

### ポリシー

1. **各月は独立最適化** → 1月と2月のシフトは別々に作成
2. **月初の「明」対応** → 月1日が「明」になる場合、月末の「夜」から2ルール
3. **ルール順守時の対象外** → 月末「夜」が無い場合、月初「明」の要求はしない

### 処理フロー

```
1. シフト作成ボタン押下（例：2月分）
2. OR-Tools設定：2月1日～2月28日（または29日）
3. 初日が「明」でない限定条件
4. 最終日が「夜」の場合も、その後「明」が無い前提で処理
5. 結果を画面Gridに反映
```

---

## 7. 画面仕様

### 7.1 施設ルール設定画面

**用途：** ルール一覧の確認・編集  
**更新頻度：** 低い（基本設定段階のみ）  
**UI要素：**

- **ルール表示Grid：**
  - 列：ID / ランク / タイトル / 説明 / アクション
  - 行ソート可能
  - ランクごとに色分け（A:赤, B:橙, C:黄）

- **操作ボタン：**
  - 「ルール追加」→ 新規入力ダイアログ
  - 「ルール削除」→ 選択行削除（確認ダイアログ）
  - 「編集」→ 選択行を編集モード
  - 「保存」→ `rules.yml` に反映

- **編集フォーム：**
  - ID, ランク, タイトル, 説明, 制約タイプ, パラメータなど

---

### 7.2 希望休み入力画面

**用途：** 月ごとの希望休・有給申請  
**更新頻度：** 毎月

**UI要素：**

- **ヘッダ：**
  - 月選択ドロップダウン（2026年2月など）
  - 「保存」「新規作成」「削除」ボタン

- **希望休Gridレイアウト：**
  - 行：スタッフ名（15名）
  - 列：日付（月初～月末）
  - セル内容：空白 / 「希」/ 「有」

- **セルのクリック動作：**
  - クリックで「空白→希→有→空白」をローテーション
  - 背景色で区別（希：水色, 有：黄色）

- **保存処理：**
  - `request_holidays_{YYYY}_{MM}.yml` に記録

---

### 7.3 シフト自動作成・表示画面

**用途：** シフト最適化と結果表示  
**更新頻度：** 毎月（保存後は固定）

**UI要素：**

- **ヘッダ：**
  - 月選択ドロップダウン
  - 「シフト自動作成」ボタン（OR-Tools実行）
  - 「保存」「削除」「Excel出力（Level UP項目）」ボタン

- **シフト表示Grid：**
  - 行：スタッフ名（15名）
  - 列：日付（月初～月末）
  - セル：勤務区分（日/夜/明/休/希/有）
  - セル背景色：
    - **通常：** 白（日）/ 紫（夜）/ 黄（明）/ 灰（休） / 水（希） / 黄（有）
    - **ランクA違反：** 赤背景
    - **ランクB違反：** ピンク背景

- **違反情報パネル：**
  - 違反ルール一覧を表示
  - 例：「ルールID: FR002 - 日勤3名未満 (2月3日)」
  - ランク別に色分け

- **処理時間表示：**
  - OR-Tools実行時間（秒単位）

---

## 8. ディレクトリ構成（予定）

```
AutoShift_ver3/
├── app.py                           # Flaskアプリのエントリポイント
├── requirements.txt                 # Python依存パッケージ
├── config.py                        # 設定ファイル
│
├── data/                            # データファイル保存先
│   ├── staff_list.yml               # スタッフマスタ
│   ├── rules.yml                    # ルール定義
│   └── request_holidays_YYYY_MM.yml # 月別希望休み
│
├── models/                          # データモデル
│   ├── __init__.py
│   ├── staff.py
│   ├── rule.py
│   ├── shift.py
│   └── constraint.py
│
├── optimizer/                       # OR-Tools最適化エンジン
│   ├── __init__.py
│   ├── solver.py                    # メイン最適化ロジック
│   └── constraints.py               # 制約定義
│
├── routes/                          # Flaskルート（画面遷移）
│   ├── __init__.py
│   ├── facility_rules.py            # 施設ルール画面
│   ├── request_holidays.py          # 希望休み入力画面
│   └── shift_result.py              # シフト表示画面
│
├── utils/                           # ユーティリティ
│   ├── __init__.py
│   ├── yaml_handler.py              # YAML読み書き
│   └── validators.py                # データ検証
│
├── templates/                       # HTMLテンプレート
│   ├── base.html
│   ├── facility_rules.html
│   ├── request_holidays.html
│   └── shift_result.html
│
├── static/                          # CSS/JS
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── grid.js                  # Grid操作
│       └── api.js                   # API呼び出し
│
└── DESIGN.md                        # このファイル
```

---

## 9. 開発フェーズ

### Phase 1: データモデル + 基本CRUD
- YMLファイル読み書き
- スタッフ、ルール、希望休みの管理

### Phase 2: OR-Tools統合
- 制約モデル実装
- ランクA/B/C対応
- 最適化ロジック

### Phase 3: UI実装
- Flask ルート + HTML/JS
- Gridコンポーネント
- リアルタイム反映

### Phase 4: 整合性テスト
- ルール遵守検証
- エッジケース確認（月跨ぎ等）

### Phase 5: 画面デバッグ
- ラウンドトリップテスト
- 違反表示確認

---

## 10. セットアップ手順（後日作成）

```bash
# 1. 環境構築
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. 初期データ作成
# data/staff_list.yml, rules.yml を手動配置

# 3. アプリ起動
python app.py

# 4. ブラウザアクセス
# http://localhost:5000
```

---

## 11. 今後の検討項目（Level UP）

- [ ] スタッフマスタ追加/削除機能
- [ ] ルール追加/削除機能
- [ ] Excel出力
- [ ] PDF帳票出力
- [ ] シフト履歴管理
- [ ] 集計レポート
- [ ] 複数施設対応
- [ ] Web版へのアップグレード（AWS等）
- [ ] ユーザー認証
- [ ] 多言語対応

---

**以上、設計フェーズを完了。**  
**次は YMLサンプルファイル作成 → OR-Tools制約設計 → 実装フェーズへ進行。**
