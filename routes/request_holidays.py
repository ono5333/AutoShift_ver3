"""
AutoShift - 希望休管理API
スタッフの希望休・有給申請入力機能
2026年2月9日
"""

from flask import Blueprint, jsonify, request, render_template
from pathlib import Path
from datetime import datetime, date
import yaml
import sys

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.yaml_handler import load_project_staff, load_project_request_holidays, save_project_request_holidays
from models import ShiftType

request_holidays_bp = Blueprint('request_holidays', __name__)


def _get_shift_generation_ordered_staff():
    """シフト生成と同じ並び順でスタッフを返す（看護師も表示）。"""
    staff_list = load_project_staff()
    class_priority = {
        '介護士': 0,
        '初級介護士': 1,
        'お風呂': 2,
        '看護師': 3,
    }
    staff_list.sort(key=lambda s: (class_priority.get(s.staff_class, 999), s.id))
    return staff_list

# ====================

# API エンドポイント
# ====================

@request_holidays_bp.route('/api/holidays/staff', methods=['GET'])
def get_staff_list():
    """
    スタッフ一覧取得API
    
    Returns:
        JSON: {
            'status': 'success',
            'data': [
                {'id': 1, 'name': 'スタッフ名', 'staff_class': '介護士'},
                ...
            ]
        }
    """
    try:
        staff_list = _get_shift_generation_ordered_staff()
        
        # スタッフ情報をJSON形式に変換
        staff_data = []
        for staff in staff_list:
            staff_data.append({
                'id': staff.id,
                'name': staff.name,
                'staff_class': staff.staff_class
            })
        
        return jsonify({
            'status': 'success',
            'data': staff_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'スタッフ一覧取得に失敗しました: {str(e)}'
        }), 500

@request_holidays_bp.route('/api/holidays/request/<month>', methods=['GET'])
def get_request_holidays(month):
    """
    希望休一覧取得API
    
    Args:
        month: 対象月 (YYYY-MM形式)
        
    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'month': '2026-02',
                'requests': [
                    {
                        'staff_id': 1,
                        'staff_name': 'スタッフ名',
                        'date': '2026-02-01',
                        'type': 'REQUEST_HOLIDAY',
                        'reason': '理由'
                    },
                    ...
                ]
            }
        }
    """
    try:
        # 月の形式確認
        try:
            datetime.strptime(month, '%Y-%m')
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '月の形式が正しくありません (YYYY-MM形式で指定してください)'
            }), 400
        
        # 希望休データ読み込み
        request_data = load_project_request_holidays(month)
        
        # スタッフ一覧も取得（名前表示用）
        staff_list = _get_shift_generation_ordered_staff()
        staff_dict = {staff.id: staff.name for staff in staff_list}
        
        # レスポンス形式に変換
        requests = []
        for staff_request in request_data.get('staff_requests', []):
            staff_id = staff_request.get('staff_id')
            staff_name = staff_request.get('staff_name', f'スタッフ{staff_id}')
            
            for request in staff_request.get('requests', []):
                requests.append({
                    'staff_id': staff_id,
                    'staff_name': staff_name,
                    'date': request.get('date'),
                    'type': request.get('type'),
                    'reason': request.get('reason', '')
                })
        
        # 日付順でソート
        requests.sort(key=lambda x: (x['date'], x['staff_id']))
        
        return jsonify({
            'status': 'success',
            'data': {
                'month': month,
                'requests': requests
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'希望休取得に失敗しました: {str(e)}'
        }), 500

@request_holidays_bp.route('/api/holidays/request/<month>', methods=['POST'])
def add_request_holiday(month):
    """
    希望休追加API
    
    Args:
        month: 対象月 (YYYY-MM形式)
        
    Body: {
        'staff_id': 1,
        'date': '2026-02-15',
        'type': 'REQUEST_HOLIDAY' or 'PAID_HOLIDAY',
        'reason': '理由'
    }
    """
    try:
        data = request.json or {}
        
        # 必須フィールド確認
        required_fields = ['staff_id', 'date', 'type']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'必須フィールドが不足しています: {", ".join(missing_fields)}'
            }), 400
        
        # データ検証
        staff_id = data['staff_id']
        request_date = data['date']
        request_type = data['type']
        reason = data.get('reason', '')
        
        # スタッフID検証
        staff_list = _get_shift_generation_ordered_staff()
        if staff_id not in [staff.id for staff in staff_list]:
            return jsonify({
                'status': 'error',
                'message': f'無効なスタッフIDです: {staff_id}'
            }), 400
        
        # 日付検証
        try:
            date_obj = datetime.strptime(request_date, '%Y-%m-%d').date()
            month_obj = datetime.strptime(month, '%Y-%m').date().replace(day=1)
            if date_obj.year != month_obj.year or date_obj.month != month_obj.month:
                return jsonify({
                    'status': 'error',
                    'message': '指定された日付が対象月と一致しません'
                }), 400
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '日付の形式が正しくありません (YYYY-MM-DD形式で指定してください)'
            }), 400
        
        # タイプ検証（看護師のみ 日/夜/明/休 を許可）
        target_staff = next((staff for staff in staff_list if staff.id == staff_id), None)
        if not target_staff:
            return jsonify({
                'status': 'error',
                'message': f'無効なスタッフIDです: {staff_id}'
            }), 400

        if target_staff.staff_class == '看護師':
            valid_types = ['日', '夜', '明', '休', '希', '有']
        else:
            valid_types = ['希', '有']

        if request_type not in valid_types:
            return jsonify({
                'status': 'error',
                'message': f'無効な設定タイプです。有効な値: {", ".join(valid_types)}'
            }), 400
        
        # 既存データ読み込み
        request_data = load_project_request_holidays(month)
        
        # 該当スタッフを検索または作成
        staff_request = None
        for staff_entry in request_data.get('staff_requests', []):
            if staff_entry.get('staff_id') == staff_id:
                staff_request = staff_entry
                break
        
        if not staff_request:
            # 新しいスタッフエントリを作成
            staff_name = next((staff.name for staff in staff_list if staff.id == staff_id), f'スタッフ{staff_id}')
            staff_request = {
                'staff_id': staff_id,
                'staff_name': staff_name,
                'requests': []
            }
            request_data.setdefault('staff_requests', []).append(staff_request)
        
        # 重複チェック
        for existing_request in staff_request.get('requests', []):
            if existing_request.get('date') == request_date:
                return jsonify({
                    'status': 'error',
                    'message': f'この日付の希望休は既に登録されています: {request_date}'
                }), 400
        
        # 新しい希望休を追加
        new_request = {
            'date': request_date,
            'type': request_type,
            'reason': reason
        }
        staff_request.setdefault('requests', []).append(new_request)
        
        # 保存
        save_project_request_holidays(month, request_data)
        
        # スタッフ名取得
        staff_name = next(staff.name for staff in staff_list if staff.id == staff_id)
        
        return jsonify({
            'status': 'success',
            'message': f'{staff_name}の{request_date}の希望休を登録しました',
            'data': {
                'staff_id': staff_id,
                'staff_name': staff_name,
                'date': request_date,
                'type': request_type,
                'reason': reason
            }
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'希望休登録に失敗しました: {str(e)}'
        }), 500

