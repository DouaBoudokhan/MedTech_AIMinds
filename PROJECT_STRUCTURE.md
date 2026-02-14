"""
README - AI MINDS Project Structure
====================================

## 📁 Project Organization

This project follows a clean architecture with clear separation of concerns:

```
AI minds/
├── Data_Layer/          # Data ingestion & storage
├── Core/                # Processing engines  
├── API/                 # User interfaces
└── Tests/               # Testing
```

## 🗂️ Detailed Structure

### Data_Layer/
**Purpose**: Collect and store multimodal data

- **Data_Collection/**: Input processors
  - Browser/ ✅ - Browser history & bookmarks
  - Calendar/ 📝 - Google Calendar events
  - Clipboard/ 📝 - Clipboard monitoring
  - Email/ 📝 - Email ingestion
  - File_System/ 📝 - Document monitoring
  - Screenshots/ ✅ - Screenshot capture
  - Audio/ 📝 - Voice recordings

- **Data_Storage/**: Persistent storage
  - vector_store/ - Faiss indices
    - text_index/ - Text embeddings (384d)
    - visual_index/ - Visual embeddings (512d)
  - browser_data_*.json - Browser exports
  - *.db - SQLite databases

- **storage_manager.py**: Main storage interface

### Core/
**Purpose**: Processing engines and AI models

- embeddings.py - Sentence-Transformers & CLIP
- text_processor.py - Chunking, preprocessing
- image_processor.py - OCR, visual processing
- audio_processor.py - Whisper transcription
- document_processor.py - PDF/DOCX extraction
- entity_extractor.py - Named Entity Recognition
- llm_manager.py - Local LLM (<4B params)
- rag_engine.py - RAG pipeline
- neo4j_manager.py [Optional] - Graph DB

### API/
**Purpose**: User interfaces

- chat_interface.py - Interactive CLI chat
- web_ui.py [Optional] - Web interface

### Tests/
**Purpose**: Quality assurance

- test_storage.py
- test_embeddings.py
- test_rag.py

## 🚀 Quick Start

### 1. Setup Environment
```bash
uv sync
```

### 2. Collect Browser Data
```bash
cd "Data_Layer\Data_Collection\Browser"
python browser_ingestion.py
```

### 3. Index Data
```bash
cd "Data_Layer"
python storage_manager.py
```

### 4. Search
```python
from Data_Layer.storage_manager import UnifiedStorageManager

manager = UnifiedStorageManager()
results = manager.search("robe Zara", top_k=5)
```

## 📊 Current Status

✅ **Completed**:
- Browser ingestion (824 records)
- Storage manager (Faiss + SQLite)
- Text embeddings (384d multilingual)
- Visual embeddings (512d CLIP)
- Semantic chunking
- Screenshot watcher

📝 **In Progress**:
- Calendar watcher
- Clipboard watcher
- File system monitor
- Email ingestion

🔜 **Next**:
- OCR integration
- Audio transcription
- RAG engine
- Local LLM integration

## 📖 Documentation

See `ARCHITECTURE.md` for complete system design.

## 🤝 Team

5-person team working on AI MINDS challenge:
- Browser ingestion: ✅ Complete
- Other 4 modules: In progress

---

**Last Updated**: February 14, 2026
