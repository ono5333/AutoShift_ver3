# 日本語対応について / Japanese Language Support

## 概要 / Overview

AutoShift アプリケーションは完全な日本語対応を実装しています。
The AutoShift application has full Japanese language support implemented.

## 実装内容 / Implementation Details

### 1. JSON API レスポンス / JSON API Responses

Flask の JSON エンコーダーを設定し、日本語文字を読みやすい形式で出力します。

```python
app = Flask(__name__)
app.json.ensure_ascii = False  # 日本語を読みやすく表示
```

**実装前 (Before):**
```json
{"name": "\u5c71\u7530\u5fd7\u4fdd\u91cc", "message": "\u30b7\u30d5\u30c8\u4f5c\u6210\u5b8c\u4e86"}
```

**実装後 (After):**
```json
{"name": "山田志保里", "message": "シフト作成完了"}
```

### 2. YAML ファイル / YAML Files

すべてのデータファイルは UTF-8 エンコーディングで保存され、正しく読み込まれます。

All data files are stored in UTF-8 encoding and are loaded correctly:

- `data/staff_list.yml` - スタッフマスタ
- `data/rules.yml` - ルール定義
- `data/request_holidays_2026_02.yml` - 希望休・有給データ

```python
with open('data/staff_list.yml', 'r', encoding='utf-8') as f:
    staff_data = yaml.safe_load(f)
```

### 3. データモデル / Data Models

すべてのデータモデルは日本語テキストを正しく処理します。

All data models handle Japanese text correctly:

```python
from models import Staff

staff = Staff(id=1, name='山田志保里', staff_class='介護士')
```

### 4. コンソール出力 / Console Output

Python のデフォルトエンコーディングは UTF-8 であり、日本語が正しく表示されます。

Python's default encoding is UTF-8, ensuring Japanese text displays correctly:

```
==================================================
AutoShift - シフト自動化ツール
==================================================
```

## テスト / Testing

日本語対応をテストするには:

To test Japanese language support:

```bash
python test_japanese_support.py
```

デモを実行するには:

To run the demonstration:

```bash
python demo_japanese_support.py
```

## 技術仕様 / Technical Specifications

- **Python バージョン**: 3.12.3
- **デフォルトエンコーディング**: UTF-8
- **Flask バージョン**: 3.1.2
- **YAML ファイルエンコーディング**: UTF-8
- **JSON 出力**: `ensure_ascii=False`

## トラブルシューティング / Troubleshooting

### 文字化けが発生する場合

If you experience garbled text:

1. ファイルが UTF-8 で保存されているか確認
   - Ensure files are saved in UTF-8 encoding

2. Python の環境変数を確認
   - Check Python environment variables:
   ```bash
   python -c "import sys; print(sys.getdefaultencoding())"
   ```
   出力は "utf-8" であるべき / Should output "utf-8"

3. Flask の設定を確認
   - Verify Flask configuration:
   ```python
   print(app.json.ensure_ascii)  # Should be False
   ```

## 参考資料 / References

- [Flask JSON Support](https://flask.palletsprojects.com/en/3.0.x/api/#flask.json.provider.DefaultJSONProvider)
- [Python UTF-8 Mode](https://docs.python.org/3/library/os.html#utf8-mode)
- [YAML and Unicode](https://yaml.org/spec/1.2/spec.html#id2771184)

---

**最終更新 / Last Updated**: 2026-02-12  
**ステータス / Status**: ✅ 完了 / Complete
