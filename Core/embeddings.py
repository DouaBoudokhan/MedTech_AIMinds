"""
Embedding Manager - Text and Visual Embeddings
===============================================

Handles initialization and encoding for:
- Text: BGE-m3 via Ollama (1024d)
- Images: CLIP (openai/clip-vit-base-patch32)
"""

from typing import List, Union, Optional
import numpy as np
import torch
from pathlib import Path
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

try:
    import ollama as _ollama_lib
except ImportError:
    _ollama_lib = None


class EmbeddingManager:
    """Unified manager for text and visual embeddings"""
    
    # Model configurations
    TEXT_MODEL = "bge-m3"          # Served by Ollama
    VISUAL_MODEL = "openai/clip-vit-base-patch32"
    TEXT_DIM = 1024                # BGE-m3 output dimension
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
        
        # ---------- Text embeddings via Ollama ----------
        if _ollama_lib is None:
            raise ImportError(
                "The 'ollama' Python package is required.  "
                "Install it with:  pip install ollama"
            )
        # Verify that the BGE model is available in Ollama
        try:
            _ollama_lib.show(self.TEXT_MODEL)
        except Exception:
            print(f"⚠️  Model '{self.TEXT_MODEL}' not found locally – pulling from Ollama…")
            _ollama_lib.pull(self.TEXT_MODEL)
        self._ollama = _ollama_lib
        print(f"✅ Text model ready (Ollama): {self.TEXT_MODEL} ({self.TEXT_DIM}d)")
        
        # ---------- Visual embeddings (unchanged) ----------
        self.clip_model = CLIPModel.from_pretrained(self.VISUAL_MODEL).to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained(self.VISUAL_MODEL)
        print(f"✅ Visual model loaded: {self.VISUAL_MODEL} ({self.VISUAL_DIM}d)")
    
    def encode_text(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Encode text(s) into embeddings via Ollama BGE-m3
        
        Args:
            texts: Single text or list of texts
            normalize: Normalize embeddings to unit length
            
        Returns:
            numpy array of shape (n, 1024) for text embeddings
        """
        if isinstance(texts, str):
            texts = [texts]
        
        # Ollama embed API accepts a list of inputs
        response = self._ollama.embed(model=self.TEXT_MODEL, input=texts)
        embeddings = np.array(response["embeddings"], dtype=np.float32)
        
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)
        
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

            # Compatibility: some environments may return model outputs instead of tensor
            if not isinstance(image_features, torch.Tensor):
                if hasattr(image_features, 'pooler_output'):
                    image_features = image_features.pooler_output
                elif hasattr(image_features, 'last_hidden_state'):
                    image_features = image_features.last_hidden_state[:, 0, :]
                else:
                    raise TypeError(f"Unexpected CLIP image feature output type: {type(image_features)}")
        
        # Convert to numpy
        embeddings = image_features.detach().cpu().numpy()
        
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

            # Compatibility: some environments may return model outputs instead of tensor
            if not isinstance(text_features, torch.Tensor):
                if hasattr(text_features, 'pooler_output'):
                    text_features = text_features.pooler_output
                elif hasattr(text_features, 'last_hidden_state'):
                    text_features = text_features.last_hidden_state[:, 0, :]
                else:
                    raise TypeError(f"Unexpected CLIP text feature output type: {type(text_features)}")
        
        # Convert to numpy
        embeddings = text_features.detach().cpu().numpy()
        
        # Normalize if requested
        if normalize:
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            embeddings = embeddings / (norms + 1e-8)
        
        return embeddings


def test_embeddings():
    """Test embedding functionality"""
    print("\n🧪 Testing Embedding Manager\n" + "="*50)
    
    manager = EmbeddingManager()
    
    # Test text embeddings (Ollama BGE-m3)
    print("\n📝 Text Embeddings (BGE-m3 via Ollama):")
    texts = ["Hello world", "Bonjour le monde"]
    text_embeds = manager.encode_text(texts)
    print(f"Shape: {text_embeds.shape}  (expected: (2, 1024))")
    print(f"Sample: {text_embeds[0][:5]}")
    
    # Test CLIP text embeddings
    print("\n🔍 CLIP Text Embeddings (for image search):")
    clip_text_embeds = manager.encode_text_for_image_search("a photo of a cat")
    print(f"Shape: {clip_text_embeds.shape}")
    print(f"Sample: {clip_text_embeds[0][:5]}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_embeddings()
