"""
AutoShift - YAML読み書きハンドラー
2026年2月9日

役割:
- data/配下のYAMLファイルを読み込み
- 適切なデータモデルに変換
- ファイルの存在チェックとエラーハンドリング
"""

import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional

# プロジェクトルートからmodelsをインポート（修正版）
import sys
sys.path.append(str(Path(__file__).parent.parent))

try:
    from models import Staff, Rule, RequestHoliday
except ImportError:
    from ..models import Staff, Rule, RequestHoliday


def load_staff_list(path: str) -> List[Staff]:
    """
    staff_list.yml を読み込んでStaffオブジェクトのリストを返す
    
    Args:
        path: staff_list.yml のパス
        
    Returns:
        List[Staff]: スタッフオブジェクトのリスト
        
    Raises:
        FileNotFoundError: ファイルが見つからない場合
        yaml.YAMLError: YAML解析エラー
        KeyError: 必要なキーが不足している場合
    """
    try:
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"スタッフファイルが見つかりません: {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML format in {path}: expected dict, got {type(data)}")
            
        if 'staff' not in data:
            raise KeyError("YAMLファイルに'staff'キーがありません")
            
        # Staffオブジェクトに変換
        staff_list = []
        for staff_data in data['staff']:
            if 'id' not in staff_data or 'name' not in staff_data or 'class' not in staff_data:
                raise KeyError(f"スタッフデータに必要なフィールドが不足: {staff_data}")
                
            staff = Staff(
                id=staff_data['id'],
                name=staff_data['name'],
                staff_class=staff_data['class']  # 'class' -> 'staff_class' にマッピング
            )
            staff_list.append(staff)
            
        print(f"✅ スタッフ {len(staff_list)}名を読み込み完了")
        return staff_list
        
    except FileNotFoundError:
        raise
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML解析エラー: {e}")
    except Exception as e:
        raise Exception(f"スタッフ読み込みエラー: {e}")


def load_rules(path: str) -> Dict[str, Any]:
    """
    rules.yml を読み込んで構造化されたルールデータを返す
    
    Args:
        path: rules.yml のパス
        
    Returns:
        Dict[str, Any]: {
            'facility_rules': List[Dict],
            'personal_rules': List[Dict], 
            'relationship_rules': List[Dict]
        }
        
    Raises:
        FileNotFoundError: ファイルが見つからない場合
        yaml.YAMLError: YAML解析エラー
    """
    try:
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"ルールファイルが見つかりません: {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML format in {path}: expected dict, got {type(data)}")
            
        if 'rules' not in data:
            raise KeyError("YAMLファイルに'rules'キーがありません")
            
        rules = data['rules']
        
        # デフォルト値設定
        result = {
            'facility_rules': rules.get('facility_rules', []),
            'personal_rules': rules.get('personal_rules', []),
            'relationship_rules': rules.get('relationship_rules', [])
        }
        
        facility_count = len(result['facility_rules'])
        personal_count = len(result['personal_rules'])
        relationship_count = len(result['relationship_rules'])
        total_count = facility_count + personal_count + relationship_count
        
        print(f"✅ ルール読み込み完了 - 施設:{facility_count}, 個人:{personal_count}, 人間関係:{relationship_count} (計{total_count}ルール)")
        return result
        
    except FileNotFoundError:
        raise
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML解析エラー: {e}")
    except Exception as e:
        raise Exception(f"ルール読み込みエラー: {e}")


