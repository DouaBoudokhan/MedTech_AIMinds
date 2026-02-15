"""
Unified Storage Manager - Dual-Vector Storage System
=====================================================

Storage architecture:
- Text embeddings: BGE-m3 via Ollama (1024d)
- Visual embeddings: CLIP (512d)  
- Metadata: SQLite
- Hierarchical: memory_items → chunks
"""

import json
import sqlite3
import traceback
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
import faiss


# Storage configuration
class StorageConfig:
    """Centralized storage configuration"""
    
    # Paths
    STORAGE_DIR = Path(__file__).parent / "Data_Storage"
    VECTOR_STORE_DIR = STORAGE_DIR / "vector_store"
    TEXT_INDEX_DIR = VECTOR_STORE_DIR / "text_index"
    VISUAL_INDEX_DIR = VECTOR_STORE_DIR / "visual_index"
    METADATA_DB = STORAGE_DIR / "metadata.db"
    
    # Embedding dimensions
    TEXT_DIM = 1024               # BGE-m3 via Ollama
    VISUAL_DIM = 512
    
    # Chunking parameters
    CHUNK_SIZE_SHORT = 512
    CHUNK_SIZE_LONG = 1500
    CHUNK_OVERLAP = 150
    
    # Model names
    TEXT_MODEL = "bge-m3"         # Served by Ollama
    VISUAL_MODEL = "openai/clip-vit-base-patch32"


