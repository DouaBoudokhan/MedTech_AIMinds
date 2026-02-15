import json
from pathlib import Path

base = Path("Data_Layer/Data_Storage")
files = sorted(base.glob("browser_data_*.json"))

for fp in files:
    print(f"\n--- {fp.name} ---")
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        print("top-level not dict:", type(data).__name__)
        continue

    records_by_day = data.get("records_by_day")
    print("records_by_day type:", type(records_by_day).__name__)

    bad_days = 0
    bad_records = 0
    total = 0

    if isinstance(records_by_day, dict):
        for day, records in records_by_day.items():
            if not isinstance(records, list):
                bad_days += 1
                continue
            for i, item in enumerate(records):
                total += 1
                if not isinstance(item, dict):
                    bad_records += 1
                    continue
                if "title" not in item or "url" not in item:
                    pass

    print("total records:", total)
    print("bad days:", bad_days)
    print("bad records:", bad_records)
