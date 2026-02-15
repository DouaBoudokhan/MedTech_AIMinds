# Video Search with Timestamp Jumping - Feasibility Analysis

## 🎯 Feature Overview

**Goal**: Search videos and jump to exact timestamps where:
- A specific word was spoken (audio transcription)
- A specific object/scene appeared (visual analysis)

## ✅ Feasibility: **HIGHLY FEASIBLE**

### What We Already Have ✅

1. **Audio Transcription with Timestamps** ([audio_processor.py](Core/audio_processor.py))
   - Whisper already provides: `segments = [{'start': 0.5, 'end': 2.3, 'text': 'hello world'}]`
   - Just need to extract audio from video first

2. **Visual Embeddings** ([embeddings.py](Core/embeddings.py))
   - CLIP (512d) for frame embeddings
   - Text-to-image search already implemented

3. **Vector Storage** ([storage_manager.py](Data_Layer/storage_manager.py))
   - FAISS for similarity search
   - SQLite for metadata (timestamps, video paths)

### What We Need to Build 🔨

## Part 1: Audio-Based Search (EASY ✅)

**Search "flower" → Jump to timestamp where someone said "flower"**

### Pipeline:
```
Video → Extract Audio (ffmpeg) → Whisper Transcription →
Store Segments with Timestamps → Text Search → Jump to Timestamp
```

### Implementation:
```python
# Already have this in audio_processor.py!
result = processor.transcribe('video.mp4')
# Returns:
{
    'text': 'Look at this beautiful flower...',
    'segments': [
        {'start': 5.2, 'end': 8.1, 'text': 'Look at this'},
        {'start': 8.1, 'end': 10.5, 'text': 'beautiful flower'},
        {'start': 10.5, 'end': 12.0, 'text': 'in the garden'}
    ]
}

# Search for "flower"
matches = [seg for seg in segments if 'flower' in seg['text'].lower()]
# Returns: [{'start': 8.1, 'end': 10.5, 'text': 'beautiful flower'}]

# Jump to timestamp 8.1 seconds
```

**Difficulty**: ⭐ Easy (1-2 hours)
**Dependencies**: `ffmpeg-python` (already uses ffmpeg in Whisper)

---

## Part 2: Visual-Based Search (MEDIUM ⚠️)

**Search "flower" → Jump to timestamp where a flower appeared on screen**

### Pipeline:
```
Video → Extract Frames (every 3-5 sec) → CLIP Encode Each Frame →
Store (timestamp, embedding) → Text-to-Image Search → Jump to Timestamp
```

### Implementation:

**Step 1: Extract Frames**
```python
import cv2

def extract_frames(video_path, interval_sec=3):
    """Extract frames at regular intervals"""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps * interval_sec)

    frames = []
    timestamp_ms = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
        ret, frame = cap.read()
        if not ret:
            break

        frames.append({
            'timestamp_sec': timestamp_ms / 1000,
            'frame': frame
        })

        timestamp_ms += interval_sec * 1000

    cap.release()
    return frames
```

**Step 2: Encode & Store**
```python
def index_video_frames(video_path):
    """Extract and index frames for search"""
    frames = extract_frames(video_path, interval_sec=3)

    for frame_data in frames:
        # Encode frame with CLIP
        embedding = embeddings.encode_image(frame_data['frame'])

        # Store with timestamp
        storage.add_visual_item(
            image_array=frame_data['frame'],
            embedding=embedding,
            metadata={
                'source': 'video_frame',
                'video_path': video_path,
                'timestamp_sec': frame_data['timestamp_sec']
            }
        )
```

**Step 3: Search & Jump**
```python
def search_video(query_text, video_path, top_k=5):
    """Search for query in video (visual + audio)"""

    # Visual search: encode query with CLIP text encoder
    query_embedding = embeddings.encode_text_for_image_search(query_text)

    # Search visual store
    results = storage.search_visual(query_embedding, filters={'video_path': video_path})

    # Each result has timestamp_sec
    for result in results:
        print(f"Found at {result['timestamp_sec']}s: {result['metadata']}")

    # Jump to first match
    return results[0]['timestamp_sec']
```

**Difficulty**: ⭐⭐⭐ Medium (4-6 hours)
**Challenges**:
- Storage: 1-hour video @ 3fps = 3,600 frames
- Processing time: Encoding 3,600 frames takes ~10-15 minutes
- Solutions:
  - Sample every 5 seconds instead of 3 (720 frames for 1-hour video)
  - Use scene detection to only store key frames
  - Background processing with progress tracking

---

## Part 3: Combined Search (ADVANCED 🚀)

