import json
import traceback
from Data_Layer.storage_manager import UnifiedStorageManager

manager = UnifiedStorageManager()
path = "Data_Layer/Data_Storage/browser_data_2026_02.json"

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

records_by_day = data.get("records_by_day", {})
checked = 0

for day, records in records_by_day.items():
    for index, item in enumerate(records):
        checked += 1
        try:
            text = f"{item.get('title', '')} {item.get('url', '')}"
            if item.get("search_query"):
                text += f" {item.get('search_query')}"
            manager.ingest_text(text, source="browser", metadata=item)
        except Exception as exc:
            print("FAIL", day, index, repr(exc))
            traceback.print_exc()
            raise

print(f"OK total {checked}")
