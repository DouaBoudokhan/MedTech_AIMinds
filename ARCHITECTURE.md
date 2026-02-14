# AI MINDS - System Architecture

## 📋 Architecture Analysis & Recommendations

### ✅ **SOLID FOUNDATION - Your Architecture is Well-Designed**

**Strengths:**

1. ✅ **Clear separation of concerns** (Input → Processing → Storage)
2. ✅ **Dual-collection strategy** (text 384d + visual 512d) - optimal for multimodal
3. ✅ **Intelligent chunking** - handles both short and long documents
4. ✅ **Hierarchical storage** (memory_items → chunks) - efficient for retrieval
5. ✅ **OCR integration** - images searchable both visually AND textually
6. ✅ **Scalable** - Faiss can handle millions of vectors

**Minor Improvements:**

1. ⚠️ **Audio → CLIP?** - CLIP is for images/text, not needed for audio transcripts
   - **Fix**: Audio → Whisper → transcript → text_collection (no CLIP)
2. ✅ **Neo4j addition** - EXCELLENT idea for relationship mapping
   - Use SQLite for fast lookups, Neo4j for graph traversal
   - Keep entities/categories in SQLite, complex relationships in Neo4j

---

## 🏗️ Final Recommended Architecture

### **INPUT PROCESSING PIPELINE**

```
├─→ Text (email, calendar, clipboard, browser)
│   └─→ Length check
│       ├─ Short (< 512 chars) → Single embedding → text_collection (384d)
│       └─ Long (> 512 chars) → Semantic chunking → Multiple embeddings → text_collection
│
├─→ Images (screenshots, photos, clipboard images)
│   ├─→ CLIP encoder → visual_collection (512d)
│   └─→ OCR (pytesseract/EasyOCR) → text → embedding → text_collection (384d)
│
├─→ Audio (voice recordings)
│   └─→ Whisper (tiny/base) → transcript → chunk if long → text_collection (384d)
│
└─→ Documents (PDFs, DOCX)
    └─→ Extract text → Semantic chunking → Multiple embeddings → text_collection (384d)
```

### **STORAGE LAYER**

```
├─→ FAISS (Vector Search)
│   ├─ text_collection (384d) - Sentence-Transformers multilingual
│   └─ visual_collection (512d) - CLIP ViT-B/32
│
├─→ SQLite (Metadata & Fast Lookups)
│   ├─ memory_items (parent documents)
│   ├─ chunks (text chunks with FK to memory_items)
│   ├─ entities (people, places, organizations)
│   └─ categories (classifications)
│
└─→ Neo4j [OPTIONAL] (Relationship Graph)
    ├─ Document nodes (mirror memory_items)
    ├─ Entity nodes (people, places, concepts)
    └─ Relationships (MENTIONED_IN, RELATED_TO, FOLLOWS, PRECEDES)
```

### **WHEN TO USE NEO4J vs SQLite**

**Use SQLite for:**

- ✅ Metadata lookups (by ID, timestamp, source_type)
- ✅ Simple parent-child (memory_item → chunks)
- ✅ Fast existence checks
- ✅ Counting, aggregations

**Use Neo4j for:**

- ✅ "Find all documents related to person X"
- ✅ "What meetings happened before this email?"
- ✅ "Show me the chain of documents about project Y"
- ✅ Network analysis (who collaborates with whom)
- ✅ Temporal graphs (timeline of events)

**Verdict:** Neo4j is **worth it** if you need:

- Temporal reasoning (before/after relationships)
- Entity co-occurrence networks
- Multi-hop queries ("friends of friends")

**Skip Neo4j if:** You only need simple lookups and vector search.

---

## 📁 Project Structure

```
AI minds/
│
├── Data_Layer/                          # Data ingestion & storage
│   ├── Data_Collection/                 # Input processors
│   │   ├── Browser/
│   │   │   ├── browser_ingestion.py    ✅ DONE
│   │   │   └── test_browser_ingestion.py
│   │   ├── Calendar/
│   │   │   └── calendar_watcher.py     📝 TODO
│   │   ├── Clipboard/
│   │   │   └── clipboard_watcher.py    📝 TODO
│   │   ├── Email/
│   │   │   └── email_watcher.py        📝 TODO
│   │   ├── File_System/
│   │   │   ├── activity_monitor.py     📝 TODO
│   │   │   └── document_extractor.py   📝 TODO
│   │   ├── Screenshots/
│   │   │   └── screenshot_watcher.py   📝 TODO
│   │   └── Audio/
│   │       └── audio_recorder.py       📝 TODO
│   │
│   ├── Data_Storage/                    # Persistent storage
│   │   ├── vector_store/
│   │   │   ├── text_index/
│   │   │   │   ├── faiss_index.bin
│   │   │   │   ├── id_mapping.pkl
│   │   │   │   └── metadata.db
│   │   │   └── visual_index/
│   │   │       ├── faiss_index.bin
│   │   │       ├── id_mapping.pkl
│   │   │       └── metadata.db
│   │   ├── browser_data_2026_01.json   ✅ DONE
│   │   └── browser_data_2026_02.json   ✅ DONE
│   │
│   └── storage_manager.py               ✅ DONE (enhanced)
│
├── Core/                                # Processing engines
│   ├── __init__.py
│   ├── embeddings.py                    # Sentence-Transformers & CLIP
│   ├── text_processor.py                # Chunking, length detection
│   ├── image_processor.py               # OCR, CLIP encoding
│   ├── audio_processor.py               # Whisper transcription
│   ├── document_processor.py            # PDF, DOCX extraction
│   ├── entity_extractor.py              # Named entity recognition
│   ├── llm_manager.py                   # Local LLM (<4B params)
│   ├── rag_engine.py                    # RAG pipeline
│   └── neo4j_manager.py [OPTIONAL]      # Graph relationships
│
├── API/                                 # User interfaces
│   ├── __init__.py
│   ├── chat_interface.py                # Interactive chat
│   └── web_ui.py [OPTIONAL]             # Gradio/Streamlit UI
│
├── Tests/                               # Testing
│   ├── __init__.py
│   ├── test_storage.py
│   ├── test_embeddings.py
│   └── test_rag.py
│
├── main_daemon.py                       # Background watcher daemon
├── pyproject.toml                       # UV dependencies
├── README.md
└── ARCHITECTURE.md                      # This file
```

