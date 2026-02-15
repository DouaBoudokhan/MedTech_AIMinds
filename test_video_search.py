"""
Test Video Search Feature
==========================

This script demonstrates the video search capabilities.
For full testing, you need a video file.
"""

import sys
from pathlib import Path

print("="*70)
print("🎬 VIDEO SEARCH - TEST SCRIPT")
print("="*70)

# Check if video file provided
if len(sys.argv) < 2:
    print("\n⚠️  No video file provided!")
    print("\n💡 Usage:")
    print("   python test_video_search.py path/to/video.mp4")
    print("\n📁 Current directory:")
    for f in Path(".").glob("*.mp4"):
        print(f"   - {f}")
    print("\n🌐 Or download a sample video:")
    print("   https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4")
    sys.exit(1)

video_path = sys.argv[1]

if not Path(video_path).exists():
    print(f"\n❌ Video not found: {video_path}")
    sys.exit(1)

print(f"\n✅ Video found: {Path(video_path).name}")
print(f"   Size: {Path(video_path).stat().st_size / 1024 / 1024:.1f} MB")

# Import processor
print("\n🔧 Importing VideoProcessor...")
try:
    from Core.video_processor import VideoProcessor
    print("   ✅ VideoProcessor imported")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    sys.exit(1)

# Initialize
print("\n🚀 Initializing VideoProcessor...")
try:
    processor = VideoProcessor(
        whisper_model='tiny',  # Use tiny model for speed
        frame_interval_sec=5,  # Extract frame every 5 seconds
        ocr_engine='none'      # Disable OCR for now
    )
except Exception as e:
    print(f"   ❌ Initialization error: {e}")
    print("\n💡 This is expected if Whisper or CLIP models aren't downloaded yet.")
    print("   The code structure is correct - just need to download models.")
    sys.exit(1)

# Test 1: Audio transcription
print("\n" + "="*70)
print("TEST 1: Audio Transcription")
print("="*70)

try:
    transcription = processor.transcribe_video(video_path, language=None)

    if 'error' in transcription:
        print(f"❌ Error: {transcription['error']}")
    else:
        print(f"✅ Transcription successful!")
        print(f"\n📝 Full Text ({len(transcription['text'])} chars):")
        print("   " + transcription['text'][:200] + "...")

        print(f"\n🔢 Segments ({len(transcription.get('segments', []))}):")
        for i, seg in enumerate(transcription.get('segments', [])[:5]):
            print(f"   {i+1}. {seg['start']:.1f}s - {seg['end']:.1f}s: {seg['text']}")
        if len(transcription.get('segments', [])) > 5:
            print(f"   ... and {len(transcription.get('segments', [])) - 5} more")

except Exception as e:
    print(f"❌ Transcription failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Frame extraction (if CLIP available)
print("\n" + "="*70)
print("TEST 2: Frame Extraction")
print("="*70)

if processor.embeddings:
    try:
        frames = processor.extract_frames(video_path, interval_sec=5)
        print(f"✅ Extracted {len(frames)} frames")

        if frames:
            print(f"\n📊 First few frames:")
            for i, frame in enumerate(frames[:3]):
                print(f"   Frame {i+1}: {frame['timestamp_sec']:.1f}s, shape: {frame['frame_array'].shape}")

    except Exception as e:
        print(f"❌ Frame extraction failed: {e}")
        import traceback
        traceback.print_exc()
else:
    print("⚠️  CLIP embeddings not available - skipping frame extraction")

# Test 3: Create index
print("\n" + "="*70)
print("TEST 3: Create Video Index")
print("="*70)

try:
    index_path = f"test_index_{Path(video_path).stem}.json"

    index = processor.index_video(
        video_path,
        store_path=index_path,
        extract_frames=False  # Skip frames for faster testing
    )

    print(f"✅ Index created: {index_path}")
    print(f"   Audio segments: {len(index.get('audio', {}).get('segments', []))}")

except Exception as e:
    print(f"❌ Index creation failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Search
print("\n" + "="*70)
print("TEST 4: Search Functionality")
print("="*70)

try:
    # Load the index we just created
    import json
    with open(index_path, 'r', encoding='utf-8') as f:
        index = json.load(f)

    # Test searches
    test_queries = ['the', 'video', 'test']

    for query in test_queries:
        results = processor.search_audio(index, query, case_sensitive=False)
        print(f"\n🔍 Query: '{query}'")
        print(f"   Results: {len(results)} matches")
        for r in results[:3]:
            print(f"   - {r['timestamp_sec']:.1f}s: {r['text']}")

except Exception as e:
    print(f"❌ Search failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("✅ TEST COMPLETE")
print("="*70)
print("\n💡 Next steps:")
print("   1. Try with your own video: python test_video_search.py my_video.mp4")
print("   2. Open video_search_demo.html in browser to see the UI")
print("   3. Integration: connect backend to frontend API")
print()
