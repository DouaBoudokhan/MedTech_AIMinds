"""
Query vs Stored Embeddings Test
===============================

Usage examples:
  python test_query_against_store.py --query "machine learning" --type text --top-k 5
  python test_query_against_store.py --query "cat photo" --type visual --top-k 5
  python test_query_against_store.py --query "project report" --type both --top-k 5
"""

import argparse
import sqlite3
from pathlib import Path

from Data_Layer.storage_manager import UnifiedStorageManager, StorageConfig


def fetch_text_metadata_by_vector_id(vector_id: int):
    """Try to recover text metadata from SQLite for a text vector_id."""
    db_path = Path(StorageConfig.METADATA_DB)
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Prefer chunk mapping (long documents)
    cur.execute(
        """
        SELECT c.id, c.chunk_text, c.memory_item_id, m.source, m.created_at
        FROM chunks c
        JOIN memory_items m ON m.id = c.memory_item_id
        WHERE c.vector_id = ?
        LIMIT 1
        """,
        (vector_id,),
    )
    row = cur.fetchone()
    if row:
        conn.close()
        text = row["chunk_text"] or ""
        return {
            "kind": "chunk",
            "source": row["source"],
            "created_at": row["created_at"],
            "preview": text[:220] + ("..." if len(text) > 220 else ""),
        }

    # Fallback: direct memory item mapping (if vector_id is populated there)
    cur.execute(
        """
        SELECT id, source, content, created_at
        FROM memory_items
        WHERE vector_id = ?
        LIMIT 1
        """,
        (vector_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row:
        text = row["content"] or ""
        return {
            "kind": "memory_item",
            "source": row["source"],
            "created_at": row["created_at"],
            "preview": text[:220] + ("..." if len(text) > 220 else ""),
        }

    return None


def fetch_visual_metadata_by_vector_id(vector_id: int):
    """Recover visual metadata from SQLite for a visual vector_id."""
    db_path = Path(StorageConfig.METADATA_DB)
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT path, ocr_text, created_at
        FROM visual_items
        WHERE vector_id = ?
        LIMIT 1
        """,
        (vector_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    ocr_text = row["ocr_text"] or ""
    return {
        "path": row["path"],
        "created_at": row["created_at"],
        "ocr_preview": ocr_text[:220] + ("..." if len(ocr_text) > 220 else ""),
    }


def run_query_test(query: str, search_type: str, top_k: int):
    print("\n" + "=" * 72)
    print("🧪 Query vs Stored Embeddings Test")
    print("=" * 72)
    print(f"Query: {query}")
    print(f"Type: {search_type}")
    print(f"Top-K: {top_k}")

    manager = UnifiedStorageManager()

    print("\n🔍 Comparing query embedding with stored vectors...")
    results = manager.search(query=query, top_k=top_k, search_type=search_type)

    if not results:
        print("\nNo results found.")
        return

    print(f"\n✅ Found {len(results)} matches")
    print("-" * 72)

    for i, result in enumerate(results, start=1):
        r_type = result.get("type", "unknown")
        vector_id = result.get("vector_id", -1)
        score = result.get("score", 0.0)

        print(f"[{i}] type={r_type} | vector_id={vector_id} | score={score:.4f}")

        if r_type == "text":
            distance = result.get("distance")
            if distance is not None:
                print(f"    distance={distance:.4f}")

            meta = fetch_text_metadata_by_vector_id(vector_id)
            if meta:
                print(f"    source={meta['source']} | from={meta['kind']} | created_at={meta['created_at']}")
                print(f"    preview={meta['preview']}")
            else:
                print("    metadata=not found for this vector_id")

        elif r_type == "visual":
            meta = fetch_visual_metadata_by_vector_id(vector_id)
            if meta:
                print(f"    path={meta['path']}")
                print(f"    created_at={meta['created_at']}")
                if meta["ocr_preview"]:
                    print(f"    ocr_preview={meta['ocr_preview']}")
            else:
                print("    metadata=not found for this vector_id")

        print("-" * 72)


def parse_args():
    parser = argparse.ArgumentParser(description="Embed a query and compare with stored FAISS vectors.")
    parser.add_argument("--query", required=True, help="Query text to embed and search")
    parser.add_argument("--type", default="text", choices=["text", "visual", "both"], help="Search space")
    parser.add_argument("--top-k", type=int, default=5, help="Number of nearest results")
    return parser.parse_args()


def main():
    args = parse_args()
    run_query_test(query=args.query, search_type=args.type, top_k=args.top_k)


if __name__ == "__main__":
    main()