---

## 🔧 Technology Stack

### **Vector Storage**

- **Faiss-CPU** (1.7.4+): L2 for text, IP for visual
- Collections: `text_collection` (384d), `visual_collection` (512d)

### **Embeddings**

- **Text**: `paraphrase-multilingual-MiniLM-L12-v2` (118M, 384d, FR+EN)
- **Vision**: `openai/clip-vit-base-patch32` (151M, 512d)

### **Processing**

- **OCR**: `pytesseract` or `easyocr`
- **Audio**: `openai/whisper-tiny` or `whisper-base` (<1B params)
- **Documents**: `PyPDF2`, `python-docx`
- **NER**: `spacy` (fr_core_news_sm, en_core_web_sm)

### **LLM (Local <4B params)**

- **Phi-2** (2.7B) - Microsoft, best reasoning
- **TinyLlama** (1.1B) - Fast, good quality
- **MobileLLM** (350M-1B) - Ultra-efficient

### **Database**

- **SQLite**: Built-in, metadata
- **Neo4j** [Optional]: Graph relationships

---

## 🚀 Implementation Priority

### **Phase 1: Core Storage** ✅ DONE

- [x] Browser ingestion
- [x] Storage manager (Faiss + SQLite)
- [x] Text embeddings
- [x] Visual embeddings
- [x] Chunking system

### **Phase 2: Additional Data Sources** 📝 IN PROGRESS

- [ ] Calendar watcher
- [ ] Clipboard watcher
- [ ] File system monitor
- [ ] Screenshot capture

### **Phase 3: Processing Engines**

- [ ] OCR for images
- [ ] Audio transcription (Whisper)
- [ ] Document extraction (PDF/DOCX)
- [ ] Entity extraction (NER)

### **Phase 4: RAG & LLM**

- [ ] Embeddings manager
- [ ] RAG engine
- [ ] Local LLM integration (Phi-2)
- [ ] Query understanding

### **Phase 5: User Interface**

- [ ] Chat interface (CLI)
- [ ] Background daemon
- [ ] Web UI [Optional]

### **Phase 6: Advanced Features** [Optional]

- [ ] Neo4j integration
- [ ] Temporal reasoning
- [ ] Entity networks
- [ ] Automatic summarization

---

## 💡 Recommendations

### **Start Now:**

1. ✅ Keep current Faiss + SQLite setup
2. ✅ Complete 4 other data sources (Calendar, Clipboard, File System, Screenshots)
3. ✅ Implement OCR for images
4. ✅ Build RAG engine with local LLM

### **Add Later (if needed):**

1. Neo4j - Only if you need complex relationship queries
2. Advanced NER - Start with spaCy, upgrade if needed
3. Web UI - CLI first, web later

### **Skip (for now):**

1. Audio processing - Unless voice recording is core use case
2. Real-time video - Out of scope for personal knowledge system
3. Cloud deployment - Challenge requires local operation

---

## 📊 Expected Performance

### **Storage**

- **Capacity**: 1M+ documents (Faiss handles it)
- **Search latency**: < 100ms for 100k vectors
- **Disk usage**: ~500MB per 100k documents

### **Ingestion Speed**

- Browser: 800+ records/sec
- Images (CLIP): ~10 images/sec (CPU)
- OCR: ~2 images/sec
- Audio (Whisper): ~5x realtime (Whisper-tiny)

### **LLM Inference**

- Phi-2 (2.7B): ~20 tokens/sec (CPU)
- TinyLlama (1.1B): ~50 tokens/sec (CPU)
- Context: 2048 tokens

---

## ✅ Conclusion

**Your architecture is SOLID and well-thought-out.**

Minor tweaks:

1. Remove CLIP from audio pipeline
2. Add Neo4j only if you need graph queries
3. Focus on completing data sources first, then RAG

**Next steps:** Create the folder structure and implement missing components.

---

**Author**: AI MINDS Team  
**Date**: February 14, 2026  
**Status**: Production-Ready Architecture
