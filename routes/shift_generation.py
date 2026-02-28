"""
AutoShift - シフト生成API
2026年2月9日

役割:
- シフト自動生成エンドポイント
- 結果の取得・保存
- 統計情報の提供
"""

from flask import Blueprint, jsonify, request, render_template
from typing import Dict, Any
import json
import os
from pathlib import Path

# AutoShiftコア機能
from optimizer.solver import ShiftOptimizer
from utils.shift_display import ShiftDisplayManager
from utils.yaml_handler import load_project_staff, load_project_rules, load_project_request_holidays

# Blueprint作成
shift_generation_bp = Blueprint('shift_generation', __name__)

# ==========================================
# API エンドポイント
# ==========================================

@shift_generation_bp.route('/api/shift/generate', methods=['POST'])
def generate_shift():
    """
    シフト自動生成API
    
    POST /api/shift/generate
    Body: {
        "month": "2026-02"
    }
    
    Returns:
        JSON: 生成結果とメタデータ
    """
    try:
        data = request.json or {}
        month = data.get('month', '2026-02')
        
        # print(f"シフト生成開始: {month}")
        
        # 1. 最適化実行
        optimizer = ShiftOptimizer(month)
        result = optimizer.optimize()

        # 実行可能解がない場合
        if result.solver_status in ('INFEASIBLE', 'UNKNOWN'):
            return jsonify({
                'status': 'error',
                'message': (
                    f'{month}はシフトを作成できませんでした '
                    f'(solver_status={result.solver_status})。'
                    'ルールまたは希望休を見直してください。'
                ),
                'data': {
                    'month': month,
                    'solver_status': result.solver_status,
                    'solver_status_code': result.solver_status_code,
                    'solver_status_name': result.solver_status_name,
                    'solver_time': round(result.solver_time, 4),
                    'diagnosis': result.diagnosis
                }
            }), 422
        
        # 2. 結果を辞書形式に変換
        shift_dict = {}
        for (staff_id, date), shift_type_value in result.shifts.items():
            date_str = date.strftime('%Y-%m-%d')
            if date_str not in shift_dict:
                shift_dict[date_str] = {}
            shift_dict[date_str][str(staff_id)] = shift_type_value.value
            
        # 3. 統計情報生成
        display = ShiftDisplayManager()
        stats = _generate_statistics(result, optimizer.staff_list, optimizer.dates)
        
        # 4. 結果保存（オプション）
        save_path = _save_result(month, result, optimizer)
        
        response_data = {
            'status': 'success',
            'message': f'{month}のシフトを生成しました',
            'data': {
                'month': month,
                'solver_status': result.solver_status,
                'solver_status_code': result.solver_status_code,
                'solver_status_name': result.solver_status_name,
                'solver_time': round(result.solver_time, 4),
                'shifts': shift_dict,
                'violations': result.violations,
                'statistics': stats,
                'save_path': save_path
            }
        }
        
        # print(f"シフト生成完了: {result.solver_status} ({result.solver_time:.3f}秒)")
        return jsonify(response_data), 200
        
    except Exception as e:
        # print(f"シフト生成エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'シフト生成に失敗しました: {str(e)}'
        }), 500

