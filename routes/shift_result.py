"""
AutoShift - シフト表示API
生成されたシフトの表示とダウンロード機能
2026年2月9日
"""

from flask import Blueprint, jsonify, request, render_template, send_file
from pathlib import Path
import json
import csv
import io
import sys
from datetime import datetime, date

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from optimizer.solver import ShiftOptimizer
from utils.shift_display import ShiftDisplayManager
from utils.yaml_handler import load_project_staff
from models import ShiftType

shift_result_bp = Blueprint('shift_result', __name__)

# ====================

# API エンドポイント
# ====================

@shift_result_bp.route('/api/shift/display/generate/<month>', methods=['POST'])
def generate_and_display_shift(month):
    """
    シフト生成して表示API
    
    Args:
        month: 対象月 (YYYY-MM形式)
        
    Returns:
        JSON: 生成されたシフト情報
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
        
        # 最適化実行
        print(f"🚀 {month} のシフト最適化を開始...")
        optimizer = ShiftOptimizer(month)
        result = optimizer.optimize()

        # 実行可能解がない場合は、表示データを作らずエラー返却
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
                    'solver_time': round(result.solver_time, 4)
                }
            }), 422
        
        # 表示マネージャー初期化
        display = ShiftDisplayManager()
        
        # シフト表データ生成
        shift_table = display.generate_shift_table_data(result, optimizer.staff_list, optimizer.dates)
        
        # 統計データ生成
        statistics = display.generate_statistics_data(result, optimizer.staff_list, optimizer.dates)
        
        # 違反情報
        violations = []
        if result.violations:
            for violation in result.violations:
                violations.append({
                    'type': violation.get('type', 'unknown'),
                    'message': violation.get('message', ''),
                    'staff_id': violation.get('staff_id'),
                    'date': violation.get('date')
                })
        
        response_data = {
            'status': 'success',
            'message': f'{month}のシフトを生成しました',
            'data': {
                'month': month,
                'solver_status': result.solver_status,
                'solver_time': round(result.solver_time, 4),
                'shift_table': shift_table,
                'statistics': statistics,
                'violations': violations,
                'generated_at': datetime.now().isoformat()
            }
        }
        
        print(f"✅ シフト生成・表示データ作成完了: {result.solver_status} ({result.solver_time:.3f}秒)")
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"❌ シフト生成・表示エラー: {e}")
        return jsonify({
            'status': 'error',
            'message': f'シフト生成に失敗しました: {str(e)}'
        }), 500

@shift_result_bp.route('/api/shift/display/table/<month>', methods=['GET'])
def get_shift_table_data(month):
    """
    シフト表データ取得API（表示専用、生成は行わない）
    
    Args:
        month: 対象月 (YYYY-MM形式)
        
    Returns:
        JSON: 保存済みシフト表データまたはデータなしメッセージ
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
        
        # 保存済み結果確認
        results_dir = Path(__file__).parent.parent / "results"
        result_file = results_dir / f"shift_result_{month.replace('-', '_')}.json"
        
        if result_file.exists():
            # 保存済みデータを読み込み
            with open(result_file, 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                
            # 表示マネージャー初期化
            display = ShiftDisplayManager()
            
            # 必要に応じてデータ形式を変換
            response_data = {
                'status': 'success',
                'message': f'{month}の保存済みシフトデータを読み込みました',
                'data': saved_data
            }
            
            return jsonify(response_data), 200
        else:
            # 保存済みデータが存在しない場合
            return jsonify({
                'status': 'no_data',
                'message': f'{month}のシフトデータがありません。生成ボタンを押してシフトを作成してください。'
            }), 200
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'シフト表データ取得に失敗しました: {str(e)}'
        }), 500

