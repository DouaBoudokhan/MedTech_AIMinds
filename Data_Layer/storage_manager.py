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
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, unquote
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
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
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

    def get_chunk_by_vector_id(self, vector_id: int) -> Optional[Dict]:
        """Get chunk by its FAISS vector ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM chunks WHERE vector_id = ? LIMIT 1", (vector_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_memory_item_by_vector_id(self, vector_id: int) -> Optional[Dict]:
        """Get memory item by its FAISS vector ID (for non-chunked items)"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memory_items WHERE vector_id = ? LIMIT 1", (vector_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def resolve_text_vector_id(self, vector_id: int) -> Optional[Dict]:
        """Resolve a text FAISS vector_id to its content and metadata.
        
        Checks both chunks and memory_items tables.
        Returns dict with 'text', 'source', 'metadata', 'created_at'.
        """
        # First check chunks (chunked documents)
        chunk = self.get_chunk_by_vector_id(vector_id)
        if chunk:
            # Get parent memory item for metadata
            parent = self.get_memory_item(chunk['memory_item_id'])
            metadata = {}
            if parent:
                try:
                    metadata = json.loads(parent.get('metadata') or '{}') if parent.get('metadata') else {}
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            return {
                'text': chunk['chunk_text'],
                'source': parent.get('source', 'unknown') if parent else 'unknown',
                'metadata': metadata,
                'created_at': parent.get('created_at', '') if parent else '',
                'chunk_index': chunk.get('chunk_index', 0),
                'memory_item_id': chunk.get('memory_item_id'),
            }
        
        # Then check memory_items (non-chunked)
        item = self.get_memory_item_by_vector_id(vector_id)
        if item:
            try:
                metadata = json.loads(item.get('metadata') or '{}') if item.get('metadata') else {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
            return {
                'text': item['content'],
                'source': item.get('source', 'unknown'),
                'metadata': metadata,
                'created_at': item.get('created_at', ''),
                'memory_item_id': item.get('id'),
            }
        
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
            self.dimension = int(self.index.d)
            print(f"✅ Loaded text index: {self.index.ntotal} vectors")
        else:
            self.index = faiss.IndexFlatL2(dimension)
            self.dimension = int(self.index.d)
            print(f"✅ Created new text index ({dimension}d)")
    
    def add(self, embeddings: np.ndarray) -> List[int]:
        """Add embeddings to index"""
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)

        if embeddings.shape[1] != self.index.d:
            raise ValueError(
                f"Text embedding dim mismatch: got {embeddings.shape[1]}d, "
                f"index expects {self.index.d}d"
            )
        
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
        self._text_embedding_warning_shown = False
        self._visual_embedding_warning_shown = False
        self._text_embeddings_enabled = False
        self._ingest_error_counts = {}
        self._init_embeddings()
        self._validate_text_embedding_dimension()
        
        print("=" * 60)
        print("✅ Storage manager ready\n")

    def _text_embeddings_ready(self) -> bool:
        """Return whether text embeddings are available and compatible."""
        if self.embeddings is not None and self._text_embeddings_enabled:
            return True

        if not self._text_embedding_warning_shown:
            if self.embeddings is None:
                print("❌ Text embeddings not initialized")
            else:
                print("❌ Text embeddings disabled (model/index dimension mismatch)")
            self._text_embedding_warning_shown = True
        return False

    def _visual_embeddings_ready(self) -> bool:
        """Return whether visual embeddings are available."""
        if self.embeddings is not None:
            return True

        if not self._visual_embedding_warning_shown:
            print("❌ Visual embeddings not initialized")
            self._visual_embedding_warning_shown = True
        return False
    
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
            self._text_embeddings_enabled = True
        except Exception as e:
            print(f"⚠️  Embeddings not available: {e}")
            self.embeddings = None
            self.text_processor = None
            self._text_embeddings_enabled = False

    def _validate_text_embedding_dimension(self):
        """Ensure embedding output dimension matches loaded FAISS text index."""
        if self.embeddings is None:
            return

        try:
            probe = self.embeddings.encode_text("dimension probe")
            embed_dim = int(probe.shape[1]) if probe.ndim == 2 else int(probe.shape[0])
            index_dim = int(self.text_store.index.d)

            if embed_dim != index_dim:
                raise ValueError(
                    "Text embedding dimension mismatch: "
                    f"model produced {embed_dim}d but FAISS text index expects {index_dim}d. "
                    "Your existing index was built with a different embedding model. "
                    "Reset Data_Layer/Data_Storage/vector_store/text_index and metadata.db, then re-ingest."
                )
        except Exception as e:
            print(f"⚠️  Text embeddings disabled: {e}")
            self.text_processor = None
            self._text_embeddings_enabled = False

    @staticmethod
    def _compute_hash(value: str) -> str:
        """Compute stable SHA256 hash"""
        return hashlib.sha256(value.encode('utf-8', errors='ignore')).hexdigest()

    @staticmethod
    def _normalize_text_for_embedding(text: str, max_chars: int = 2000) -> str:
        """Normalize text to reduce embedding-model failures on noisy inputs."""
        if text is None:
            return ""

        text = str(text)
        text = text.replace("\x00", " ")
        text = re.sub(r"[\x00-\x1f\x7f]", " ", text)
        text = " ".join(text.split())
        if len(text) > max_chars:
            text = text[:max_chars]
        return text

    @staticmethod
    def _compact_url_for_embedding(raw_url: str) -> str:
        """Convert full URL into a compact semantic representation for embedding."""
        if not raw_url:
            return ""

        raw_url = str(raw_url).strip()
        parsed = urlparse(raw_url)

        # Skip schemes that often contain high-entropy payloads
        if parsed.scheme in {"data", "blob", "chrome-extension", "edge"}:
            return ""

        host = (parsed.netloc or "").lower()
        path = unquote(parsed.path or "")
        path = path.replace("/", " ").replace("-", " ").replace("_", " ")
        path = re.sub(r"\s+", " ", path).strip()

        compact = f"{host} {path}".strip()
        return compact[:600]

    @staticmethod
    def _filter_noisy_tokens(text: str) -> str:
        """Drop likely high-entropy tokens that can destabilize embedding calls."""
        if not text:
            return ""

        kept = []
        for token in text.split():
            # Drop very long tokens (often hashes/base64/query blobs)
            if len(token) > 80:
                continue

            # Drop symbol-heavy tokens
            alnum_count = sum(ch.isalnum() for ch in token)
            if len(token) >= 20 and alnum_count / max(len(token), 1) < 0.55:
                continue

            kept.append(token)

        return " ".join(kept)

    def _build_browser_search_text(self, item: Dict) -> str:
        """Build robust browser text payload for embedding from browser record."""
        title = self._normalize_text_for_embedding(item.get('title', ''), max_chars=500)
        search_query = self._normalize_text_for_embedding(item.get('search_query', ''), max_chars=400)
        url_compact = self._compact_url_for_embedding(item.get('url', ''))

        parts = [p for p in [title, search_query, url_compact] if p]
        text = " ".join(parts)
        text = self._filter_noisy_tokens(text)
        return self._normalize_text_for_embedding(text, max_chars=1000)

    def _build_browser_fallback_text(self, item: Dict) -> str:
        """Minimal fallback text for browser records if primary payload fails."""
        title = self._normalize_text_for_embedding(item.get('title', ''), max_chars=280)
        search_query = self._normalize_text_for_embedding(item.get('search_query', ''), max_chars=220)
        text = " ".join(p for p in [title, search_query] if p)
        return self._normalize_text_for_embedding(text, max_chars=500)
    
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
        if not self._text_embeddings_ready():
            return -1

        # Skip empty content early
        text = self._normalize_text_for_embedding(text)
        if not text:
            return -1

        try:
            # Deduplicate by source + normalized text
            normalized = " ".join((text or "").split())
            content_hash = self._compute_hash(f"{source}|{normalized}")
            existing = self.metadata_store.get_memory_item_by_hash(content_hash)
            if existing:
                # If vector_id is missing (legacy/partial records), do not attempt
                # synchronous repair here to avoid re-embedding stalls during ingestion.
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
                    if not np.isfinite(embedding).all():
                        raise ValueError("Non-finite values in chunk embedding")

                    # Add to vector store
                    vector_ids = self.text_store.add(embedding)

                    # Add chunk to metadata
                    self.metadata_store.add_chunk(memory_id, chunk_text, i, start_pos, end_pos, vector_ids[0])
            else:
                # Encode full text
                embedding = self.embeddings.encode_text(text)
                if not np.isfinite(embedding).all():
                    raise ValueError("Non-finite values in text embedding")

                # Add to vector store
                vector_ids = self.text_store.add(embedding)

                # Save vector_id back to memory_items so lookups work
                self.metadata_store.update_memory_item_vector_id(memory_id, vector_ids[0])

            return memory_id
        except Exception as e:
            key = f"{source}:{type(e).__name__}:{str(e)[:80]}"
            seen = self._ingest_error_counts.get(key, 0) + 1
            self._ingest_error_counts[key] = seen

            if seen <= 3:
                print(f"⚠️  Skipping text item from '{source}': {e}")
            elif seen == 4:
                print(f"⚠️  Further similar '{source}' errors suppressed...")
            return -1
    
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
            skipped = 0
            processed = 0
            progress_every = 50

            def _show_progress():
                if processed and processed % progress_every == 0:
                    print(f"   ⏳ Processed {processed} browser records (ok={count}, skipped={skipped})")
            
            # Handle nested structure: data["records_by_day"]["date"][items]
            if isinstance(data, dict) and 'records_by_day' in data:
                records_by_day = data['records_by_day']
                
                for date, records in records_by_day.items():
                    if not isinstance(records, list):
                        continue
                    for item in records:
                        if not isinstance(item, dict):
                            continue
                        processed += 1
                        text = self._build_browser_search_text(item)
                        if not text:
                            skipped += 1
                            _show_progress()
                            continue
                        
                        memory_id = self.ingest_text(text, source='browser', metadata=item)
                        if memory_id == -1:
                            fallback_text = self._build_browser_fallback_text(item)
                            if fallback_text:
                                memory_id = self.ingest_text(fallback_text, source='browser', metadata=item)

                        if memory_id != -1:
                            count += 1
                        else:
                            skipped += 1
                        _show_progress()
            
            # Handle flat list structure (backward compatibility)
            elif isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    processed += 1
                    text = self._build_browser_search_text(item)
                    if not text:
                        skipped += 1
                        _show_progress()
                        continue
                    
                    memory_id = self.ingest_text(text, source='browser', metadata=item)
                    if memory_id == -1:
                        fallback_text = self._build_browser_fallback_text(item)
                        if fallback_text:
                            memory_id = self.ingest_text(fallback_text, source='browser', metadata=item)

                    if memory_id != -1:
                        count += 1
                    else:
                        skipped += 1
                    _show_progress()
            
            self.save()
            print(f"✅ Ingested {count} browser items from {Path(json_path).name}")
            if skipped:
                print(f"⚠️  Skipped {skipped} browser items from {Path(json_path).name}")
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
        if not self._visual_embeddings_ready():
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
        results = []
        visual_min_score = 0.28
        
        # Text search
        if search_type in ['text', 'both']:
            if self._text_embeddings_ready():
                query_embedding = self.embeddings.encode_text(query)
                distances, indices = self.text_store.search(query_embedding, top_k)
            else:
                distances, indices = [], []
            
            for dist, idx in zip(distances, indices):
                if idx >= 0:  # Valid index
                    # Convert L2 distance to similarity score
                    score = 1.0 / (1.0 + dist)
                    
                    # Resolve vector ID to actual text content
                    resolved = self.metadata_store.resolve_text_vector_id(int(idx))
                    
                    result_entry = {
                        'vector_id': int(idx),
                        'score': float(score),
                        'type': 'text',
                        'distance': float(dist),
                    }
                    
                    if resolved:
                        result_entry['text'] = resolved.get('text', '')
                        result_entry['source'] = resolved.get('source', 'unknown')
                        result_entry['metadata'] = resolved.get('metadata', {})
                        result_entry['created_at'] = resolved.get('created_at', '')
                    
                    results.append(result_entry)
        
        # Visual search
        if search_type in ['visual', 'both']:
            if self._visual_embeddings_ready():
                query_embedding = self.embeddings.encode_text_for_image_search(query)
                scores, indices = self.visual_store.search(query_embedding, top_k)
            else:
                scores, indices = [], []

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
                        'type': 'visual',
                    }
                    if visual_item:
                        candidate['path'] = visual_item.get('path', '')
                        candidate['text'] = visual_item.get('ocr_text', '')
                        try:
                            candidate['metadata'] = json.loads(visual_item.get('metadata') or '{}') if visual_item.get('metadata') else {}
                        except (json.JSONDecodeError, TypeError):
                            candidate['metadata'] = {}

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
