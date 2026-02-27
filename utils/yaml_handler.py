"""
AutoShift - YAML読み書きハンドラー
2026年2月9日

役割:
- data/配下のYAMLファイルを読み込み
- 適切なデータモデルに変換
- ファイルの存在チェックとエラーハンドリング
"""

import yaml
import csv
import calendar
from pathlib import Path
from datetime import datetime
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
                staff_class=staff_data['class'],  # 'class' -> 'staff_class' にマッピング
                employment_type=staff_data.get('employment_type', '正社員')
            )
            staff_list.append(staff)
            
        print(f"[OK] スタッフ {len(staff_list)}名を読み込み完了")
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
        
        # 新しいYAML構造に対応：直接トップレベルにルールカテゴリがある
        # 古い構造との互換性も保つ
        if 'rules' in data:
            # 古い構造: rules -> facility_rules, etc.
            rules = data['rules']
        else:
            # 新しい構造: 直接 facility_rules, etc.
            rules = data
        
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
        
        print(f"[OK] ルール読み込み完了 - 施設:{facility_count}, 個人:{personal_count}, 人間関係:{relationship_count} (計{total_count}ルール)")
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
                    
        print(f"[OK] 希望休読み込み完了 - {data['month']} (希望休:{request_count}, 有給:{paid_count}, 計:{total_requests}件)")
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
                    'class': staff.staff_class,
                    'employment_type': getattr(staff, 'employment_type', '正社員')
                }
                for staff in staff_list
            ]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, indent=2)
            
        print(f"[OK] スタッフリスト保存完了: {path}")
        
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
    """プロジェクトの希望休を読み込み (デフォルト: 2026-02)。
    優先順:
    1) data/request_holidays/YYYY/request_holidays_YYYY_MM.yml
    2) 旧: data/request_holidays_YYYY_MM.yml
    """
    project_root = Path(__file__).parent.parent
    year = month.split('-')[0]
    filename = f"request_holidays_{month.replace('-', '_')}.yml"
    new_path = project_root / "data" / "request_holidays" / year / filename
    old_path = project_root / "data" / filename

    if new_path.exists():
        return load_request_holidays(str(new_path))
    if old_path.exists():
        return load_request_holidays(str(old_path))

    # 初回作成前は空の月データを返す
    return {
        'month': month,
        'staff_requests': []
    }


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
            
        print(f"[OK] ルール保存完了: {path}")
        
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
            
        print(f"[OK] 希望休データ保存完了: {path}")
        
    except Exception as e:
        raise Exception(f"希望休データ保存エラー: {e}")


def save_project_rules(rules_data: Dict[str, Any]) -> None:
    """プロジェクトのルールを保存"""
    project_root = Path(__file__).parent.parent
    save_rules(str(project_root / "data" / "rules.yml"), rules_data)


def save_project_request_holidays(month: str, holidays_data: Dict[str, Any]) -> None:
    """プロジェクトの希望休を保存（新パスへ保存）。"""
    project_root = Path(__file__).parent.parent
    year = month.split('-')[0]
    filename = f"request_holidays_{month.replace('-', '_')}.yml"
    target_dir = project_root / "data" / "request_holidays" / year
    target_dir.mkdir(parents=True, exist_ok=True)
    save_request_holidays(str(target_dir / filename), holidays_data)


def load_project_month_end_carryover() -> Dict[str, Any]:
    """前月末引継ぎデータを読み込む。未作成時は空構造を返す。"""
    project_root = Path(__file__).parent.parent
    path = project_root / "data" / "month_end_carryover.yml"
    if not path.exists():
        return {"carryover": {}}
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {"carryover": {}}
    if 'carryover' not in data or not isinstance(data.get('carryover'), dict):
        data['carryover'] = {}
    return data


def save_project_month_end_carryover(data: Dict[str, Any]) -> None:
    """前月末引継ぎデータを保存する。"""
    project_root = Path(__file__).parent.parent
    path = project_root / "data" / "month_end_carryover.yml"
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, indent=2)


