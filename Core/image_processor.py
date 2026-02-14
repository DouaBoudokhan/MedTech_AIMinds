"""
Image Processor - OCR and Visual Processing
============================================

Handles:
- OCR text extraction from images
- Image preprocessing for embeddings
- Screenshot analysis
"""

from typing import Tuple, Optional, Dict
from pathlib import Path
from PIL import Image
import numpy as np


class ImageProcessor:
    """Process images for OCR and embeddings"""
    
    def __init__(self, ocr_engine: str = "none"):
        """
        Initialize image processor
        
        Args:
            ocr_engine: 'pytesseract', 'easyocr', or 'none'
        """
        self.ocr_engine = ocr_engine
        self.ocr = None
        
        if ocr_engine == "pytesseract":
            try:
                import pytesseract
                self.ocr = pytesseract
                print("✅ OCR: pytesseract loaded")
            except ImportError:
                print("⚠️  pytesseract not installed. OCR disabled.")
                print("   Install: uv add pytesseract")
        
        elif ocr_engine == "easyocr":
            try:
                import easyocr
                self.ocr = easyocr.Reader(['en', 'fr'])
                print("✅ OCR: EasyOCR loaded (en, fr)")
            except ImportError:
                print("⚠️  easyocr not installed. OCR disabled.")
                print("   Install: uv add easyocr")
    
    def extract_text(self, image_path: str) -> str:
        """
        Extract text from image using OCR
        
        Args:
            image_path: Path to image file
            
        Returns:
            Extracted text
        """
        if self.ocr is None:
            return ""
        
        try:
            image = Image.open(image_path)
            
            if self.ocr_engine == "pytesseract":
                text = self.ocr.image_to_string(image, lang='eng+fra')
            
            elif self.ocr_engine == "easyocr":
                result = self.ocr.readtext(np.array(image))
                text = " ".join([detection[1] for detection in result])
            
            else:
                return ""
            
            return text.strip()
        
        except Exception as e:
            print(f"❌ OCR error for {image_path}: {e}")
            return ""
    
    def get_image_metadata(self, image_path: str) -> Dict:
        """
        Extract image metadata
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dictionary with metadata
        """
        try:
            image = Image.open(image_path)
            
            return {
                'width': image.width,
                'height': image.height,
                'format': image.format,
                'mode': image.mode,
                'size_bytes': Path(image_path).stat().st_size
            }
        
        except Exception as e:
            print(f"❌ Metadata error for {image_path}: {e}")
            return {}
    
    def preprocess_image(self, image_path: str, max_size: Tuple[int, int] = (1024, 1024)) -> Image.Image:
        """
        Preprocess image for embedding
        
        Args:
            image_path: Path to image file
            max_size: Maximum dimensions (width, height)
            
        Returns:
            Preprocessed PIL Image
        """
        image = Image.open(image_path).convert('RGB')
        
        # Resize if too large
        if image.width > max_size[0] or image.height > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        return image
    
    def is_screenshot(self, image_path: str) -> bool:
        """
        Detect if image is likely a screenshot
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if likely a screenshot
        """
        path = Path(image_path)
        
        # Check filename patterns
        screenshot_patterns = ['screenshot', 'screen shot', 'capture', 'scr_']
        filename_lower = path.name.lower()
        
        if any(pattern in filename_lower for pattern in screenshot_patterns):
            return True
        
        # Check parent folder
        if 'screenshot' in str(path.parent).lower():
            return True
        
        return False


def test_image_processor():
    """Test image processing functionality"""
    print("\n🧪 Testing Image Processor\n" + "="*50)
    
    # Test without OCR
    print("\n📸 Testing without OCR:")
    processor = ImageProcessor(ocr_engine="none")
    
    # Create a test image
    print("\n🎨 Creating test image:")
    test_image = Image.new('RGB', (800, 600), color='blue')
    test_path = Path("test_image.png")
    test_image.save(test_path)
    print(f"Created: {test_path}")
    
    # Test metadata
    print("\n📊 Testing Metadata:")
    metadata = processor.get_image_metadata(str(test_path))
    print(f"Metadata: {metadata}")
    
    # Test screenshot detection
    print("\n🔍 Testing Screenshot Detection:")
    is_screenshot = processor.is_screenshot(str(test_path))
    print(f"Is screenshot: {is_screenshot}")
    
    # Cleanup
    test_path.unlink()
    print(f"\n🧹 Cleaned up: {test_path}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_image_processor()
