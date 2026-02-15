# AI MINDS - Data Ingestion Layer

Multimodal personal knowledge assistant - Data collection and ingestion modules for MemoryOS.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA COLLECTION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Emails           • Browser History    • Calendar                        │
│  • Clipboard        • User Clicks        • Open Windows                    │
│  • File Systems                                                        │
│    - Images          - Audio              - Documents                      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            RAW DATA STORAGE                                 │
│  Save original files:                                                       │
│  • email_2024_11_15.json                                                    │
│  • screenshot_001.png                                                       │
│  • document.pdf                                                             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MULTIMODAL EMBEDDING ENGINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Text Content (email, calendar, clipboard)                                  │
│    ├─ Long → Chunk → BGE-M3 Embedding                                       │
│    └─ Short → BGE-M3 Embedding                                              │
│                                                                              │
│  Audio (Voice Recording) → Whisper → Transcription → Text Embedding         │
│                                                                              │
│  Documents (PDFs, Excel, DOCX) → Text Extraction → BGE-M3 Embedding         │
│                                                                              │
│  Images (Screenshots, Photos) → CLIP Embedding (512d)                       │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         VECTOR STORAGE & RETRIEVAL                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  SQLite (Metadata) ──────────────────────────────────────────┐             │
│  FAISS Index (Text Embeddings 1024d) ────────────────────────┤             │
│  FAISS Index (Visual Embeddings 512d) ───────────────────────┤             │
│  └─► Vector DB (Semantic Search & Retrieval) ◄────────────────┘             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CONTEXT MANAGEMENT                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  Phase 1: Long Memory                    │
│    • Semantic retrieval over lengthy conversation                             │
│                                                                              │
│  Phase 2: Current User Traces                │
│    • Real-time context: "sees what the user sees"                            │
│                                                                              │
│  Phase 3: Long Memory + Session State          │
│    • Overall conversation goal/intent                                     │
│    • Tasks completed in this conversation                                   │
│    • Pending tasks                                                          │
│    • Future perspective                                                     │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LOCAL SLM (Qwen 4B / Phi-2) + ReAct                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  User Query → Event-Driven Processing                                       │
│                                                                              │
│  CHAIN OF THOUGHT:                                                           │
│  ┌──────────────────────────────────────────────────────────────┐           │
│  │ CONTEXT GATHERING - Step-Back Prompting                       │           │
│  │   "What do I already know about this?" → Check memory        │           │
│  ├──────────────────────────────────────────────────────────────┤           │
│  │ INTENT UNDERSTANDING - Metacognitive Check                   │           │
│  │   ✓ Do I have enough context to answer?                      │           │
│  │   ✓ Is this request clear or ambiguous?                      │           │
│  │   ✓ What's the actual goal behind this request?              │           │
│  │   ✓ Are there missing critical details?                      │           │
│  │   → IF AMBIGUOUS: Ask clarifying questions                   │           │
│  │   → IF CLEAR: Continue to execution                          │           │
│  ├──────────────────────────────────────────────────────────────┤           │
│  │ ReAct EXECUTION LOOP - Reason → Act → Observe                │           │
│  │   ✓ Iterate until goal achieved                              │           │
│  └──────────────────────────────────────────────────────────────┘           │
│                                                                              │
│  AVAILABLE TOOLS:                                                            │
│  • Send email            • Search Google                                     │
│  • Create calendar Event  • Set reminder                                     │
│  • Manipulate ToDo list   • Open browser/file/show_in_folder                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Text Embeddings** | BGE-M3 (via Ollama) | 1024d semantic vectors |
| **Visual Embeddings** | CLIP ViT-B/32 | 512d image vectors |
| **Vector Storage** | FAISS-CPU | Fast similarity search |
| **Metadata Storage** | SQLite | Structured data & relationships |
| **Audio Transcription** | Whisper | Speech-to-text |
| **Document Processing** | PyPDF2, python-docx | Text extraction |
| **OCR** | EasyOCR, Pytesseract | Image text extraction |
| **Local LLM** | Qwen 4B, Phi-2 (via Ollama) | On-device reasoning |
| **Google APIs** | Calendar, Gmail | Event & email integration |


## Quick Start

### 1. Install Dependencies

