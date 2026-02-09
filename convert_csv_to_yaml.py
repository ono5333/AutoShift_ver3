import csv
import yaml

# スタッフマスタを読み込む
yaml_path = r"c:\D\JisakuTool\AutoShift_ver3\data\staff_list.yml"
with open(yaml_path, 'r', encoding='utf-8') as f:
    staff_master = yaml.safe_load(f)

# スタッフ名とIDのマッピング
staff_name_to_id = {staff['name']: staff['id'] for staff in staff_master['staff']}

# CSVファイルを読み込む（カンマ区切り、BOM付き）
csv_path = r"c:\D\JisakuTool\AutoShift_ver3\202602_hope.csv"
with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    lines = list(reader)

# ヘッダー行（曜日）と日付行を抽出
# lines[0] = 曜日行 (1列目は空)
# lines[1] = 日付行 (1列目は "2026/02")
date_row = lines[1][1:]  # 日付を抽出

# スタッフ別の希望休を構築
staff_requests = []
for i in range(2, len(lines)):
    staff_name = lines[i][0].strip()
    
    # スタッフ名が空の場合はスキップ
    if not staff_name:
        continue
    
    # マスタから対応するスタッフIDを取得
    staff_id = staff_name_to_id.get(staff_name)
    if not staff_id:
        print(f"警告: '{staff_name}' がスタッフマスタに見つかりません")
        continue
    
    # このスタッフの希望休を抽出
    requests = []
    for j, day_str in enumerate(date_row):
        # CSVの列 j+1 (1列目はスタッフ名なので +1)
        cell_index = j + 1
        if cell_index >= len(lines[i]):
            break
        
        request_type = lines[i][cell_index].strip()
        
        # 希望休（希）または有給（有）の場合
        if request_type in ['希', '有']:
            day_num = int(day_str)
            date_str = f"2026-02-{day_num:02d}"
            requests.append({
                'date': date_str,
                'type': request_type
            })
    
    staff_requests.append({
        'staff_id': staff_id,
        'staff_name': staff_name,
        'requests': requests
    })

# YAML形式で保存
output = {
    'month': '2026-02',
    'staff_requests': staff_requests
}

with open(r"c:\D\JisakuTool\AutoShift_ver3\data\request_holidays_2026_02.yml", 'w', encoding='utf-8') as f:
    yaml.dump(output, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

print("OK: YAMLファイルを生成しました")
print(f"結果: {len(staff_requests)}名のスタッフ")
for req in staff_requests:
    print(f"  {req['staff_name']}: {len(req['requests'])}件")
