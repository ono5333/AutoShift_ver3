"""
AutoShift - スタッフ管理API
2026年2月11日

役割:
- スタッフ一覧・詳細取得
- スタッフ新規作成・更新・削除
- スタッフ管理画面の表示
"""

from flask import Blueprint, jsonify, request, render_template
from typing import Dict, Any, List
import yaml
from pathlib import Path

# プロジェクト設定
import config

def load_staff_data():
    """staff_list.yml を辞書リストとして読み込み"""
    try:
        with open(config.STAFF_LIST_FILE, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # dataがNoneまたは辞書でない場合のハンドリング
        if not isinstance(data, dict):
            return []
            
        return data.get('staff', [])
    except FileNotFoundError:
        return []
    except Exception as e:
        raise Exception(f"スタッフデータ読み込みエラー: {e}")

def save_staff_data(staff_list):
    """staff_list.yml に辞書リストを保存"""
    try:
        data = {'staff': staff_list}
        with open(config.STAFF_LIST_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except Exception as e:
        raise Exception(f"スタッフデータ保存エラー: {e}")

# Blueprint作成
staff_management_bp = Blueprint('staff_management', __name__)

# ==========================================
# Web画面ルート
# ==========================================

@staff_management_bp.route('/staff_management')
def staff_management_page():
    """スタッフ管理画面を表示"""
    try:
        return render_template('staff_management.html')
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'画面表示エラー: {str(e)}'
        }), 500

# ==========================================
# API エンドポイント  
# ==========================================

@staff_management_bp.route('/api/staff', methods=['GET'])
def get_staff_list():
    """スタッフ一覧取得
    GET /api/staff
    """
    try:
        staff_list = load_staff_data()
        
        return jsonify({
            'status': 'success',
            'data': {
                'staff': staff_list,
                'total': len(staff_list),
                'active': len([s for s in staff_list if s.get('active', True)])
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'スタッフ一覧取得エラー: {str(e)}'
        }), 500

@staff_management_bp.route('/api/staff/<int:staff_id>', methods=['GET'])
def get_staff_detail(staff_id):
    """スタッフ詳細取得  
    GET /api/staff/{id}
    """
    try:
        staff_list = load_staff_data()
        staff = next((s for s in staff_list if s['id'] == staff_id), None)
        
        if not staff:
            return jsonify({
                'status': 'error',
                'message': 'スタッフが見つかりません'
            }), 404
            
        return jsonify({
            'status': 'success',
            'data': staff
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'スタッフ詳細取得エラー: {str(e)}'
        }), 500

@staff_management_bp.route('/api/staff', methods=['POST'])
def create_staff():
    """スタッフ新規作成
    POST /api/staff
    Body: {
        "name": "新田花子",
        "class": "介護士"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'リクエストデータが必要です'
            }), 400
            
        # バリデーション
        name = data.get('name', '').strip()
        staff_class = data.get('class', '').strip()
        
        if not name:
            return jsonify({
                'status': 'error',
                'message': 'スタッフ名は必須です'
            }), 400
            
        if not staff_class:
            return jsonify({
                'status': 'error',
                'message': '職種は必須です'
            }), 400
            
        if staff_class not in ['介護士', '初級介護士', 'お風呂']:
            return jsonify({
                'status': 'error',
                'message': '無効な職種です'
            }), 400
        
        # 現在のスタッフリスト取得
        staff_list = load_staff_data()
        
        # 新しいIDを生成（最大ID + 1）
        new_id = max([s['id'] for s in staff_list], default=0) + 1
        
        # 同名スタッフの重複チェック
        if any(s['name'] == name for s in staff_list):
            return jsonify({
                'status': 'error',
                'message': '同名のスタッフが既に存在します'
            }), 400
        
        # 新しいスタッフを作成
        new_staff = {
            'id': new_id,
            'name': name,
            'class': staff_class
        }
        
        # リストに追加
        staff_list.append(new_staff)
        
        # YAMLファイルに保存
        save_staff_data(staff_list)
        
        return jsonify({
            'status': 'success',
            'message': 'スタッフを追加しました',
            'data': new_staff
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'スタッフ作成エラー: {str(e)}'
        }), 500

@staff_management_bp.route('/api/staff/<int:staff_id>', methods=['PUT'])
def update_staff(staff_id):
    """スタッフ更新
    PUT /api/staff/{id}  
    Body: {
        "name": "山田志保里（更新）",
        "class": "介護士"
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'リクエストデータが必要です'
            }), 400
            
        # バリデーション
        name = data.get('name', '').strip()
        staff_class = data.get('class', '').strip()
        
        if not name:
            return jsonify({
                'status': 'error',
                'message': 'スタッフ名は必須です'
            }), 400
            
        if not staff_class:
            return jsonify({
                'status': 'error',
                'message': '職種は必須です'
            }), 400
            
        if staff_class not in ['介護士', '初級介護士', 'お風呂']:
            return jsonify({
                'status': 'error',
                'message': '無効な職種です'
            }), 400
        
        # 現在のスタッフリスト取得
        staff_list = load_staff_data()
        
        # 対象スタッフを検索
        target_staff = None
        for i, staff in enumerate(staff_list):
            if staff['id'] == staff_id:
                target_staff = staff
                target_index = i
                break
        
        if not target_staff:
            return jsonify({
                'status': 'error',
                'message': 'スタッフが見つかりません'
            }), 404
        
        # 同名スタッフの重複チェック（自分以外）
        if any(s['name'] == name and s['id'] != staff_id for s in staff_list):
            return jsonify({
                'status': 'error',
                'message': '同名のスタッフが既に存在します'
            }), 400
        
        # スタッフ情報を更新
        staff_list[target_index]['name'] = name
        staff_list[target_index]['class'] = staff_class
        
        # YAMLファイルに保存
        save_staff_data(staff_list)
        
        return jsonify({
            'status': 'success',
            'message': 'スタッフ情報を更新しました',
            'data': staff_list[target_index]
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'スタッフ更新エラー: {str(e)}'
        }), 500

@staff_management_bp.route('/api/staff/<int:staff_id>', methods=['DELETE'])
def delete_staff(staff_id):
    """スタッフ削除
    DELETE /api/staff/{id}
    """
    try:
        # 現在のスタッフリスト取得
        staff_list = load_staff_data()
        
        # 対象スタッフを検索
        target_staff = None
        for i, staff in enumerate(staff_list):
            if staff['id'] == staff_id:
                target_staff = staff
                target_index = i
                break
        
        if not target_staff:
            return jsonify({
                'status': 'error',
                'message': 'スタッフが見つかりません'
            }), 404
        
        # TODO: 制約チェック - 削除対象スタッフが个人ルールやシフトに使用されていないか確認
        # 現時点では削除を許可
        
        # スタッフをリストから削除
        deleted_staff = staff_list.pop(target_index)
        
        # YAMLファイルに保存
        save_staff_data(staff_list)
        
        return jsonify({
            'status': 'success',
            'message': f'スタッフ「{deleted_staff["name"]}」を削除しました'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'スタッフ削除エラー: {str(e)}'
        }), 500

@staff_management_bp.route('/api/staff/classes', methods=['GET'])
def get_staff_classes():
    """職種一覧取得
    GET /api/staff/classes
    """
    try:
        return jsonify({
            'status': 'success',
            'data': {
                'classes': ['介護士', '初級介護士', 'お風呂']
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'職種一覧取得エラー: {str(e)}'
        }), 500