"""
Embedding Manager - Text and Visual Embeddings
===============================================

Handles initialization and encoding for:
- Text: Sentence-Transformers (paraphrase-multilingual-MiniLM-L12-v2)
- Images: CLIP (openai/clip-vit-base-patch32)
"""

from typing import List, Union, Optional
import numpy as np
import torch
from pathlib import Path
from PIL import Image
from sentence_transformers import SentenceTransformer
from transformers import CLIPProcessor, CLIPModel


class EmbeddingManager:
    """Unified manager for text and visual embeddings"""
    
    # Model configurations
    TEXT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
    VISUAL_MODEL = "openai/clip-vit-base-patch32"
    TEXT_DIM = 384
    VISUAL_DIM = 512
    
    def __init__(self, device: Optional[str] = None):
        """
        Initialize embedding models
        
        Args:
            device: 'cuda', 'cpu', or None (auto-detect)
        """
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"🔧 Initializing embeddings on {self.device}...")
        
        # Text embeddings
        self.text_model = SentenceTransformer(self.TEXT_MODEL, device=self.device)
        print(f"✅ Text model loaded: {self.TEXT_MODEL} ({self.TEXT_DIM}d)")
        
        # Visual embeddings
        self.clip_model = CLIPModel.from_pretrained(self.VISUAL_MODEL).to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained(self.VISUAL_MODEL)
        print(f"✅ Visual model loaded: {self.VISUAL_MODEL} ({self.VISUAL_DIM}d)")
    
    def encode_text(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Encode text(s) into embeddings
        
        Args:
            texts: Single text or list of texts
            normalize: Normalize embeddings to unit length
            
        Returns:
            numpy array of shape (n, 384) for text embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.text_model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode_image(self, images: Union[str, Path, Image.Image, List], normalize: bool = True) -> np.ndarray:
        """
        Encode image(s) into embeddings using CLIP
        
        Args:
            images: Single image path/PIL Image or list of them
            normalize: Normalize embeddings to unit length
            
        Returns:
            numpy array of shape (n, 512) for visual embeddings
        """
        # Convert to list
        if not isinstance(images, list):
            images = [images]
        
        # Load images
        pil_images = []
        for img in images:
            if isinstance(img, (str, Path)):
                pil_images.append(Image.open(img).convert('RGB'))
            elif isinstance(img, Image.Image):
                pil_images.append(img.convert('RGB'))
            else:
                raise ValueError(f"Unsupported image type: {type(img)}")
        
        # Process and encode
        inputs = self.clip_processor(images=pil_images, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            image_features = self.clip_model.get_image_features(**inputs)
        
        # Convert to numpy
        embeddings = image_features.cpu().numpy()
        
        # Normalize if requested
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)
        
        return embeddings
    
    def encode_text_for_image_search(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Encode text queries for image search using CLIP text encoder
        
        Args:
            texts: Single text or list of texts
            normalize: Normalize embeddings to unit length
            
        Returns:
            numpy array of shape (n, 512) for text embeddings in visual space
        """
        if isinstance(texts, str):
            texts = [texts]
        
        # Process and encode
        inputs = self.clip_processor(text=texts, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            text_features = self.clip_model.get_text_features(**inputs)
        
        # Convert to numpy
        embeddings = text_features.cpu().numpy()
        
        # Normalize if requested
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)
        
        return embeddings


def test_embeddings():
    """Test embedding functionality"""
    print("\n🧪 Testing Embedding Manager\n" + "="*50)
    
    manager = EmbeddingManager()
    
    # Test text embeddings
    print("\n📝 Text Embeddings:")
    texts = ["Hello world", "Bonjour le monde"]
    text_embeds = manager.encode_text(texts)
    print(f"Shape: {text_embeds.shape}")
    print(f"Sample: {text_embeds[0][:5]}")
    
    # Test CLIP text embeddings
    print("\n🔍 CLIP Text Embeddings (for image search):")
    clip_text_embeds = manager.encode_text_for_image_search("a photo of a cat")
    print(f"Shape: {clip_text_embeds.shape}")
    print(f"Sample: {clip_text_embeds[0][:5]}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_embeddings()
