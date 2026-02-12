"""
日本語対応デモンストレーション
Japanese Support Demonstration

このスクリプトは、日本語対応の実装前後の違いを示します。
"""

import json
from flask import Flask, jsonify

def demo_before():
    """実装前: ensure_ascii=True (デフォルト)"""
    print("=" * 60)
    print("【実装前】 Before: Default Flask behavior")
    print("=" * 60)
    
    app = Flask(__name__)
    # ensure_ascii は True がデフォルト (日本語がエスケープされる)
    
    data = {
        'status': 'success',
        'message': 'シフト自動作成を実行しました',
        'staff': [
            {'name': '山田志保里', 'class': '介護士'},
            {'name': '佐藤美幸', 'class': '介護士'},
            {'name': '田中茂子', 'class': '介護士'}
        ]
    }
    
    with app.test_request_context():
        response = jsonify(data)
        json_output = response.get_data(as_text=True)
        print(json_output)
        print("\n問題点: 日本語がUnicodeエスケープシーケンス (\\uXXXX) で表示されている")
        print("        人間には読みづらく、デバッグやログ確認が困難\n")

def demo_after():
    """実装後: ensure_ascii=False"""
    print("=" * 60)
    print("【実装後】 After: With Japanese support")
    print("=" * 60)
    
    app = Flask(__name__)
    app.json.ensure_ascii = False  # ← この1行を追加
    
    data = {
        'status': 'success',
        'message': 'シフト自動作成を実行しました',
        'staff': [
            {'name': '山田志保里', 'class': '介護士'},
            {'name': '佐藤美幸', 'class': '介護士'},
            {'name': '田中茂子', 'class': '介護士'}
        ]
    }
    
    with app.test_request_context():
        response = jsonify(data)
        json_output = response.get_data(as_text=True)
        # 見やすく整形して表示
        parsed = json.loads(json_output)
        formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
        print(formatted)
        print("\n✓ 改善点: 日本語がそのまま表示される")
        print("          読みやすく、デバッグやログ確認が容易\n")

def show_comparison():
    """比較表示"""
    print("\n" + "=" * 60)
    print("【比較】 Comparison")
    print("=" * 60)
    
    print("\n実装前 (Before):")
    print('  {"name": "\\u5c71\\u7530\\u5fd7\\u4fdd\\u91cc"}')
    print('  ↑ 何が書いてあるか分からない')
    
    print("\n実装後 (After):")
    print('  {"name": "山田志保里"}')
    print('  ↑ 一目で分かる！')
    
    print("\n" + "=" * 60)
    print("変更内容: app.py に1行追加")
    print("=" * 60)
    print("""
    app = Flask(__name__)
    app.json.ensure_ascii = False  # ← この1行を追加
    """)

if __name__ == '__main__':
    print("\n")
    print("*" * 60)
    print("  AutoShift - 日本語対応デモンストレーション")
    print("  Japanese Language Support Demonstration")
    print("*" * 60)
    print()
    
    demo_before()
    demo_after()
    show_comparison()
    
    print("\n✓ 日本語対応が完了しました！")
    print("✓ Japanese language support is now enabled!")
    print()
