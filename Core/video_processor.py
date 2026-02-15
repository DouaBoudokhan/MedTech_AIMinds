"""
Video Processor - Audio Transcription + Visual Frame Search
===========================================================

Features:
- Extract audio from video and transcribe with timestamps (Whisper)
- Extract frames at intervals and encode with CLIP
- Search for spoken words → jump to timestamp
- Search for visual content → jump to timestamp
- Combined audio + visual search

Example:
    processor = VideoProcessor()
    processor.index_video('meeting.mp4')

    # Search for what was said
    results = processor.search_audio('budget')

    # Search for what appeared
    results = processor.search_visual('chart')

    # Combined search
    results = processor.search_combined('project')
"""

import json
import cv2
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime

# Import existing processors
from audio_processor import AudioProcessor
from image_processor import ImageProcessor

try:
    from embeddings import EmbeddingManager
except ImportError:
    EmbeddingManager = None


class VideoProcessor:
    """Process videos for searchable audio and visual content"""

    def __init__(
        self,
        whisper_model: str = "base",
        frame_interval_sec: int = 3,
        ocr_engine: str = "easyocr"
    ):
        """
        Initialize video processor

        Args:
            whisper_model: Whisper model size ('tiny', 'base', 'small')
            frame_interval_sec: Extract frames every N seconds (default: 3)
            ocr_engine: OCR engine for frame text extraction
        """
        print(f"\n{'='*70}")
        print("🎬 VIDEO PROCESSOR INITIALIZED")
        print(f"{'='*70}")

        # Audio transcription
        self.audio = AudioProcessor(model_size=whisper_model)

        # Image processing (OCR + metadata)
        self.image = ImageProcessor(ocr_engine=ocr_engine)

        # Embeddings (for visual search)
        if EmbeddingManager:
            self.embeddings = EmbeddingManager()
            print("✅ CLIP embeddings loaded for visual search")
        else:
            self.embeddings = None
            print("⚠️  Embeddings not available - visual search disabled")

        # Configuration
        self.frame_interval_sec = frame_interval_sec
        print(f"✅ Frame extraction interval: {frame_interval_sec} seconds")
        print(f"{'='*70}\n")

    def extract_audio(self, video_path: str) -> str:
        """
        Extract audio from video using ffmpeg

        Args:
            video_path: Path to video file

        Returns:
            Path to extracted audio file
        """
        import subprocess
        import tempfile

        video_path = Path(video_path)
        audio_path = video_path.parent / f"{video_path.stem}_audio.wav"

        # Use ffmpeg to extract audio
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # Audio codec
            '-ar', '16000',  # Sample rate for Whisper
            '-ac', '1',  # Mono
            '-y',  # Overwrite
            str(audio_path)
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return str(audio_path)
        except subprocess.CalledProcessError as e:
            print(f"❌ ffmpeg error: {e.stderr.decode()}")
            return None
        except FileNotFoundError:
            print("❌ ffmpeg not found. Install: https://ffmpeg.org/download.html")
            return None

    def transcribe_video(self, video_path: str, language: str = None) -> Dict:
        """
        Transcribe video audio with timestamps

        Args:
            video_path: Path to video file
            language: Language code (None for auto-detect)

        Returns:
            Dictionary with transcription and segments
        """
        print(f"\n🎥 Transcribing video: {Path(video_path).name}")

        # Extract audio
        print("   Step 1: Extracting audio...")
        audio_path = self.extract_audio(video_path)

        if not audio_path:
            return {'error': 'Failed to extract audio'}

        # Transcribe
        print("   Step 2: Transcribing with Whisper...")
        result = self.audio.transcribe(audio_path, language=language)

        # Cleanup audio file
        Path(audio_path).unlink(missing_ok=True)

        # Add video metadata
        result['video_path'] = str(video_path)
        result['video_name'] = Path(video_path).name

        # Print summary
        if 'error' not in result:
            print(f"   ✅ Transcription complete!")
            print(f"   📝 Text length: {len(result['text'])} chars")
            print(f"   🔢 Segments: {len(result.get('segments', []))}")

        return result

    def extract_frames(self, video_path: str, interval_sec: int = None) -> List[Dict]:
        """
        Extract frames from video at regular intervals

        Args:
            video_path: Path to video file
            interval_sec: Extract every N seconds (defaults to self.frame_interval_sec)

        Returns:
            List of frame dictionaries with timestamps
        """
        if interval_sec is None:
            interval_sec = self.frame_interval_sec

        print(f"\n🎞️  Extracting frames every {interval_sec}s from: {Path(video_path).name}")

        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            print(f"❌ Cannot open video: {video_path}")
            return []

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_sec = total_frames / fps if fps > 0 else 0

        print(f"   📊 Video: {fps:.2f} fps, {total_frames} frames, {duration_sec:.1f} seconds")

        frame_interval = int(fps * interval_sec)
        frames = []

        timestamp_ms = 0
        frame_count = 0

        while True:
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
            ret, frame = cap.read()

            if not ret:
                break

            frames.append({
                'timestamp_sec': timestamp_ms / 1000,
                'frame_number': frame_count,
                'frame_array': frame
            })

            frame_count += 1
            timestamp_ms += interval_sec * 1000

        cap.release()

        print(f"   ✅ Extracted {len(frames)} frames")
        return frames

    def index_video(
        self,
        video_path: str,
        store_path: str = None,
        extract_frames: bool = True
    ) -> Dict:
        """
        Full video indexing: transcription + frame extraction

        Args:
            video_path: Path to video file
            store_path: Path to save index (JSON)
            extract_frames: Whether to extract frames for visual search

        Returns:
            Complete video index with audio + visual data
        """
        video_path = Path(video_path)
        print(f"\n{'='*70}")
        print(f"🎬 INDEXING VIDEO: {video_path.name}")
        print(f"{'='*70}")

        index = {
            'video_path': str(video_path),
            'video_name': video_path.name,
            'indexed_at': datetime.now().isoformat(),
            'audio': None,
            'visual': None
        }

        # Part 1: Audio transcription
        print("\n📝 PART 1: AUDIO TRANSCRIPTION")
        transcription = self.transcribe_video(str(video_path))
        index['audio'] = transcription

        # Part 2: Visual indexing
        if extract_frames and self.embeddings:
            print("\n🖼️  PART 2: VISUAL INDEXING")
            frames = self.extract_frames(str(video_path))

            if frames:
                # Encode frames
                print(f"   🔢 Encoding {len(frames)} frames with CLIP...")
                frame_arrays = [f['frame_array'] for f in frames]
                embeddings = self.embeddings.encode_image(frame_arrays)

                # Store in index
                index['visual'] = {
                    'frame_count': len(frames),
                    'interval_sec': self.frame_interval_sec,
                    'frames': []
                }

                for i, (frame_data, embedding) in enumerate(zip(frames, embeddings)):
                    index['visual']['frames'].append({
                        'timestamp_sec': frame_data['timestamp_sec'],
                        'frame_number': frame_data['frame_number'],
                        'embedding': embedding.tolist()  # Convert to list for JSON
                    })

                    if (i + 1) % 10 == 0:
                        print(f"   Processed {i+1}/{len(frames)} frames...")

                print(f"   ✅ Visual indexing complete!")

        # Part 3: Save index
        if store_path:
            store_path = Path(store_path)
            store_path.parent.mkdir(parents=True, exist_ok=True)

            with open(store_path, 'w', encoding='utf-8') as f:
                json.dump(index, f, indent=2)

            print(f"\n💾 Index saved to: {store_path}")

        print(f"\n{'='*70}")
        print("✅ VIDEO INDEXING COMPLETE")
        print(f"{'='*70}\n")

        return index

    def search_audio(
        self,
        index: Dict,
        query: str,
        case_sensitive: bool = False
    ) -> List[Dict]:
        """
        Search for spoken words in transcription

        Args:
            index: Video index from index_video()
            query: Search query
            case_sensitive: Whether to match case

        Returns:
            List of matching segments with timestamps
        """
        if not index.get('audio') or not index['audio'].get('segments'):
            return []

        segments = index['audio']['segments']
        query = query if case_sensitive else query.lower()

        matches = []
        for segment in segments:
            text = segment['text'] if case_sensitive else segment['text'].lower()

            if query in text:
                matches.append({
                    'timestamp_sec': segment['start'],
                    'end_sec': segment['end'],
                    'text': segment['text'],
                    'type': 'audio'
                })

        return matches

    def search_visual(
        self,
        index: Dict,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        """
        Search for visual content in frames

        Args:
            index: Video index from index_video()
            query: Search query (e.g., "flower", "person", "chart")
            top_k: Number of results to return

        Returns:
            List of matching frames with timestamps
        """
        if not index.get('visual') or not self.embeddings:
            return []

        # Encode query with CLIP text encoder
        query_embedding = self.embeddings.encode_text_for_image_search(query)

        # Get frame embeddings
        frames = index['visual']['frames']
        frame_embeddings = [f['embedding'] for f in frames]

        import numpy as np
        frame_embeddings = np.array(frame_embeddings, dtype=np.float32)

        # Calculate similarity
        similarities = np.dot(frame_embeddings, query_embedding[0])

        # Get top-k
        top_indices = np.argsort(similarities)[::-1][:top_k]

        matches = []
        for idx in top_indices:
            frame = frames[idx]
            matches.append({
                'timestamp_sec': frame['timestamp_sec'],
                'frame_number': frame['frame_number'],
                'score': float(similarities[idx]),
                'type': 'visual'
            })

        return matches

    def search_combined(
        self,
        index: Dict,
        query: str,
        top_k_visual: int = 3
    ) -> List[Dict]:
        """
        Combined audio + visual search

        Args:
            index: Video index from index_video()
            query: Search query
            top_k_visual: Number of visual results to include

        Returns:
            Sorted list of all matches (audio + visual)
        """
        # Search both modalities
        audio_matches = self.search_audio(index, query)
        visual_matches = self.search_visual(index, query, top_k=top_k_visual)

        # Combine
        all_matches = audio_matches + visual_matches

        # Sort by timestamp
        all_matches.sort(key=lambda x: x['timestamp_sec'])

        return all_matches


def test_video_processor():
    """Test video processor with a sample video"""
    print("\n" + "="*70)
    print("🧪 TESTING VIDEO PROCESSOR")
    print("="*70)

    processor = VideoProcessor(whisper_model='tiny', frame_interval_sec=5)

    # Example usage (uncomment to test with actual video)
    """
    # Index a video
    index = processor.index_video(
        'sample_video.mp4',
        store_path='video_index.json',
        extract_frames=True
    )

    # Search for audio
    print("\n🔍 Search Audio 'hello':")
    audio_results = processor.search_audio(index, 'hello')
    for r in audio_results:
        print(f"  {r['timestamp_sec']:.1f}s: {r['text']}")

    # Search for visual
    print("\n🔍 Search Visual 'person':")
    visual_results = processor.search_visual(index, 'person', top_k=3)
    for r in visual_results:
        print(f"  {r['timestamp_sec']:.1f}s: score={r['score']:.3f}")

    # Combined search
    print("\n🔍 Combined Search 'meeting':")
    combined_results = processor.search_combined(index, 'meeting')
    for r in combined_results:
        icon = "🎤" if r['type'] == 'audio' else "🖼️"
        print(f"  {icon} {r['timestamp_sec']:.1f}s")
    """

    print("\n✅ Video processor initialized successfully!")
    print("\n💡 To use:")
    print("   processor = VideoProcessor()")
    print("   index = processor.index_video('video.mp4', 'video_index.json')")
    print("   results = processor.search_combined(index, 'search query')")
    print("\n" + "="*70)


if __name__ == "__main__":
    test_video_processor()