def _carryover_month_file_path(month: str) -> Path:
    project_root = Path(__file__).parent.parent
    year = month.split('-')[0]
    filename = f"month_end_carryover_{month.replace('-', '_')}.yml"
    return project_root / "data" / "carryover" / year / filename


def load_project_month_end_carryover_for_month(month: str) -> Dict[str, Any]:
    """対象月専用のcarryoverを読み込む。"""
    path = _carryover_month_file_path(month)
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def save_project_month_end_carryover_for_month(month: str, data: Dict[str, Any]) -> None:
    """対象月専用のcarryoverを保存する。未作成時は新規作成。"""
    path = _carryover_month_file_path(month)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False, indent=2)


def load_project_carryover_for_month(month: str) -> Dict[str, Any]:
    """指定月の前月末引継ぎ情報を返す。
    優先順:
    1) data/history/shift_history_YYYY_MM.csv
    2) 互換: data/carryover/YYYY/shift_history_YYYY_MM.csv
    3) 互換: data/carryover/YYYY/month_end_carryover_YYYY_MM.yml
    4) 互換: data/month_end_carryover.yml の carryover.<month>
    """
    # CSV履歴優先: data/history/shift_history_YYYY_MM.csv
    # 互換フォールバック: data/carryover/YYYY/shift_history_YYYY_MM.csv
    try:
        target_dt = datetime.strptime(month, "%Y-%m")
        prev_year = target_dt.year if target_dt.month > 1 else target_dt.year - 1
        prev_month = target_dt.month - 1 if target_dt.month > 1 else 12
        prev_token = f"{prev_year:04d}_{prev_month:02d}"
        last_day = calendar.monthrange(prev_year, prev_month)[1]
        last_day_header = f"{prev_month:02d}/{last_day:02d}"

        project_root = Path(__file__).parent.parent
        primary_csv = project_root / "data" / "history" / f"shift_history_{prev_token}.csv"
        fallback_csv = project_root / "data" / "carryover" / f"{prev_year:04d}" / f"shift_history_{prev_token}.csv"
        csv_path = primary_csv if primary_csv.exists() else fallback_csv
        if not csv_path.exists():
            return {}

        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        if not rows:
            return {}

        header = rows[0]
        last_col_idx = None
        for i, col in enumerate(header):
            col_str = str(col or '').strip()
            if col_str.startswith(last_day_header):
                last_col_idx = i
                break
        if last_col_idx is None:
            return {}

        prev_month_last_shifts: Dict[str, str] = {}
        for row in rows[1:]:
            if not row or not str(row[0]).strip().isdigit():
                continue
            if len(row) <= last_col_idx:
                continue
            staff_id = str(int(str(row[0]).strip()))
            shift_label = str(row[last_col_idx]).strip()
            if shift_label in {'日', '夜', '明', '休', '希', '有'}:
                prev_month_last_shifts[staff_id] = shift_label

        if not prev_month_last_shifts:
            # CSVが存在しても有効データが無い場合は次のフォールバックへ
            pass
        else:
            night_staff_ids = sorted([
                int(sid) for sid, shift_label in prev_month_last_shifts.items()
                if shift_label == '夜'
            ])
            return {
                'source': 'history_csv',
                'night_staff_ids': night_staff_ids,
                'prev_month_last_shifts': prev_month_last_shifts
            }
    except Exception:
        pass

    month_data = load_project_month_end_carryover_for_month(month)
    if isinstance(month_data, dict) and month_data:
        return month_data

    all_data = load_project_month_end_carryover()
    carryover = all_data.get('carryover', {}) if isinstance(all_data, dict) else {}
    entry = carryover.get(month) if isinstance(carryover, dict) else None
    if isinstance(entry, dict) and entry:
        return entry

    try:
        # 旧ロジックの安全弁（空返却）
        return {}
    except Exception:
        return {}
