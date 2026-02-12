"""
AutoShift - Flaskアプリケーション
2026年2月9日
"""

from flask import Flask, jsonify, request
from pathlib import Path
import sys

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent))

import config

app = Flask(__name__)

# 日本語対応: JSONレスポンスで日本語を正しく表示
app.json.ensure_ascii = False

# ====================
# エンドポイント
# ====================

@app.route('/', methods=['GET'])
def index():
    """ホームページ"""
    return jsonify({
        'status': 'ok',
        'message': 'AutoShift API Server',
        'version': '1.0.0'
    })

@app.route('/api/shift/generate', methods=['POST'])
def generate_shift():
    """
    シフト自動作成
    
    POST /api/shift/generate
    Body: {
        "month": "2026-02",
        "year": 2026,
        "month_num": 2
    }
    """
    try:
        data = request.json or {}
        month = data.get('month', '2026-02')
        
        # TODO: ShiftOptimizerを呼び出す
        # optimizer = ShiftOptimizer(month)
        # status, result = optimizer.solve()
        
        return jsonify({
            'status': 'success',
            'message': 'シフト自動作成を実行しました',
            'data': {
                'month': month,
                'shifts': {},  # TODO: 結果を追加
                'violations': []  # TODO: 違反情報を追加
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/shift/result/<month>', methods=['GET'])
def get_shift_result(month):
    """
    シフト結果取得
    GET /api/shift/result/2026-02
    """
    try:
        # TODO: 保存済みシフト結果を読み込む
        return jsonify({
            'status': 'success',
            'data': {
                'month': month,
                'shifts': {},
                'violations': []
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/rules', methods=['GET'])
def get_rules():
    """
    ルール一覧取得
    GET /api/rules
    """
    try:
        # TODO: rules.yml を読み込む
        return jsonify({
            'status': 'success',
            'data': {
                'facility_rules': [],
                'personal_rules': [],
                'relationship_rules': []
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@app.route('/api/staff', methods=['GET'])
def get_staff():
    """
    スタッフ一覧取得
    GET /api/staff
    """
    try:
        # TODO: staff_list.yml を読み込む
        return jsonify({
            'status': 'success',
            'data': {
                'staff': []
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

# ====================
# エラーハンドラ
# ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'message': 'Not Found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Internal Server Error'
    }), 500

# ====================
# アプリ起動
# ====================

if __name__ == '__main__':
    print("="*50)
    print("AutoShift - シフト自動化ツール")
    print("="*50)
    print(f"Flask Server starting on {config.FLASK_CONFIG['HOST']}:{config.FLASK_CONFIG['PORT']}")
    print(f"Access: http://localhost:{config.FLASK_CONFIG['PORT']}")
    print("="*50)
    
    app.run(
        host=config.FLASK_CONFIG['HOST'],
        port=config.FLASK_CONFIG['PORT'],
        debug=config.FLASK_CONFIG['DEBUG']
    )
