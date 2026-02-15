"""
Audio Processor - Transcription with Whisper
=============================================

Handles:
- Audio transcription
- Multiple audio formats
- Timestamp extraction
"""

from typing import Dict, Optional
from pathlib import Path


class AudioProcessor:
    """Process audio files with Whisper"""
    
    def __init__(self, model_size: str = "base"):
        """
        Initialize audio processor
        
        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
        """
        self.model_size = model_size
        self.model = None
        
        try:
            import whisper
            print(f"🔧 Loading Whisper model: {model_size}...")
            self.model = whisper.load_model(model_size)
            print(f"✅ Whisper model loaded: {model_size}")
        except ImportError:
            print("⚠️  Whisper not installed")
            print("   Install: uv add openai-whisper")
        except Exception as e:
            print(f"❌ Whisper error: {e}")
    
    def transcribe(self, audio_path: str, language: str = None, use_gpu: bool = True) -> Dict:
        """
        Transcribe audio file

        Args:
            audio_path: Path to audio file
            language: Language code ('en', 'fr', etc.) or None for auto-detect
            use_gpu: Use GPU if available (default: True)

        Returns:
            Dictionary with transcription results
        """
        if self.model is None:
            return {
                'text': '',
                'error': 'Whisper model not loaded'
            }

        try:
            # Check if CUDA is available
            import torch
            device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"

            # Move model to device
            self.model = self.model.to(device)

            # Transcribe
            result = self.model.transcribe(
                audio_path,
                language=language,
                fp16=(device == "cuda")  # Enable FP16 only on GPU
            )
            
            return {
                'text': result['text'].strip(),
                'language': result.get('language', language),
                'segments': [
                    {
                        'start': seg['start'],
                        'end': seg['end'],
                        'text': seg['text'].strip()
                    }
                    for seg in result.get('segments', [])
                ]
            }
        
        except Exception as e:
            print(f"❌ Transcription error for {audio_path}: {e}")
            return {
                'text': '',
                'error': str(e)
            }
    
    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        """
        Get audio duration in seconds
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds or None
        """
        try:
            import wave
            import contextlib
            
            with contextlib.closing(wave.open(audio_path, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                duration = frames / float(rate)
                return duration
        except Exception:
            return None


def test_audio_processor():
    """Test audio processing functionality"""
    print("\n🧪 Testing Audio Processor\n" + "="*50)
    
    processor = AudioProcessor(model_size="base")
    
    if processor.model:
        print("\n✅ Whisper model loaded successfully")
        print("\n💡 To transcribe audio:")
        print("   result = processor.transcribe('audio.mp3')")
        print("   print(result['text'])")
    else:
        print("\n⚠️  Whisper not available")
        print("   Install: uv add openai-whisper")


if __name__ == "__main__":
    test_audio_processor()