**Search "flower" → Returns BOTH:
- Timestamps where "flower" was said
- Timestamps where flowers appeared visually**

### Implementation:
```python
def search_video_combined(query, video_path):
    """Search both audio and visual"""

    # Audio search
    audio_matches = search_transcription(query, video_path)

    # Visual search
    visual_matches = search_frames(query, video_path)

    # Merge and sort by timestamp
    all_matches = []

    for match in audio_matches:
        all_matches.append({
            'timestamp': match['start'],
            'type': 'audio',
            'context': match['text'],
            'confidence': match['confidence']
        })

    for match in visual_matches:
        all_matches.append({
            'timestamp': match['timestamp_sec'],
            'type': 'visual',
            'context': 'Frame match',
            'confidence': match['score']
        })

    # Sort by timestamp
    all_matches.sort(key=lambda x: x['timestamp'])

    return all_matches
```

**Result**: Interactive timeline of all matches!

---

## 📊 Storage Estimates

### 1-Hour Video Analysis:

| Component | Storage |
|-----------|---------|
| **Audio**: Transcript text | ~10 KB |
| **Audio**: Timestamps | ~5 KB |
| **Visual**: Frames @ 3fps | ~3,600 frames |
| **Visual**: CLIP embeddings | 3,600 × 512 × 4 bytes = ~7 MB |
| **Visual**: Frame thumbnails (optional) | 3,600 × 50 KB = ~180 MB |

**Total**: ~200 MB per video (with thumbnails) or ~7 MB (embeddings only)

### Optimization:
- Sample every 5 seconds → ~720 frames → ~3.5 MB (embeddings only)
- Don't store full frames, just thumbnails for preview
- Lazy loading: extract frames on demand

---

## 🛠️ Required Dependencies

```toml
# Already have
torch>=2.0.0
transformers>=4.30.0
faiss-cpu>=1.7.4

# Need to add
opencv-python>=4.8.0      # Video frame extraction
ffmpeg-python>=0.2.0      # Audio extraction (optional, Whisper handles it)
```

---

## 💡 Implementation Plan

### Phase 1: Audio Search (Easy) ✅
- [ ] Extract audio from video
- [ ] Transcribe with Whisper (timestamps)
- [ ] Store segments in SQLite
- [ ] Text search with timestamp results
- [ ] Video player integration (HTML5)

**Time**: 2-3 hours

### Phase 2: Visual Search (Medium)
- [ ] Extract frames at intervals (3-5 sec)
- [ ] Encode frames with CLIP
- [ ] Store embeddings + timestamps
- [ ] Text-to-image search
- [ ] Return matching timestamps

**Time**: 4-6 hours

### Phase 3: UI & Integration
- [ ] Video player with timestamp jumping
- [ ] Search interface
- [ ] Timeline visualization of matches
- [ ] Preview thumbnails

**Time**: 3-4 hours

### Total Time: **9-13 hours** for full implementation

---

## 🎬 Demo Scenario

```python
# User searches: "flower"

# System returns:
[
  {'timestamp': 8.1, 'type': 'audio', 'context': 'beautiful flower'},
  {'timestamp': 45.2, 'type': 'visual', 'context': 'Frame: flower in garden'},
  {'timestamp': 127.8, 'type': 'audio', 'context': 'the flower bloomed'},
  {'timestamp': 210.5, 'type': 'visual', 'context': 'Frame: close-up of rose'}
]

# User clicks 45.2 → Video jumps to 45.2 seconds
# User sees a flower on screen!
```

---

## ✅ Verdict: **DEFINITELY BUILD THIS**

**Why it's feasible:**
1. All core components already exist (Whisper timestamps, CLIP embeddings, vector search)
2. Just need integration layer
3. Storage is manageable (~10 MB per video for embeddings)
4. Processing is reasonable (~15 min for 1-hour video)

**Why it's valuable:**
1. Unique feature - very few tools do this
2. Perfect for MemoryOS hackathon
3. Demonstrates full multimodal AI capabilities
4. Practical use case (lectures, tutorials, meetings)

**Recommended approach:**
1. Start with audio-only (quick win)
2. Add visual search incrementally
3. Optimize frame sampling based on performance

---

## 🚀 Next Steps

1. **Create prototype**: `Core/video_processor.py`
2. **Test with sample video**: 5-10 min clip
3. **Measure performance**: Frame extraction + encoding speed
4. **Build simple UI**: HTML5 video player + search box
5. **Demo to judges**: Show audio + visual search working!

---

**Author**: AI MINDS Team
**Date**: February 15, 2026
**Status**: Ready for Implementation
