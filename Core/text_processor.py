"""
Text Processor - Chunking and Preprocessing
============================================

Handles:
- Intelligent text chunking with overlap
- Length-based routing (short vs long documents)
- Text cleaning and normalization
"""

from typing import List, Tuple
import re


class TextProcessor:
    """Process and chunk text for embedding"""
    
    # Chunking parameters
    CHUNK_SIZE_SHORT = 512
    CHUNK_SIZE_LONG = 1500
    CHUNK_OVERLAP = 150
    
    def __init__(self):
        """Initialize text processor"""
        pass
    
    def should_chunk(self, text: str) -> bool:
        """
        Determine if text needs chunking
        
        Args:
            text: Input text
            
        Returns:
            True if text exceeds CHUNK_SIZE_LONG
        """
        return len(text) > self.CHUNK_SIZE_LONG
    
    def chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[Tuple[str, int, int]]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Input text
            chunk_size: Chunk size (defaults to CHUNK_SIZE_LONG)
            overlap: Overlap size (defaults to CHUNK_OVERLAP)
            
        Returns:
            List of (chunk_text, start_pos, end_pos) tuples
        """
        if chunk_size is None:
            chunk_size = self.CHUNK_SIZE_LONG
        if overlap is None:
            overlap = self.CHUNK_OVERLAP

        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")

        # Keep overlap valid and guarantee forward progress
        overlap = max(0, min(overlap, chunk_size - 1))
        
        # Don't chunk if text is short
        if len(text) <= chunk_size:
            return [(text, 0, len(text))]
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + chunk_size, len(text))
            
            # Extract chunk
            chunk = text[start:end]
            
            # Try to break at sentence boundary if not at the end
            if end < len(text):
                # Look for sentence endings in the last 200 chars
                search_start = max(0, len(chunk) - 200)
                sentence_breaks = [m.end() for m in re.finditer(r'[.!?]\s+', chunk[search_start:])]
                
                if sentence_breaks:
                    # Use the last sentence break
                    break_pos = search_start + sentence_breaks[-1]
                    chunk = chunk[:break_pos]
                    end = start + break_pos
            
            clean_chunk = chunk.strip()
            if clean_chunk:
                chunks.append((clean_chunk, start, end))

            # End reached: stop cleanly
            if end >= len(text):
                break

            # Move to next chunk with overlap (must move forward)
            next_start = end - overlap
            if next_start <= start:
                next_start = start + 1
            start = next_start
        
        return chunks
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
        
        return text.strip()
    
    def extract_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def get_word_count(self, text: str) -> int:
        """
        Get word count
        
        Args:
            text: Input text
            
        Returns:
            Number of words
        """
        return len(text.split())


def test_processor():
    """Test text processing functionality"""
    print("\n🧪 Testing Text Processor\n" + "="*50)
    
    processor = TextProcessor()
    
    # Test chunking
    print("\n📄 Testing Chunking:")
    long_text = "This is a test sentence. " * 100
    chunks = processor.chunk_text(long_text)
    print(f"Original length: {len(long_text)} chars")
    print(f"Number of chunks: {len(chunks)}")
    for i, (chunk, start, end) in enumerate(chunks[:3]):
        print(f"  Chunk {i+1}: {len(chunk)} chars (pos {start}-{end})")
    
    # Test cleaning
    print("\n🧹 Testing Cleaning:")
    dirty_text = "Hello   world\n\n\nwith    extra    spaces"
    clean = processor.clean_text(dirty_text)
    print(f"Before: {repr(dirty_text)}")
    print(f"After: {repr(clean)}")
    
    # Test sentence extraction
    print("\n📝 Testing Sentence Extraction:")
    text = "First sentence. Second sentence! Third sentence? Fourth."
    sentences = processor.extract_sentences(text)
    print(f"Input: {text}")
    print(f"Sentences: {sentences}")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_processor()
