"""
Quick Start Guide - AI MINDS
=============================

Get started with AI MINDS in 3 steps
"""

QUICK_START = """
╔════════════════════════════════════════════════════════════════╗
║  🧠 AI MINDS - Quick Start Guide                              ║
╚════════════════════════════════════════════════════════════════╝

STEP 1: Install Dependencies
────────────────────────────────────────────────────────────────
uv sync

Optional (for full AI features):
uv sync --extra ai-full


STEP 2: Collect Browser Data
────────────────────────────────────────────────────────────────
cd Data_Layer\\Data_Collection\\Browser
python browser_ingestion.py

This will create monthly JSON files in Data_Storage/


STEP 3: Run the Main System
────────────────────────────────────────────────────────────────
python main.py

Menu options:
  1. Collect browser data
  2. Ingest data to storage (creates vector embeddings)
  3. Interactive search
  4. Full pipeline (1 + 2)
  5. Show statistics
  6. Exit


QUICK SEARCH EXAMPLE
────────────────────────────────────────────────────────────────
from Data_Layer.storage_manager import UnifiedStorageManager

manager = UnifiedStorageManager()

# Ingest browser data
manager.ingest_browser_data("Data_Layer/Data_Storage/browser_data_2026_02.json")

# Search
results = manager.search("machine learning", top_k=5)
for r in results:
    print(f"Score: {r['score']:.3f}")

# Show stats
manager.print_stats()


MODULES AVAILABLE
────────────────────────────────────────────────────────────────
✅ Browser ingestion       - browser_ingestion.py
✅ Screenshot watcher      - screenshot_watcher.py
✅ Clipboard watcher       - clipboard_watcher.py
✅ File system monitor     - activity_monitor.py
📝 Calendar watcher        - calendar_watcher.py (needs Google API)
📝 Email watcher          - email_watcher.py (needs Gmail API)


CORE PROCESSORS
────────────────────────────────────────────────────────────────
✅ Embeddings             - embeddings.py (Sentence-Transformers + CLIP)
✅ Text processor         - text_processor.py (chunking)
✅ Image processor        - image_processor.py (OCR ready)
✅ Audio processor        - audio_processor.py (Whisper ready)
✅ Document processor     - document_processor.py (PDF/DOCX ready)
✅ RAG engine            - rag_engine.py


OPTIONAL FEATURES (Install Extra)
────────────────────────────────────────────────────────────────
uv add openai-whisper     # Audio transcription
uv add pytesseract        # OCR (also needs Tesseract binary)
uv add easyocr           # Alternative OCR
uv add pypdf2            # PDF extraction
uv add python-docx       # DOCX extraction
uv add spacy             # Named Entity Recognition


NEXT STEPS
────────────────────────────────────────────────────────────────
1. ✅ Ingest your browser data (already works!)
2. 📸 Add screenshot monitoring
3. 📋 Add clipboard monitoring
4. 📁 Add document monitoring
5. 🤖 Add local LLM (Phi-2 or TinyLlama)
6. 🌐 Add web UI (Gradio/Streamlit)


DOCUMENTATION
────────────────────────────────────────────────────────────────
📖 ARCHITECTURE.md       - Complete system design
📖 PROJECT_STRUCTURE.md  - Folder organization
📖 README.md            - Project overview


CURRENT STATUS
────────────────────────────────────────────────────────────────
✅ Browser: 824 records extracted
✅ Storage: Dual-vector (text 384d + visual 512d)
✅ Chunking: Intelligent overlap-based
✅ Search: Semantic similarity
✅ All data collection modules created
✅ All core processors created
✅ RAG engine ready
✅ Chat interface ready


TEAM COORDINATION
────────────────────────────────────────────────────────────────
5-person team:
  - Browser ingestion: ✅ DONE (you)
  - Calendar watcher: 📝 Ready for teammate
  - Clipboard watcher: 📝 Ready for teammate
  - Email watcher: 📝 Ready for teammate
  - File system monitor: 📝 Ready for teammate


╔════════════════════════════════════════════════════════════════╗
║  Questions? Check ARCHITECTURE.md for detailed documentation   ║
╚════════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    print(QUICK_START)
