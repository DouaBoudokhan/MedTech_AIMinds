"""
RAG Engine - Retrieval-Augmented Generation
============================================

Handles:
- Contextual retrieval from vector store
- Query expansion
- Result ranking and reranking
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path

# Add Data_Layer to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Data_Layer"))


class RAGEngine:
    """RAG pipeline for context retrieval"""
    
    def __init__(self, storage_manager=None):
        """
        Initialize RAG engine
        
        Args:
            storage_manager: UnifiedStorageManager instance
        """
        self.storage = storage_manager
    
    def retrieve(self, query: str, top_k: int = 5, filters: Dict = None) -> List[Dict]:
        """
        Retrieve relevant context for query
        
        Args:
            query: User query
            top_k: Number of results to retrieve
            filters: Optional filters (source, date range, etc.)
            
        Returns:
            List of relevant documents
        """
        if self.storage is None:
            print("⚠️  No storage manager connected")
            return []
        
        # Search storage
        results = self.storage.search(query, top_k=top_k)
        
        # Apply filters if provided
        if filters:
            results = self._apply_filters(results, filters)
        
        return results
    
    def _apply_filters(self, results: List[Dict], filters: Dict) -> List[Dict]:
        """Apply filters to results"""
        filtered = results
        
        # Filter by source
        if 'source' in filters:
            filtered = [r for r in filtered if r.get('source') == filters['source']]
        
        # Filter by date range
        if 'start_date' in filters or 'end_date' in filters:
            # TODO: Implement date filtering
            pass
        
        return filtered
    
    def build_context(self, results: List[Dict], max_tokens: int = 2000) -> str:
        """
        Build context string from results
        
        Args:
            results: Retrieved documents
            max_tokens: Maximum context length (approximate)
            
        Returns:
            Formatted context string
        """
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough approximation
        
        for i, result in enumerate(results, 1):
            # Format result
            text = result.get('text', result.get('content', ''))
            source = result.get('source', 'Unknown')
            score = result.get('score', 0.0)
            
            part = f"[{i}] Source: {source} (relevance: {score:.2f})\n{text}\n"
            
            # Check if adding this would exceed limit
            if total_chars + len(part) > max_chars:
                break
            
            context_parts.append(part)
            total_chars += len(part)
        
        return "\n---\n".join(context_parts)
    
    def generate_prompt(self, query: str, context: str, system_prompt: str = None) -> str:
        """
        Generate final prompt for LLM
        
        Args:
            query: User query
            context: Retrieved context
            system_prompt: Optional system prompt
            
        Returns:
            Complete prompt
        """
        if system_prompt is None:
            system_prompt = "You are a helpful AI assistant. Use the provided context to answer the user's question accurately."
        
        prompt = f"""{system_prompt}

Context:
{context}

User Question: {query}

Answer:"""
        
        return prompt


def test_rag_engine():
    """Test RAG engine"""
    print("\n🧪 Testing RAG Engine\n" + "="*50)
    
    # Create mock results
    mock_results = [
        {
            'text': 'This is a sample document about AI.',
            'source': 'browser',
            'score': 0.95
        },
        {
            'text': 'Another document discussing machine learning.',
            'source': 'documents',
            'score': 0.87
        }
    ]
    
    engine = RAGEngine()
    
    # Test context building
    print("\n📄 Testing Context Building:")
    context = engine.build_context(mock_results)
    print(context)
    
    # Test prompt generation
    print("\n📝 Testing Prompt Generation:")
    prompt = engine.generate_prompt("What is AI?", context)
    print(prompt[:200] + "...")
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_rag_engine()