@shift_generation_bp.route('/api/shift/result/<month>', methods=['GET'])
def get_shift_result(month):
    """
    シフト結果取得API
    
    GET /api/shift/result/2026-02
    
    Returns:
        JSON: 保存済みシフト結果
    """
    try:
        # 保存ファイル確認
        results_dir = Path(__file__).parent.parent / "results"
        result_file = results_dir / f"shift_result_{month.replace('-', '_')}.json"
        
        if not result_file.exists():
            return jsonify({
                'status': 'error', 
                'message': f'{month}のシフト結果が見つかりません'
            }), 404
            
        # 結果読み込み
        with open(result_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            
        return jsonify({
            'status': 'success',
            'data': saved_data
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'結果取得に失敗しました: {str(e)}'
        }), 500

@shift_generation_bp.route('/api/shift/display/<month>', methods=['GET'])
def display_shift_table(month):
    """
    シフト表表示API（HTML表示用）
    
    GET /api/shift/display/2026-02
    
    Returns:
        JSON: 表示用データ
    """
    try:
        # 最新結果を再生成（デモ用）
        optimizer = ShiftOptimizer(month)
        result = optimizer.optimize()

        # 実行可能解がない場合
        if result.solver_status in ('INFEASIBLE', 'UNKNOWN'):
            return jsonify({
                'status': 'error',
                'message': (
                    f'{month}はシフトを作成できませんでした '
                    f'(solver_status={result.solver_status})。'
                    'ルールまたは希望休を見直してください。'
                ),
                'data': {
                    'month': month,
                    'solver_status': result.solver_status,
                    'solver_status_code': result.solver_status_code,
                    'solver_status_name': result.solver_status_name,
                    'solver_time': round(result.solver_time, 4),
                    'diagnosis': result.diagnosis
                }
            }), 422
        
        # 表示マネージャー作成
        display = ShiftDisplayManager() 
        
        # 各種表示データ生成
        shift_table_data = _generate_table_data(result, optimizer.staff_list, optimizer.dates)
        stats_data = _generate_statistics(result, optimizer.staff_list, optimizer.dates)
        daily_data = _generate_daily_assignments(result, optimizer.staff_list, optimizer.dates[:7])  # 1週間分
        
        return jsonify({
            'status': 'success',
            'data': {
                'month': month,
                'solver_info': {
                    'status': result.solver_status,
                    'status_code': result.solver_status_code,
                    'status_name': result.solver_status_name,
                    'time': round(result.solver_time, 4),
                    'violations_count': len(result.violations)
                },
                'shift_table': shift_table_data,
                'statistics': stats_data,
                'daily_assignments': daily_data,
                'violations': result.violations
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'表示データ生成に失敗しました: {str(e)}'
        }), 500

# ==========================================
# Web UI エンドポイント
# ==========================================

@shift_generation_bp.route('/shift/result/<month>')
def shift_result_page(month):
    """
    シフト結果表示ページ
    
    GET /shift/result/2026-02
    """
    try:
        return render_template('shift_result.html', month=month)
    except Exception as e:
        return f"ページ表示エラー: {str(e)}", 500

# ==========================================
# ヘルパー関数
# ==========================================

def _generate_table_data(result, staff_list, dates) -> Dict[str, Any]:
    """シフト表データ生成"""
    table_data = {
        'header': ['スタッフ名', '職種'] + [f"{d.month}/{d.day}" for d in dates],
        'rows': []
    }
    
    shift_names = {0: "日勤", 1: "夜勤", 2: "夜勤明", 3: "公休", 4: "希望休", 5: "有給"}
    
    for staff in staff_list:
        row = [staff.name, staff.staff_class]
        for date in dates:
            shift_value = result.shifts.get((staff.id, date), 0)
            row.append(shift_names.get(shift_value, "不明"))
        table_data['rows'].append(row)
        
    return table_data

def _generate_statistics(result, staff_list, dates) -> Dict[str, Any]:
    """統計データ生成"""
    stats = {
        'staff_stats': [],
        'total_stats': {
            'day_shifts': 0,
            'night_shifts': 0, 
            'night_offs': 0,
            'public_holidays': 0,
            'request_holidays': 0,
            'paid_holidays': 0
        }
    }
    
    for staff in staff_list:
        staff_stat = {
            'name': staff.name,
            'class': staff.staff_class,
            'day_shifts': 0,
            'night_shifts': 0,
            'night_offs': 0,
            'public_holidays': 0,
            'request_holidays': 0,
            'paid_holidays': 0,
            'total_work_days': 0
        }
        
        for date in dates:
            shift_value = result.shifts.get((staff.id, date), 0)
            if shift_value == 0:  # 日勤
                staff_stat['day_shifts'] += 1
                staff_stat['total_work_days'] += 1
                stats['total_stats']['day_shifts'] += 1
            elif shift_value == 1:  # 夜勤
                staff_stat['night_shifts'] += 1
                staff_stat['total_work_days'] += 1
                stats['total_stats']['night_shifts'] += 1
            elif shift_value == 2:  # 夜勤明
                staff_stat['night_offs'] += 1
                staff_stat['total_work_days'] += 1
                stats['total_stats']['night_offs'] += 1
            elif shift_value == 3:  # 公休
                staff_stat['public_holidays'] += 1
                stats['total_stats']['public_holidays'] += 1
            elif shift_value == 4:  # 希望休
                staff_stat['request_holidays'] += 1
                stats['total_stats']['request_holidays'] += 1
            elif shift_value == 5:  # 有給
                staff_stat['paid_holidays'] += 1
                stats['total_stats']['paid_holidays'] += 1
                
        stats['staff_stats'].append(staff_stat)
        
    return stats

def _generate_daily_assignments(result, staff_list, dates) -> Dict[str, Any]:
    """日別配置データ生成"""
    daily_data = {}
    
    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        assignments = {
            'date': date_str,
            'weekday': date.strftime('%A'),
            'day_shift': [],
            'night_shift': [],
            'night_off': [],
            'public_holiday': [],
            'request_holiday': [],
            'paid_holiday': []
        }
        
        for staff in staff_list:
            shift_value = result.shifts.get((staff.id, date), 0)
            staff_info = f"{staff.name}({staff.staff_class})"
            
            if shift_value == 0:
                assignments['day_shift'].append(staff_info)
            elif shift_value == 1:
                assignments['night_shift'].append(staff_info)
            elif shift_value == 2:
                assignments['night_off'].append(staff_info)
            elif shift_value == 3:
                assignments['public_holiday'].append(staff_info)
            elif shift_value == 4:
                assignments['request_holiday'].append(staff_info)
            elif shift_value == 5:
                assignments['paid_holiday'].append(staff_info)
                
        daily_data[date_str] = assignments
        
    return daily_data

def _save_result(month: str, result, optimizer) -> str:
    """結果をJSONファイルに保存"""
    try:
        # 保存ディレクトリ作成
        results_dir = Path(__file__).parent.parent / "results"
        results_dir.mkdir(exist_ok=True)
        
        # ファイル名生成
        filename = f"shift_result_{month.replace('-', '_')}.json"
        filepath = results_dir / filename
        
        # 保存データ作成
        save_data = {
            'month': month,
            'generated_at': str(result.solver_time),
            'solver_status': result.solver_status,
            'solver_time': result.solver_time,
            'shifts': {f"{staff_id}_{date.strftime('%Y%m%d')}": shift_type.value 
                      for (staff_id, date), shift_type in result.shifts.items()},
            'violations': result.violations,
            'staff_count': len(optimizer.staff_list),
            'dates_count': len(optimizer.dates)
        }
        
        # JSON保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
            
        return str(filepath)
        
    except Exception as e:
        # print(f"結果保存エラー: {e}")
        return f"保存失敗: {e}"
