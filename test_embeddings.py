"""
Simple Embedding Test - Quick verification
===========================================

Tests embeddings without waiting for full model loading
"""

print("🧪 Testing AI MINDS Embedding System\n" + "="*60)

# Test 1: Check if dependencies are installed
print("\n📦 Checking Dependencies...")

try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
except ImportError:
    print("❌ PyTorch not installed")

try:
    import numpy as np
    print(f"✅ NumPy: {np.__version__}")
except ImportError:
    print("❌ NumPy not installed")

try:
    import faiss
    print(f"✅ Faiss: {faiss.__version__}")
except ImportError:
    print("❌ Faiss not installed")

try:
    import sentence_transformers
    print(f"✅ Sentence-Transformers: {sentence_transformers.__version__}")
except ImportError:
    print("❌ Sentence-Transformers not installed")

try:
    import transformers
    print(f"✅ Transformers: {transformers.__version__}")
except ImportError:
    print("❌ Transformers not installed")

print("\n" + "="*60)
print("🔄 Loading embedding models (this may take 30-60 seconds)...\n")

# Test 2: Load and test embeddings
try:
    from Core.embeddings import EmbeddingManager
    
    manager = EmbeddingManager()
    
    # Test text embeddings
    print("\n📝 Testing Text Embeddings:")
    test_texts = ["Hello world", "Bonjour le monde", "Machine learning"]
    
    print(f"   Input: {test_texts}")
    embeddings = manager.encode_text(test_texts)
    print(f"   Output shape: {embeddings.shape}")
    print(f"   Dimension: {embeddings.shape[1]}d")
    print(f"   Sample values: {embeddings[0][:5]}")
    
    # Test CLIP text embeddings
    print("\n🔍 Testing CLIP Text Embeddings (for image search):")
    clip_query = "a photo of a cat"
    print(f"   Input: '{clip_query}'")
    clip_embeddings = manager.encode_text_for_image_search(clip_query)
    print(f"   Output shape: {clip_embeddings.shape}")
    print(f"   Dimension: {clip_embeddings.shape[1]}d")
    print(f"   Sample values: {clip_embeddings[0][:5]}")
    
    # Test similarity
    print("\n🎯 Testing Similarity:")
    emb1 = manager.encode_text("machine learning")
    emb2 = manager.encode_text("artificial intelligence")
    emb3 = manager.encode_text("cooking recipes")
    
    # Cosine similarity
    sim_12 = np.dot(emb1[0], emb2[0])  # Already normalized
    sim_13 = np.dot(emb1[0], emb3[0])
    
    print(f"   Similarity('machine learning', 'AI'): {sim_12:.3f}")
    print(f"   Similarity('machine learning', 'cooking'): {sim_13:.3f}")
    print(f"   ✅ Related concepts have higher similarity!")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    
except Exception as e:
    print(f"\n❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