@request_holidays_bp.route('/api/holidays/request/<month>/<staff_id>/<date>', methods=['DELETE'])
def delete_request_holiday(month, staff_id, date):
    """
    希望休削除API
    
    Args:
        month: 対象月 (YYYY-MM形式)
        staff_id: スタッフID
        date: 日付 (YYYY-MM-DD形式)
    """
    try:
        staff_id = int(staff_id)
        
        # データ読み込み
        request_data = load_project_request_holidays(month)
        staff_list = _get_shift_generation_ordered_staff()
        
        # 希望休削除
        deleted = False
        for staff_entry in request_data.get('staff_requests', []):
            if staff_entry.get('staff_id') == staff_id:
                # 該当する日付の希望休を削除
                original_requests = staff_entry.get('requests', [])
                staff_entry['requests'] = [
                    req for req in original_requests 
                    if req.get('date') != date
                ]
                
                # 削除されたかチェック 
                if len(staff_entry['requests']) < len(original_requests):
                    deleted = True
                break
        
        if deleted:
            # 保存
            save_project_request_holidays(month, request_data)
            
            # スタッフ名取得
            staff_name = next((staff.name for staff in staff_list if staff.id == staff_id), f'スタッフ{staff_id}')
            
            return jsonify({
                'status': 'success',
                'message': f'{staff_name}の{date}の希望休を削除しました'
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': '指定された希望休が見つかりません'
            }), 404
            
    except ValueError:
        return jsonify({
            'status': 'error',
            'message': '無効なスタッフIDです'
        }), 400
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'希望休削除に失敗しました: {str(e)}'
        }), 500

