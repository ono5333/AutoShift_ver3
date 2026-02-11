"""
AutoShift - ルール管理API
施設固有ルールの設定・編集機能
2026年2月9日
"""

from flask import Blueprint, jsonify, request, render_template
from pathlib import Path
import yaml
import sys

# プロジェクトパスを追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.yaml_handler import load_project_rules, save_project_rules
from models import RuleRank

facility_rules_bp = Blueprint('facility_rules', __name__)

# ====================
# API エンドポイント
# ====================

@facility_rules_bp.route('/api/rules/facility', methods=['GET'])
def get_facility_rules():
    """
    施設ルール一覧取得API
    
    Returns:
        JSON: {
            'status': 'success',
            'data': {
                'facility_rules': [...],
                'personal_rules': [...],
                'relationship_rules': [...]
            }
        }
    """
    try:
        rules = load_project_rules()
        
        return jsonify({
            'status': 'success',
            'data': rules
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'ルール取得に失敗しました: {str(e)}'
        }), 500

@facility_rules_bp.route('/api/rules/facility', methods=['POST'])
def create_facility_rule():
    """
    施設ルール新規作成API
    
    Body: {
        'rule_id': 'FR001',
        'rule_name': 'ルール名',
        'description': '説明',
        'rank': 'A',
        'parameters': {...}
    }
    """
    try:
        data = request.json or {}
        
        # 必須フィールド確認
        required_fields = ['rule_id', 'rule_name', 'description', 'rank']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'必須フィールドが不足しています: {", ".join(missing_fields)}'
            }), 400
        
        # 現在のルールを読み込み
        rules = load_project_rules()
        
        # ルールIDのプレフィックスに基づいてカテゴリを決定
        rule_id = data['rule_id']
        if rule_id.startswith('FR'):
            category = 'facility_rules'
            category_name = '施設ルール'
        elif rule_id.startswith('PR'):
            category = 'personal_rules'
            category_name = '個人ルール'
        elif rule_id.startswith('RR'):
            category = 'relationship_rules'
            category_name = '関係性ルール'
        else:
            return jsonify({
                'status': 'error',
                'message': f'無効なルールIDです。FR（施設）、PR（個人）、RR（関係性）のいずれかで始まる必要があります: {rule_id}'
            }), 400
        
        # ルールID重複チェック（全カテゴリをチェック）
        all_existing_ids = []
        for cat in ['facility_rules', 'personal_rules', 'relationship_rules']:
            all_existing_ids.extend([rule['id'] for rule in rules[cat]])
        
        if data['rule_id'] in all_existing_ids:
            return jsonify({
                'status': 'error',
                'message': f'ルールID "{data["rule_id"]}" は既に存在します'
            }), 400
        
        # 新しいルールを追加 (既存の構造に合わせ、適切なカテゴリに配置)
        new_rule = {
            'id': data['rule_id'],
            'title': data['rule_name'],
            'description': data['description'],
            'rank': data['rank'],
            'parameters': data.get('parameters', {})
        }
        
        rules[category].append(new_rule)
        
        # 保存
        save_project_rules(rules)
        
        return jsonify({
            'status': 'success',
            'message': f'{category_name} "{data["rule_name"]}" を作成しました',
            'data': new_rule
        }), 201
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'ルール作成に失敗しました: {str(e)}'
        }), 500

