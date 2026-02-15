import json
from Data_Layer.storage_manager import UnifiedStorageManager

m = UnifiedStorageManager()
p = 'Data_Layer/Data_Storage/browser_data_2026_02.json'

with open(p, 'r', encoding='utf-8') as f:
    d = json.load(f)

records_by_day = d['records_by_day']
first_day = next(iter(records_by_day))
first_item = records_by_day[first_day][0]

text = f"{first_item.get('title', '')} {first_item.get('url', '')}"
if first_item.get('search_query'):
    text += f" {first_item.get('search_query')}"

print('day', first_day)
print('text_len', len(text))
mid = m.ingest_text(text, source='browser', metadata=first_item)
print('ingest_ok', mid)
