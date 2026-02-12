"""
日本語対応テスト
Japanese language support test
"""

import json
import yaml
from pathlib import Path

def test_yaml_loading():
    """YAMLファイルから日本語データを正しく読み込めるかテスト"""
    print("=" * 50)
    print("Test 1: YAML ファイルの日本語読み込み")
    print("=" * 50)
    
    # スタッフリストの読み込み
    with open('data/staff_list.yml', 'r', encoding='utf-8') as f:
        staff_data = yaml.safe_load(f)
    
    print(f"スタッフ数: {len(staff_data['staff'])}名")
    for staff in staff_data['staff'][:3]:
        print(f"  - {staff['name']} ({staff['class']})")
    
    assert staff_data['staff'][0]['name'] == '山田志保里'
    assert staff_data['staff'][0]['class'] == '介護士'
    print("✓ YAML読み込みテスト成功\n")

def test_json_encoding():
    """JSON出力で日本語が正しく表示されるかテスト"""
    print("=" * 50)
    print("Test 2: JSON エンコーディング")
    print("=" * 50)
    
    data = {
        'name': '山田志保里',
        'message': 'シフト自動作成を実行しました',
        'class': '介護士',
        'rules': ['夜勤は月7回まで', '連続勤務は5日まで']
    }
    
    # ensure_ascii=False で日本語を読みやすく表示
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    print("JSON出力:")
    print(json_str)
    
    # 日本語文字が含まれているか確認
    assert '山田志保里' in json_str
    assert 'シフト自動作成' in json_str
    assert '\\u' not in json_str  # Unicode エスケープシーケンスがないことを確認
    print("✓ JSONエンコーディングテスト成功\n")

def test_flask_json():
    """FlaskアプリケーションのJSON出力で日本語が正しく表示されるかテスト"""
    print("=" * 50)
    print("Test 3: Flask JSON 出力")
    print("=" * 50)
    
    from flask import Flask, jsonify
    
    app = Flask(__name__)
    app.json.ensure_ascii = False
    
    with app.test_request_context():
        response = jsonify({
            'status': 'success',
            'message': 'シフトを作成しました',
            'staff_name': '佐藤美幸',
            'shift_type': '夜勤'
        })
        
        json_data = response.get_data(as_text=True)
        print("Flask JSONレスポンス:")
        print(json_data)
        
        # 日本語が含まれているか確認
        assert 'シフトを作成しました' in json_data
        assert '佐藤美幸' in json_data
        assert '夜勤' in json_data
        print("✓ Flask JSONテスト成功\n")

def test_models_with_japanese():
    """データモデルで日本語が正しく扱えるかテスト"""
    print("=" * 50)
    print("Test 4: データモデルでの日本語処理")
    print("=" * 50)
    
    from models import Staff, Rule, RequestHoliday
    from dataclasses import asdict
    
    # スタッフオブジェクト作成
    staff = Staff(id=1, name='山田志保里', staff_class='介護士')
    print(f"スタッフ: {staff}")
    
    # ルールオブジェクト作成
    rule = Rule(
        id='FR001',
        rank='A',
        title='夜勤回数制限',
        description='1ヶ月の夜勤回数は7回まで',
        rule_type='facility'
    )
    print(f"ルール: {rule.title} - {rule.description}")
    
    # 希望休オブジェクト作成
    request = RequestHoliday(
        staff_id=1,
        date='2026-02-15',
        request_type='希'
    )
    print(f"希望休: スタッフID {request.staff_id} - {request.date} ({request.request_type})")
    
    # JSONシリアライズ
    staff_dict = asdict(staff)
    staff_json = json.dumps(staff_dict, ensure_ascii=False)
    assert '山田志保里' in staff_json
    assert '介護士' in staff_json
    print("✓ データモデルテスト成功\n")

def test_console_output():
    """コンソール出力で日本語が正しく表示されるかテスト"""
    print("=" * 50)
    print("Test 5: コンソール出力")
    print("=" * 50)
    
    messages = [
        'AutoShift - シフト自動化ツール',
        'シフト作成を開始します...',
        '処理が完了しました',
        'スタッフ: 山田志保里 (介護士)',
        '夜勤: 7回, 公休: 8回'
    ]
    
    for msg in messages:
        print(f"  {msg}")
    
    print("✓ コンソール出力テスト成功\n")

if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("日本語対応テスト実行")
    print("Japanese Language Support Test")
    print("=" * 50 + "\n")
    
    try:
        test_yaml_loading()
        test_json_encoding()
        test_flask_json()
        test_models_with_japanese()
        test_console_output()
        
        print("=" * 50)
        print("✓ すべてのテストが成功しました！")
        print("✓ All tests passed!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