class SQLiteMetadataStore:
    """SQLite database for metadata and relationships"""
    
    def __init__(self, db_path: str = None):
        """Initialize SQLite store"""
        if db_path is None:
            db_path = StorageConfig.METADATA_DB
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()
        
        # Memory items (parent documents)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                vector_id INTEGER,
                content_hash TEXT
            )
        """)
        
        # Text chunks (for long documents)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_item_id INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                start_pos INTEGER,
                end_pos INTEGER,
                vector_id INTEGER,
                FOREIGN KEY (memory_item_id) REFERENCES memory_items(id)
            )
        """)
        
        # Visual items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visual_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                ocr_text TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                vector_id INTEGER,
                image_hash TEXT
            )
        """)

        # Backward-compatible migrations for existing DBs
        try:
            cursor.execute("ALTER TABLE memory_items ADD COLUMN content_hash TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE visual_items ADD COLUMN image_hash TEXT")
        except sqlite3.OperationalError:
            pass
        
        # Create indices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON memory_items(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON memory_items(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_chunks ON chunks(memory_item_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_content_hash ON memory_items(content_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_visual_image_hash ON visual_items(image_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_visual_vector_id ON visual_items(vector_id)")
        
        self.conn.commit()
    
    def add_memory_item(self, source: str, content: str, metadata: Dict = None, content_hash: str = None) -> int:
        """Add memory item"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO memory_items (source, content, metadata, created_at, content_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (source, content, json.dumps(metadata) if metadata else None, datetime.now().isoformat(), content_hash))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def add_chunk(self, memory_item_id: int, chunk_text: str, chunk_index: int, 
                  start_pos: int, end_pos: int, vector_id: int = None) -> int:
        """Add text chunk"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO chunks (memory_item_id, chunk_text, chunk_index, start_pos, end_pos, vector_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (memory_item_id, chunk_text, chunk_index, start_pos, end_pos, vector_id))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def add_visual_item(self, path: str, ocr_text: str = None, metadata: Dict = None, vector_id: int = None, image_hash: str = None) -> int:
        """Add visual item"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO visual_items (path, ocr_text, metadata, created_at, vector_id, image_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (path, ocr_text, json.dumps(metadata) if metadata else None, datetime.now().isoformat(), vector_id, image_hash))
        
        self.conn.commit()
        return cursor.lastrowid

    def get_memory_item_by_hash(self, content_hash: str) -> Optional[Dict]:
        """Get memory item by dedup hash"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memory_items WHERE content_hash = ? LIMIT 1", (content_hash,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_visual_item_by_hash(self, image_hash: str) -> Optional[Dict]:
        """Get visual item by dedup hash"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM visual_items WHERE image_hash = ? LIMIT 1", (image_hash,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_visual_item_by_vector_id(self, vector_id: int) -> Optional[Dict]:
        """Get visual item by vector ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM visual_items WHERE vector_id = ? LIMIT 1", (vector_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    def update_memory_item_vector_id(self, item_id: int, vector_id: int):
        """Set vector_id on a memory item"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE memory_items SET vector_id = ? WHERE id = ?", (vector_id, item_id))
        self.conn.commit()

    def get_memory_item(self, item_id: int) -> Optional[Dict]:
        """Get memory item by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memory_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_chunk(self, chunk_id: int) -> Optional[Dict]:
        """Get chunk by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_stats(self) -> Dict:
        """Get storage statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM memory_items")
        memory_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM visual_items")
        visual_count = cursor.fetchone()[0]
        
        return {
            'memory_items': memory_count,
            'chunks': chunk_count,
            'visual_items': visual_count
        }


class TextVectorStore:
    """Faiss-based text vector store"""
    
    def __init__(self, index_dir: str = None, dimension: int = StorageConfig.TEXT_DIM):
        """Initialize text vector store"""
        if index_dir is None:
            index_dir = StorageConfig.TEXT_INDEX_DIR
        
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.dimension = dimension
        self.index_path = self.index_dir / "faiss_index.bin"
        
        # Load or create index
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            print(f"✅ Loaded text index: {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatL2(dimension)
            print(f"✅ Created new text index ({dimension}d)")
    
    def add(self, embeddings: np.ndarray) -> List[int]:
        """Add embeddings to index"""
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        start_id = self.index.ntotal
        self.index.add(embeddings.astype('float32'))
        
        return list(range(start_id, self.index.ntotal))
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """Search for similar vectors"""
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        distances, indices = self.index.search(query_embedding.astype('float32'), top_k)
        return distances[0], indices[0]
    
    def save(self):
        """Save index to disk"""
        faiss.write_index(self.index, str(self.index_path))
    
    def get_count(self) -> int:
        """Get number of vectors"""
        return self.index.ntotal


class VisualVectorStore:
    """Faiss-based visual vector store"""
    
    def __init__(self, index_dir: str = None, dimension: int = StorageConfig.VISUAL_DIM):
        """Initialize visual vector store"""
        if index_dir is None:
            index_dir = StorageConfig.VISUAL_INDEX_DIR
        
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        self.dimension = dimension
        self.index_path = self.index_dir / "faiss_index.bin"
        
        # Load or create index (use IndexFlatIP for cosine similarity)
        if self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            print(f"✅ Loaded visual index: {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatIP(dimension)
            print(f"✅ Created new visual index ({dimension}d)")
    
    def add(self, embeddings: np.ndarray) -> List[int]:
        """Add embeddings to index"""
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        
        start_id = self.index.ntotal
        self.index.add(embeddings.astype('float32'))
        
        return list(range(start_id, self.index.ntotal))
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """Search for similar vectors"""
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        scores, indices = self.index.search(query_embedding.astype('float32'), top_k)
        return scores[0], indices[0]
    
    def save(self):
        """Save index to disk"""
        faiss.write_index(self.index, str(self.index_path))
    
    def get_count(self) -> int:
        """Get number of vectors"""
        return self.index.ntotal


class UnifiedStorageManager:
    """Main storage interface - orchestrates all storage components"""
    
    def __init__(self):
        """Initialize unified storage manager"""
        print("\n🔧 Initializing Unified Storage Manager")
        print("=" * 60)
        
        # Initialize components
        self.metadata_store = SQLiteMetadataStore()
        self.text_store = TextVectorStore()
        self.visual_store = VisualVectorStore()
        
        # Initialize embedding models
        self._init_embeddings()
        
        print("=" * 60)
        print("✅ Storage manager ready\n")
    
    def _init_embeddings(self):
        """Initialize embedding models"""
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent / "Core"))
            
            from embeddings import EmbeddingManager
            from text_processor import TextProcessor
            
            self.embeddings = EmbeddingManager()
            self.text_processor = TextProcessor()
        except Exception as e:
            print(f"⚠️  Embeddings not available: {e}")
            self.embeddings = None
            self.text_processor = None

    @staticmethod
    def _compute_hash(value: str) -> str:
        """Compute stable SHA256 hash"""
        return hashlib.sha256(value.encode('utf-8', errors='ignore')).hexdigest()
    
    def ingest_text(self, text: str, source: str, metadata: Dict = None) -> int:
        """
        Ingest text document
        
        Args:
            text: Text content
            source: Source identifier
            metadata: Optional metadata
            
        Returns:
            Memory item ID
        """
        if self.embeddings is None:
            print("❌ Embeddings not initialized")
            return -1

        # Deduplicate by source + normalized text
        normalized = " ".join((text or "").split())
        content_hash = self._compute_hash(f"{source}|{normalized}")
        existing = self.metadata_store.get_memory_item_by_hash(content_hash)
        if existing:
            # If vector_id was never written (legacy data), repair it now
            if existing.get('vector_id') is None:
                embedding = self.embeddings.encode_text(text)
                vector_ids = self.text_store.add(embedding)
                self.metadata_store.update_memory_item_vector_id(int(existing['id']), vector_ids[0])
            return int(existing['id'])
        
        # Add memory item
        memory_id = self.metadata_store.add_memory_item(source, text, metadata, content_hash=content_hash)
        
        # Check if chunking needed
        if self.text_processor.should_chunk(text):
            # Chunk text
            chunks = self.text_processor.chunk_text(text)
            
            for i, (chunk_text, start_pos, end_pos) in enumerate(chunks):
                # Encode chunk
                embedding = self.embeddings.encode_text(chunk_text)
                
                # Add to vector store
                vector_ids = self.text_store.add(embedding)
                
                # Add chunk to metadata
                self.metadata_store.add_chunk(memory_id, chunk_text, i, start_pos, end_pos, vector_ids[0])
        else:
            # Encode full text
            embedding = self.embeddings.encode_text(text)
            
            # Add to vector store
            vector_ids = self.text_store.add(embedding)
            
            # Save vector_id back to memory_items so lookups work
            self.metadata_store.update_memory_item_vector_id(memory_id, vector_ids[0])
        
        return memory_id
    
    def ingest_browser_data(self, json_path: str) -> int:
        """
        Ingest browser data from JSON file
        
        Args:
            json_path: Path to browser data JSON
            
        Returns:
            Number of items ingested
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            count = 0
            
            # Handle nested structure: data["records_by_day"]["date"][items]
            if isinstance(data, dict) and 'records_by_day' in data:
                records_by_day = data['records_by_day']
                
                for date, records in records_by_day.items():
                    if not isinstance(records, list):
                        continue
                    for item in records:
                        if not isinstance(item, dict):
                            continue
                        # Combine title and URL for search
                        text = f"{item.get('title', '')} {item.get('url', '')}"
                        
                        # Add search query if available
                        if 'search_query' in item and item['search_query']:
                            text += f" {item['search_query']}"
                        
                        self.ingest_text(text, source='browser', metadata=item)
                        count += 1
            
            # Handle flat list structure (backward compatibility)
            elif isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    text = f"{item.get('title', '')} {item.get('url', '')}"
                    
                    if 'search_query' in item and item['search_query']:
                        text += f" {item['search_query']}"
                    
                    self.ingest_text(text, source='browser', metadata=item)
                    count += 1
            
            self.save()
            print(f"✅ Ingested {count} browser items from {Path(json_path).name}")
            return count
        
        except Exception as e:
            print(f"❌ Error ingesting browser data from {Path(json_path).name}: {type(e).__name__}: {e!r}")
            traceback.print_exc()
            return 0
    
    def ingest_image(self, image_path: str, ocr_text: str = None, metadata: Dict = None) -> int:
        """
        Ingest image
        
        Args:
            image_path: Path to image
            ocr_text: Optional OCR text
            metadata: Optional metadata
            
        Returns:
            Visual item ID
        """
        if self.embeddings is None:
            print("❌ Embeddings not initialized")
            return -1
        
        try:
            image_path_resolved = str(Path(image_path).resolve())
            image_file = Path(image_path_resolved)
            stat = image_file.stat()
            image_hash = self._compute_hash(f"{image_path_resolved}|{stat.st_size}|{int(stat.st_mtime)}")

            # Deduplicate image ingestion by path+file state
            existing = self.metadata_store.get_visual_item_by_hash(image_hash)
            if existing:
                return int(existing['id'])

            # Encode image
            embedding = self.embeddings.encode_image(image_path_resolved)
            
            # Add to visual store
            vector_ids = self.visual_store.add(embedding)
            
            # Add to metadata
            visual_id = self.metadata_store.add_visual_item(image_path_resolved, ocr_text, metadata, vector_ids[0], image_hash=image_hash)
            
            # If OCR text available, also add to text store
            if ocr_text:
                self.ingest_text(ocr_text, source='image_ocr', metadata={'image_path': image_path})
            
            return visual_id
        
        except Exception as e:
            print(f"❌ Error ingesting image: {e}")
            return -1
    
    def search(self, query: str, top_k: int = 5, search_type: str = 'text') -> List[Dict]:
        """
        Search storage
        
        Args:
            query: Search query
            top_k: Number of results
            search_type: 'text', 'visual', or 'both'
            
        Returns:
            List of results with scores
        """
        if self.embeddings is None:
            print("❌ Embeddings not initialized")
            return []
        
        results = []
        visual_min_score = 0.22
        
        # Text search
        if search_type in ['text', 'both']:
            query_embedding = self.embeddings.encode_text(query)
            distances, indices = self.text_store.search(query_embedding, top_k)
            
            for dist, idx in zip(distances, indices):
                if idx >= 0:  # Valid index
                    # Convert L2 distance to similarity score
                    score = 1.0 / (1.0 + dist)
                    
                    results.append({
                        'vector_id': int(idx),
                        'score': float(score),
                        'type': 'text',
                        'distance': float(dist)
                    })
        
        # Visual search
        if search_type in ['visual', 'both']:
            query_embedding = self.embeddings.encode_text_for_image_search(query)
            scores, indices = self.visual_store.search(query_embedding, top_k)

            best_by_path = {}
            for score, idx in zip(scores, indices):
                if idx >= 0:  # Valid index
                    score = float(score)
                    if score < visual_min_score:
                        continue

                    visual_item = self.metadata_store.get_visual_item_by_vector_id(int(idx))
                    path_key = visual_item['path'] if visual_item and visual_item.get('path') else f"vector:{int(idx)}"

                    current = best_by_path.get(path_key)
                    candidate = {
                        'vector_id': int(idx),
                        'score': score,
                        'type': 'visual'
                    }

                    if current is None or score > current['score']:
                        best_by_path[path_key] = candidate

            results.extend(best_by_path.values())
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:top_k]
    
    def save(self):
        """Save all indices to disk"""
        self.text_store.save()
        self.visual_store.save()
        print("💾 Saved vector stores")
    
    def get_stats(self) -> Dict:
        """Get storage statistics"""
        metadata_stats = self.metadata_store.get_stats()
        
        return {
            **metadata_stats,
            'text_vectors': self.text_store.get_count(),
            'visual_vectors': self.visual_store.get_count()
        }
    
    def print_stats(self):
        """Print storage statistics"""
        stats = self.get_stats()
        
        print("\n📊 Storage Statistics")
        print("=" * 60)
        print(f"Memory Items:   {stats['memory_items']:,}")
        print(f"Text Chunks:    {stats['chunks']:,}")
        print(f"Visual Items:   {stats['visual_items']:,}")
        print(f"Text Vectors:   {stats['text_vectors']:,}")
        print(f"Visual Vectors: {stats['visual_vectors']:,}")
        print("=" * 60 + "\n")


def main():
    """Test storage manager"""
    print("\n🧪 Testing Unified Storage Manager\n")
    
    manager = UnifiedStorageManager()
    
    # Test text ingestion
    print("\n📝 Testing Text Ingestion:")
    manager.ingest_text(
        "This is a test document about AI and machine learning.",
        source="test",
        metadata={"category": "test"}
    )
    
    # Test search
    print("\n🔍 Testing Search:")
    results = manager.search("AI machine learning", top_k=3)
    print(f"Found {len(results)} results")
    for r in results:
        print(f"  - Score: {r['score']:.3f}, Type: {r['type']}")
    
    # Show stats
    manager.print_stats()
    
    # Save
    manager.save()


if __name__ == "__main__":
    main()