def load_request_holidays(path: str) -> Dict[str, Any]:
    """
    request_holidays_YYYY_MM.yml を読み込んで希望休・有給データを返す
    
    Args:
        path: request_holidays_2026_02.yml のパス
        
    Returns:
        Dict[str, Any]: {
            'month': str,
            'staff_requests': List[Dict]
        }
        
    Raises:
        FileNotFoundError: ファイルが見つからない場合
        yaml.YAMLError: YAML解析エラー
    """
    try:
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise FileNotFoundError(f"希望休ファイルが見つかりません: {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML format in {path}: expected dict, got {type(data)}")
            
        if 'month' not in data or 'staff_requests' not in data:
            raise KeyError("YAMLファイルに'month'または'staff_requests'キーがありません")
            
        # 統計情報計算
        total_requests = 0
        request_count = 0
        paid_count = 0
        
        for staff_req in data['staff_requests']:
            requests = staff_req.get('requests', [])
            total_requests += len(requests)
            
            for req in requests:
                if req.get('type') == '希':
                    request_count += 1
                elif req.get('type') == '有':
                    paid_count += 1
                    
        print(f"✅ 希望休読み込み完了 - {data['month']} (希望休:{request_count}, 有給:{paid_count}, 計:{total_requests}件)")
        return data
        
    except FileNotFoundError:
        raise
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML解析エラー: {e}")
    except Exception as e:
        raise Exception(f"希望休読み込みエラー: {e}")


def save_staff_list(path: str, staff_list: List[Staff]) -> None:
    """
    Staffオブジェクトのリストをstaff_list.ymlに保存
    
    Args:
        path: 保存先パス
        staff_list: Staffオブジェクトのリスト
    """
    try:
        data = {
            'staff': [
                {
                    'id': staff.id,
                    'name': staff.name,
                    'class': staff.staff_class
                }
                for staff in staff_list
            ]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, indent=2)
            
        print(f"✅ スタッフリスト保存完了: {path}")
        
    except Exception as e:
        raise Exception(f"スタッフリスト保存エラー: {e}")


# プロジェクト用のショートカット関数
def load_project_staff() -> List[Staff]:
    """プロジェクトのスタッフリストを読み込み"""
    project_root = Path(__file__).parent.parent
    return load_staff_list(str(project_root / "data" / "staff_list.yml"))


def load_project_rules() -> Dict[str, Any]:
    """プロジェクトのルールを読み込み"""
    project_root = Path(__file__).parent.parent
    return load_rules(str(project_root / "data" / "rules.yml"))


def load_project_request_holidays(month: str = "2026-02") -> Dict[str, Any]:
    """プロジェクトの希望休を読み込み (デフォルト: 2026-02)"""
    project_root = Path(__file__).parent.parent
    filename = f"request_holidays_{month.replace('-', '_')}.yml"
    return load_request_holidays(str(project_root / "data" / filename))


def save_rules(path: str, rules_data: Dict[str, Any]) -> None:
    """
    ルールデータをrules.ymlに保存
    
    Args:
        path: 保存先パス
        rules_data: ルールデータ辞書
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(rules_data, f, allow_unicode=True, default_flow_style=False, indent=2)
            
        print(f"✅ ルール保存完了: {path}")
        
    except Exception as e:
        raise Exception(f"ルール保存エラー: {e}")


def save_request_holidays(path: str, holidays_data: Dict[str, Any]) -> None:
    """
    希望休データをYAMLファイルに保存
    
    Args:
        path: 保存先パス
        holidays_data: 希望休データ辞書
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(holidays_data, f, allow_unicode=True, default_flow_style=False, indent=2)
            
        print(f"✅ 希望休データ保存完了: {path}")
        
    except Exception as e:
        raise Exception(f"希望休データ保存エラー: {e}")


def save_project_rules(rules_data: Dict[str, Any]) -> None:
    """プロジェクトのルールを保存"""
    project_root = Path(__file__).parent.parent
    save_rules(str(project_root / "data" / "rules.yml"), rules_data)


def save_project_request_holidays(month: str, holidays_data: Dict[str, Any]) -> None:
    """プロジェクトの希望休を保存"""
    project_root = Path(__file__).parent.parent  
    filename = f"request_holidays_{month.replace('-', '_')}.yml"
    save_request_holidays(str(project_root / "data" / filename), holidays_data)