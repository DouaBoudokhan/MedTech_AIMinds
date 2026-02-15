"""Quick debug script to inspect DB state - delete after use"""
import sqlite3
from pathlib import Path

db = Path("Data_Layer/Data_Storage/metadata.db")
if not db.exists():
    print("DB does not exist!")
    exit()

conn = sqlite3.connect(str(db))
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check memory_items with and without vector_id
cur.execute("SELECT COUNT(*) as total FROM memory_items")
total = cur.fetchone()["total"]
cur.execute("SELECT COUNT(*) as c FROM memory_items WHERE vector_id IS NOT NULL")
with_vid = cur.fetchone()["c"]
cur.execute("SELECT COUNT(*) as c FROM memory_items WHERE vector_id IS NULL")
without_vid = cur.fetchone()["c"]
print(f"memory_items: total={total}, with vector_id={with_vid}, without vector_id={without_vid}")

# Check chunks
cur.execute("SELECT COUNT(*) as total FROM chunks")
total_chunks = cur.fetchone()["total"]
cur.execute("SELECT COUNT(*) as c FROM chunks WHERE vector_id IS NOT NULL")
chunks_vid = cur.fetchone()["c"]
print(f"chunks: total={total_chunks}, with vector_id={chunks_vid}")

# Show first 5 memory_items
print("\nSample memory_items (first 5):")
cur.execute("SELECT id, source, vector_id, substr(content,1,100) as preview FROM memory_items LIMIT 5")
for r in cur.fetchall():
    print(f"  id={r['id']} src={r['source']} vid={r['vector_id']} preview={r['preview']}")

# Look up the specific vector IDs from the failing query
print("\nLooking up vector_id=4, 691, 692:")
for vid in [4, 691, 692]:
    cur.execute("SELECT id, source, vector_id, substr(content,1,100) as preview FROM memory_items WHERE vector_id=? LIMIT 1", (vid,))
    row = cur.fetchone()
    if row:
        print(f"  memory_items vid={vid} -> id={row['id']} src={row['source']} preview={row['preview']}")
    else:
        print(f"  memory_items vid={vid} -> NOT FOUND")

    cur.execute("SELECT id, memory_item_id, vector_id, substr(chunk_text,1,100) as preview FROM chunks WHERE vector_id=? LIMIT 1", (vid,))
    row = cur.fetchone()
    if row:
        print(f"  chunks vid={vid} -> chunk_id={row['id']} mem_id={row['memory_item_id']} preview={row['preview']}")
    else:
        print(f"  chunks vid={vid} -> NOT FOUND")

# Check FAISS vector count
from Data_Layer.storage_manager import StorageConfig
import faiss

text_idx = StorageConfig.TEXT_INDEX_DIR / "faiss_index.bin"
if text_idx.exists():
    idx = faiss.read_index(str(text_idx))
    print(f"\nFAISS text index: {idx.ntotal} vectors, dim={idx.d}")
else:
    print("\nFAISS text index does not exist")

# Count memory items that SHOULD have vector_id (non-chunked = no child chunks)
cur.execute("""
    SELECT m.id, m.vector_id, substr(m.content,1,80) as preview
    FROM memory_items m
    WHERE m.id NOT IN (SELECT DISTINCT memory_item_id FROM chunks)
    AND m.vector_id IS NULL
    LIMIT 10
""")
rows = cur.fetchall()
print(f"\nNon-chunked memory_items with NULL vector_id (first 10 of problem rows):")
for r in rows:
    print(f"  id={r['id']} vid={r['vector_id']} preview={r['preview']}")

cur.execute("""
    SELECT COUNT(*) as c
    FROM memory_items m
    WHERE m.id NOT IN (SELECT DISTINCT memory_item_id FROM chunks)
    AND m.vector_id IS NULL
""")
print(f"Total non-chunked items with NULL vector_id: {cur.fetchone()['c']}")

conn.close()