@request_holidays_bp.route('/api/holidays/request/<month>/bulk', methods=['POST'])
def bulk_add_request_holidays(month):
    """
    希望休一括登録API
    
    Args:
        month: 対象月 (YYYY-MM形式)
        
    Body: {
        'requests': [
            {
                'staff_id': 1,
                'date': '2026-02-15',
                'type': 'REQUEST_HOLIDAY',
                'reason': '理由'
            },
            ...
        ]
    }
    """
    try:
        data = request.json or {}
        requests = data.get('requests', [])
        
        if not requests:
            return jsonify({
                'status': 'error',
                'message': '登録する希望休データがありません'
            }), 400
        
        # 既存データ読み込み
        request_data = load_project_request_holidays(month)
        staff_list = _get_shift_generation_ordered_staff()
        staff_ids = [staff.id for staff in staff_list]
        
        # バリデーション
        errors = []
        for i, req in enumerate(requests):
            if req.get('staff_id') not in staff_ids:
                errors.append(f'{i+1}番目: 無効なスタッフID {req.get("staff_id")}')
            
            try:
                datetime.strptime(req.get('date', ''), '%Y-%m-%d')
            except ValueError:
                errors.append(f'{i+1}番目: 無効な日付形式 {req.get("date")}')
            
            if req.get('type') not in ['REQUEST_HOLIDAY', 'PAID_HOLIDAY']:
                errors.append(f'{i+1}番目: 無効な休暇タイプ {req.get("type")}')
        
        if errors:
            return jsonify({
                'status': 'error',
                'message': 'バリデーションエラー',
                'errors': errors
            }), 400
        
        # 一括登録
        added_count = 0
        skipped_count = 0
        
        for req in requests:
            staff_id = req['staff_id']
            request_date = req['date']
            request_type = req['type']
            reason = req.get('reason', '')
            
            # 該当スタッフを検索
            staff_request = None
            for staff_entry in request_data.get('staff_requests', []):
                if staff_entry.get('staff_id') == staff_id:
                    staff_request = staff_entry
                    break
            
            if not staff_request:
                # 新しいスタッフエントリを作成
                staff_name = next((staff.name for staff in staff_list if staff.id == staff_id), f'スタッフ{staff_id}')
                staff_request = {
                    'staff_id': staff_id,
                    'staff_name': staff_name,
                    'requests': []
                }
                request_data.setdefault('staff_requests', []).append(staff_request)
            
            # 重複チェック
            already_exists = any(
                existing_req.get('date') == request_date 
                for existing_req in staff_request.get('requests', [])
            )
            
            if not already_exists:
                new_request = {
                    'date': request_date,
                    'type': request_type,
                    'reason': reason
                }
                staff_request.setdefault('requests', []).append(new_request)
                added_count += 1
            else:
                skipped_count += 1
        
        # 保存
        save_project_request_holidays(month, request_data)
        
        return jsonify({
            'status': 'success',
            'message': f'{added_count}件の希望休を登録しました',
            'details': {
                'added': added_count,
                'skipped': skipped_count
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'一括登録に失敗しました: {str(e)}'
        }), 500

@request_holidays_bp.route('/api/holidays/calendar/<month>', methods=['GET'])
def get_calendar_data(month):
    """
    カレンダー表示用データ取得API
    
    Args:
        month: 対象月 (YYYY-MM形式)
        
    Returns:
        JSON: カレンダー表示用のデータ
    """
    try:
        from calendar import monthrange
        import calendar
        
        # 月情報取得 
        year, month_num = map(int, month.split('-'))
        days_in_month = monthrange(year, month_num)[1]
        
        # 希望休データ読み込み
        request_data = load_project_request_holidays(month)
        
        # スタッフ一覧読み込み
        staff_list = _get_shift_generation_ordered_staff()
        
        # カレンダーデータ生成
        calendar_data = {
            'year': year,
            'month': month_num,
            'month_name': calendar.month_name[month_num],
            'days_in_month': days_in_month,
            'staff': [],
            'holidays': {}
        }
        
        # スタッフ情報
        for staff in staff_list:
            calendar_data['staff'].append({
                'id': staff.id,
                'name': staff.name,
                'staff_class': staff.staff_class
            })
        
        # 希望休情報
        for staff_request in request_data.get('staff_requests', []):
            staff_id = staff_request.get('staff_id')
            if staff_id not in calendar_data['holidays']:
                calendar_data['holidays'][staff_id] = {}
            
            for request in staff_request.get('requests', []):
                date_str = request.get('date')
                if date_str:
                    day = int(date_str.split('-')[2])
                    calendar_data['holidays'][staff_id][day] = {
                        'type': request.get('type'),
                        'reason': request.get('reason', '')
                    }
        
        return jsonify({
            'status': 'success',
            'data': calendar_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'カレンダーデータ取得に失敗しました: {str(e)}'
        }), 500