@shift_result_bp.route('/api/shift/display/export/<month>/<format>', methods=['GET'])
def export_shift_data(month, format):
    """
    シフトデータエクスポートAPI
    
    Args:
        month: 対象月 (YYYY-MM形式)
        format: エクスポート形式 (csv, json, excel)
        
    Returns:
        File: エクスポートファイル
    """
    try:
        # 最適化実行
        optimizer = ShiftOptimizer(month)
        result = optimizer.optimize()
        
        display = ShiftDisplayManager()
        
        if format.lower() == 'csv':
            # CSV生成
            csv_path = display.export_to_csv(result, optimizer.staff_list, optimizer.dates)
            return send_file(csv_path, as_attachment=True, 
                           download_name=f'shift_{month}.csv')
        
        elif format.lower() == 'json':
            # JSON生成
            shift_data = {
                'month': month,
                'generated_at': datetime.now().isoformat(),
                'solver_status': result.solver_status,
                'solver_time': result.solver_time,
                'shifts': {}
            }
            
            for (staff_id, date_obj), shift_type in result.shifts.items():
                date_str = date_obj.strftime('%Y-%m-%d')
                if date_str not in shift_data['shifts']:
                    shift_data['shifts'][date_str] = {}
                shift_data['shifts'][date_str][str(staff_id)] = shift_type.value
            
            # メモリ上でJSON作成
            json_buffer = io.StringIO()
            json.dump(shift_data, json_buffer, ensure_ascii=False, indent=2)
            json_buffer.seek(0)
            
            return send_file(
                io.BytesIO(json_buffer.getvalue().encode('utf-8')),
                mimetype='application/json',
                as_attachment=True,
                download_name=f'shift_{month}.json'
            )
        
        elif format.lower() == 'excel':
            # Excel生成 (pandas使用)
            try:
                import pandas as pd
                import openpyxl  # noqa: F401
                
                shift_table = display.generate_shift_table_data(result, optimizer.staff_list, optimizer.dates)
                
                # DataFrameに変換
                df = pd.DataFrame(shift_table['rows'])
                
                # Excel書き出し
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='シフト表', index=False)
                    
                    # 統計シートも追加
                    stats = display.generate_statistics_data(result, optimizer.staff_list, optimizer.dates)
                    stats_df = pd.DataFrame(stats['staff_stats'])
                    stats_df.to_excel(writer, sheet_name='統計', index=False)
                
                excel_buffer.seek(0)
                
                return send_file(
                    excel_buffer,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=f'shift_{month}.xlsx'
                )
                
            except ImportError as e:
                return jsonify({
                    'status': 'error',
                    'message': f'Excelエクスポートに必要なライブラリが不足しています: {e}'
                }), 500
        
        else:
            return jsonify({
                'status': 'error',
                'message': f'サポートされていないフォーマット: {format}'
            }), 400
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'エクスポートに失敗しました: {str(e)}'
        }), 500

@shift_result_bp.route('/api/shift/display/validate/<month>', methods=['GET'])
def validate_shift(month):
    """
    シフト妥当性検証API
    
    Args:
        month: 対象月 (YYYY-MM形式)
        
    Returns:
        JSON: 検証結果
    """
    try:
        # 最適化実行
        optimizer = ShiftOptimizer(month)
        result = optimizer.optimize()
        
        # 制約違反チェック
        violations = result.violations or []
        
        # 各種統計
        total_shifts = len(result.shifts)
        staff_count = len(optimizer.staff_list)
        date_count = len(optimizer.dates)
        
        # 勤務タイプ別集計
        shift_type_counts = {}
        for shift_type in result.shifts.values():
            type_name = shift_type.name
            shift_type_counts[type_name] = shift_type_counts.get(type_name, 0) + 1
        
        # 検証結果
        validation_result = {
            'is_valid': len(violations) == 0,
            'violation_count': len(violations),
            'violations': violations,
            'statistics': {
                'total_shifts': total_shifts,
                'staff_count': staff_count,
                'date_count': date_count,
                'shift_type_distribution': shift_type_counts
            },
            'performance': {
                'solver_status': result.solver_status,
                'solver_time': result.solver_time,
                'optimization_success': result.solver_status == 'OPTIMAL'
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': validation_result
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'シフト検証に失敗しました: {str(e)}'
        }), 500

@shift_result_bp.route('/api/shift/display/compare/<month1>/<month2>', methods=['GET'])
def compare_shifts(month1, month2):
    """
    シフト比較API
    
    Args:
        month1: 比較対象月1 (YYYY-MM形式)
        month2: 比較対象月2 (YYYY-MM形式)
        
    Returns:
        JSON: 比較結果
    """
    try:
        # 両方の月のシフトを生成
        optimizer1 = ShiftOptimizer(month1)
        result1 = optimizer1.optimize()
        
        optimizer2 = ShiftOptimizer(month2)
        result2 = optimizer2.optimize()
        
        # 比較データ作成
        comparison = {
            'month1': {
                'month': month1,
                'solver_status': result1.solver_status,
                'solver_time': result1.solver_time,
                'violation_count': len(result1.violations or [])
            },
            'month2': {
                'month': month2,
                'solver_status': result2.solver_status,
                'solver_time': result2.solver_time,
                'violation_count': len(result2.violations or [])
            },
            'performance_comparison': {
                'faster_month': month1 if result1.solver_time < result2.solver_time else month2,
                'time_diff': abs(result1.solver_time - result2.solver_time),
                'both_optimal': (result1.solver_status == 'OPTIMAL' and result2.solver_status == 'OPTIMAL')
            }
        }
        
        return jsonify({
            'status': 'success',
            'data': comparison
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'シフト比較に失敗しました: {str(e)}'
        }), 500