Using UV (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

### 2. Run Individual Modules

Each module runs independently:

**Browser History Extraction:**
```bash
cd Data_Layer/Data_Collection/Browser
python browser_ingestion.py
```

**Clipboard Monitoring:**
```bash
cd Data_Layer/Data_Collection/Clipboard
python clipboard_watcher.py
```

**Calendar Monitoring:**
```bash
cd Data_Layer/Data_Collection/Calendar
python calendar_watcher.py
```

**Email Monitoring:**
```bash
cd Data_Layer/Data_Collection/Email
python email_watcher.py
```

### 3. Run Complete Pipeline

**Interactive Menu (Recommended):**
```bash
python main.py
```

Options:
- Collect browser data
- Ingest all data to vector storage
- Interactive search query
- Run full pipeline

**Batch Ingestion:**
```bash
python ingest_all_data.py
```

**Query Testing:**
```bash
python test_query_against_store.py
```

### 4. Clipboard Concierge (Smart Actions)

Start the clipboard concierge service for intelligent clipboard actions:

**Windows:**
```bash
start_concierge.bat
```

**Manual:**
```bash
cd Data_Layer/Data_Collection/Clipboard_Concierge
python concierge.py
```

## Key Features

### 1. **Multimodal Data Collection**
- **Browser History**: Automatic extraction from 4+ browsers
- **Clipboard Monitoring**: Real-time capture with deduplication
- **Google Calendar**: Event tracking with OAuth 2.0
- **File System**: Document activity monitoring
- **Screenshots**: Automatic capture (in development)
- **Audio**: Voice recording with transcription (in development)

### 2. **Semantic Search & Retrieval**
- Dual-vector system (text + visual)
- Hierarchical chunking for long documents
- Fast similarity search with FAISS
- Cross-modal retrieval (search images with text, etc.)

### 3. **Privacy-First Design**
- 100% local storage (no cloud dependencies)
- No external API calls (except Google OAuth)
- Read-only access to user data
- Credentials excluded from version control

### 4. **Local LLM Integration**
- Qwen 4B / Phi-2 via Ollama
- ReAct agent framework for task execution
- Chain-of-thought reasoning
- Tool use (email, calendar, file navigation)


### Core Components Status

## Module Details

### Browser
Extracts browsing history from major browsers for search and discovery.

**Features:**
- Multi-browser support (Chrome, Firefox, Edge)
- History extraction with timestamps
- URL and title metadata

### File_System
Monitors file system activity and document access patterns.

**Features:**
- File change detection
- Document access tracking
- Activity logging

### Clipboard
Monitors clipboard for copied content and automatically captures it.

**Features:**
- Text capture
- URL detection
- Image capture (screenshots)
- File copy detection and duplication
- 5-second deduplication window
- Silent background operation

### Calendar
Monitors Google Calendar for upcoming events and meetings.

**Features:**
- Event capture (title, description, time, location)
- Attendee information
- Meeting links (Google Meet, etc.)
- 5-minute polling interval
- Looks ahead 30 days
- OAuth 2.0 authentication

**Setup:** See [Data_Layer/Data_Collection/Calendar/README.md](Data_Layer/Data_Collection/Calendar/README.md) for Google Cloud setup instructions.

### Email
Monitors Gmail for new emails and captures them automatically.

**Features:**
- Email capture (subject, sender, recipients, body)
- Headers and metadata (labels, attachments, read/unread status)
- 5-minute polling interval
- Looks back 10 minutes for new emails
- Shared OAuth authentication with Calendar watcher
- Thread and message ID tracking

## Core Components

### UnifiedStorageManager
Central storage interface managing dual-vector system:
- **Text Embeddings**: BGE-M3 (1024d) via Ollama
- **Visual Embeddings**: CLIP ViT-B/32 (512d)
- **Hierarchical Model**: memory_items → chunks
- **Metadata Database**: SQLite with full-text search
- **Vector Index**: FAISS for fast similarity search
- **RAG Pipeline**: Retrieval-augmented generation with local LLMs

### Processing Engines
Located in [Core/](Core/) directory:

| Module | Purpose | Technology |
|--------|---------|------------|
| [embeddings.py](Core/embeddings.py) | Vector generation | BGE-M3, CLIP |
| [text_processor.py](Core/text_processor.py) | Semantic chunking | spaCy, Transformers |
| [image_processor.py](Core/image_processor.py) | OCR & visual encoding | EasyOCR, CLIP |
| [audio_processor.py](Core/audio_processor.py) | Speech-to-text | Whisper |
| [document_processor.py](Core/document_processor.py) | Document extraction | PyPDF2, python-docx |
| [rag_engine.py](Core/rag_engine.py) | RAG pipeline | Custom |
| [llm_manager.py](Core/llm_manager.py) | Local LLM integration | Ollama |

### Data Flow Pipeline

```
1. Data Collection (Browser, Clipboard, Calendar, etc.)
        ↓
2. Raw Data Storage (JSON, PNG, PDF files)
        ↓
3. Processing (Chunking, OCR, Transcription)
        ↓
4. Embedding Generation (BGE-M3 for text, CLIP for images)
        ↓
5. Vector Storage (FAISS indices + SQLite metadata)
        ↓
6. Semantic Search & Retrieval
        ↓
7. Context-Aware Response (Local SLM with ReAct)
```

## Standardized Metadata Schema

All modules use the same metadata schema for compatibility:

```json
{
  "id": "unique_hash",
  "timestamp": "2026-02-14T18:54:07.332950",
  "content_type": "text|url|image|files|calendar_event|browser_history",
  "content_preview": "Brief description",
  "file_path": "path/to/detail/file.json",
  "source": "clipboard|google_calendar|browser",
  "...": "module-specific fields"
}
```

## Key Features

### 1. **Multimodal Data Collection**
- **Browser History**: Automatic extraction from 4+ browsers
- **Clipboard Monitoring**: Real-time capture with deduplication
- **Google Calendar**: Event tracking with OAuth 2.0
- **File System**: Document activity monitoring
- **Screenshots**: Automatic capture (in development)
- **Audio**: Voice recording with transcription (in development)

### 2. **Semantic Search & Retrieval**
- Dual-vector system (text + visual)
- Hierarchical chunking for long documents
- Fast similarity search with FAISS
- Cross-modal retrieval (search images with text, etc.)

### 3. **Privacy-First Design**
- 100% local storage (no cloud dependencies)
- No external API calls (except Google OAuth)
- Read-only access to user data
- Credentials excluded from version control

### 4. **Local LLM Integration**
- Qwen 4B / Phi-2 via Ollama
- ReAct agent framework for task execution
- Chain-of-thought reasoning
- Tool use (email, calendar, file navigation)

## Data Storage

```
Data_Layer/Data_Collection/
├── Browser/data/              # Browser history data
├── File_System/data/          # File system activity
├── Clipboard/data/
│   ├── text/metadata.json     # All clipboard events
│   ├── images/                # Captured screenshots
│   ├── files/                 # File lists
│   └── copied_files/          # Duplicated files
└── Calendar/data/
    ├── events/                # Individual calendar events
    └── metadata.json          # All calendar events metadata
```

## Security & Privacy

- ✅ **Local storage** - all data stays on your machine
- ✅ **No external APIs** (except Google Calendar OAuth)
- ✅ **Read-only access** - modules don't modify your data
- ✅ **Credentials protected** - excluded from Git

## For Hackathon Judges

### Technical Achievements
- ✅ **Dual-vector multimodal search** (text + visual embeddings)
- ✅ **Local-first architecture** with FAISS + SQLite
- ✅ **Hierarchical chunking** for long document understanding
- ✅ **ReAct agent framework** with chain-of-thought reasoning
- ✅ **Modular data collection** with standardized metadata schema
- ✅ **Privacy-focused** - 100% local storage (no cloud dependencies)

### Scalability
- Designed to handle **millions of documents** with FAISS indexing
- Efficient semantic search with sub-second query times
- Background services with minimal resource footprint
- Cross-platform support (Windows primary, macOS/Linux partial)

### Innovation Points
1. **Hybrid Search**: Combines semantic vector search with metadata filtering
2. **Context-Aware AI**: 3-phase memory system (long-term → current traces → session state)
3. **Local SLM Optimization**: Maximizes 4B model performance with ReAct + tool use
4. **Real-time Context**: "Sees what the user sees" through continuous monitoring

## Development

To add a new data collection module:

1. Create new folder: `Data_Layer/Data_Collection/YourModule/`
2. Create `your_module.py` with standard MemoryOS schema
3. Add dependencies to `pyproject.toml`
4. Create individual `README.md` for your module
5. Update this README with module status

## Team

- **Roua Khalfet** 
- **Doua Boudokhan** 
- **Sarra Bousnina** 
- **Yassine Kharrat** 
- **Youssef Ben Lallahom** 


## License

MIT License - AI MINDS Hackathon Team 2026