@facility_rules_bp.route('/api/rules/facility/<rule_id>', methods=['PUT'])
def update_facility_rule(rule_id):
    """
    施設ルール更新API
    
    Args:
        rule_id: 更新対象のルールID
        
    Body: {
        'rule_name': 'ルール名',
        'description': '説明',
        'rank': 'A',
        'parameters': {...}
    }
    """
    try:
        data = request.json or {}
        
        # 現在のルールを読み込み
        rules = load_project_rules()
        
        # ルールIDのプレフィックスに基づいてカテゴリを決定
        if rule_id.startswith('FR'):
            category = 'facility_rules'
            category_name = '施設ルール'
        elif rule_id.startswith('PR'):
            category = 'personal_rules'
            category_name = '個人ルール'
        elif rule_id.startswith('RR'):
            category = 'relationship_rules'
            category_name = '関係性ルール'
        else:
            return jsonify({
                'status': 'error',
                'message': f'無効なルールIDです: {rule_id}'
            }), 400
        
        # ルール検索
        target_rule = None
        for rule in rules[category]:
            if rule['id'] == rule_id:  # 正しいフィールド名を使用
                target_rule = rule
                break
        
        if not target_rule:
            return jsonify({
                'status': 'error',
                'message': f'{category_name}でルールID "{rule_id}" が見つかりません'
            }), 404
        
        # ルール更新（既存の構造に合わせて）
        if 'rule_name' in data:
            target_rule['title'] = data['rule_name']  # title フィールドに保存
        if 'description' in data:
            target_rule['description'] = data['description']
        if 'rank' in data:
            target_rule['rank'] = data['rank']
        if 'parameters' in data:
            target_rule['parameters'] = data['parameters']
        
        # 保存
        save_project_rules(rules)
        
        return jsonify({
            'status': 'success',
            'message': f'{category_name} "{rule_id}" を更新しました',
            'data': target_rule
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'ルール更新に失敗しました: {str(e)}'
        }), 500

@facility_rules_bp.route('/api/rules/facility/<rule_id>', methods=['DELETE'])
def delete_facility_rule(rule_id):
    """
    ルール削除API（全カテゴリ対応）
    
    Args:
        rule_id: 削除対象のルールID (FR001, PR001, RR001など)
    """
    try:
        # 現在のルールを読み込み
        rules = load_project_rules()
        
        # ルールIDのプレフィックスに基づいてカテゴリを決定
        if rule_id.startswith('FR'):
            category = 'facility_rules'
            category_name = '施設ルール'
        elif rule_id.startswith('PR'):
            category = 'personal_rules'
            category_name = '個人ルール'
        elif rule_id.startswith('RR'):
            category = 'relationship_rules'
            category_name = '関係性ルール'
        else:
            return jsonify({
                'status': 'error',
                'message': f'無効なルールIDです: {rule_id}'
            }), 400
        
        # ルール検索と削除
        initial_count = len(rules[category])
        rules[category] = [rule for rule in rules[category] 
                          if rule['id'] != rule_id]  # 正しいフィールド名を使用
        
        if len(rules[category]) == initial_count:
            return jsonify({
                'status': 'error',
                'message': f'{category_name}でルールID "{rule_id}" が見つかりません'
            }), 404
        
        # 保存
        save_project_rules(rules)
        
        return jsonify({
            'status': 'success',
            'message': f'{category_name} "{rule_id}" を削除しました'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'ルール削除に失敗しました: {str(e)}'
        }), 500

@facility_rules_bp.route('/api/rules/validate', methods=['POST'])
def validate_rule():
    """
    ルール定義検証API
    
    Body: {
        'rule_definition': {...}
    }
    """
    try:
        data = request.json or {}
        rule_definition = data.get('rule_definition', {})
        
        # 基本検証
        validation_errors = []
        
        # 必須フィールド
        required_fields = ['rule_id', 'rule_name', 'description', 'rank']
        for field in required_fields:
            if field not in rule_definition:
                validation_errors.append(f'必須フィールド "{field}" が不足しています')
        
        # ランク検証
        if 'rank' in rule_definition:
            valid_ranks = ['A', 'B', 'C']
            if rule_definition['rank'] not in valid_ranks:
                validation_errors.append(f'無効なランクです。有効な値: {", ".join(valid_ranks)}')
        
        # ルールID形式検証
        if 'rule_id' in rule_definition:
            import re
            if not re.match(r'^[A-Z]{2}\d{3}$', rule_definition['rule_id']):
                validation_errors.append('ルールIDは "FR001" 形式である必要があります')
        
        if validation_errors:
            return jsonify({
                'status': 'error',
                'message': 'ルール定義に問題があります',
                'errors': validation_errors
            }), 400
        
        return jsonify({
            'status': 'success',
            'message': 'ルール定義は有効です'
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'ルール検証に失敗しました: {str(e)}'
        }), 500