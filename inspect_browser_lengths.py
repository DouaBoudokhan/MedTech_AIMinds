import json
from pathlib import Path

base = Path("Data_Layer/Data_Storage")
for fp in sorted(base.glob("browser_data_*.json")):
    with open(fp, "r", encoding="utf-8") as f:
        data = json.load(f)

    max_len = 0
    max_day = None
    max_i = None

    for day, records in data.get("records_by_day", {}).items():
        for i, item in enumerate(records):
            text = f"{item.get('title','')} {item.get('url','')}"
            if item.get("search_query"):
                text += f" {item.get('search_query')}"
            l = len(text)
            if l > max_len:
                max_len = l
                max_day = day
                max_i = i

    print(fp.name, "max_text_len=", max_len, "at", max_day, max_i)
