"""
AutoShift - Flaskアプリケーション
2026年2月9日
"""

from flask import Flask, jsonify, request, render_template
from pathlib import Path
import sys

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent))

import config

# Blueprintインポート
from routes import shift_generation_bp
from routes.facility_rules import facility_rules_bp
from routes.request_holidays import request_holidays_bp
from routes.shift_result import shift_result_bp
from routes.staff_management import staff_management_bp

app = Flask(__name__)
app.secret_key = config.FLASK_CONFIG.get('SECRET_KEY', 'autoshift-secret-key-change-in-production')

# Blueprintを登録
app.register_blueprint(shift_generation_bp)
app.register_blueprint(facility_rules_bp)
app.register_blueprint(request_holidays_bp)
app.register_blueprint(shift_result_bp)
app.register_blueprint(staff_management_bp)

# ====================
# エンドポイント
# ====================

# ====================
# 基本エンドポイント
# ====================

@app.route('/', methods=['GET'])
def index():
    """ホームページ"""
    return render_template('index.html') if Path('templates/index.html').exists() else jsonify({
        'status': 'ok',
        'message': 'AutoShift API Server',
        'version': '3.0.0',
        'features': {
            'shift_generation': True,
            'constraint_management': True,
            'display_system': True,
            'web_ui': 'In Development'
        }
    })

@app.route('/facility_rules', methods=['GET'])
def facility_rules_page():
    """施設ルール管理画面"""
    return render_template('facility_rules.html')

@app.route('/request_holidays', methods=['GET'])
def request_holidays_page():
    """希望休入力画面"""
    return render_template('request_holidays.html')

@app.route('/shift_display', methods=['GET'])
def shift_display_page():
    """シフト表示画面"""
    return render_template('shift_display.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    try:
        # システム動作確認
        from optimizer.solver import ShiftOptimizer
        from utils.shift_display import ShiftDisplayManager
        
        return jsonify({
            'status': 'healthy',
            'message': 'AutoShift システム正常稼働中',
            'components': {
                'optimizer': 'OK',
                'display_manager': 'OK',
                'yaml_handler': 'OK'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': f'システムエラー: {str(e)}'
        }), 500

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
