"""
RAG Engine - Retrieval-Augmented Generation
============================================

Handles:
- Contextual retrieval from vector store
- Query expansion
- Result ranking and reranking
- Context formatting for LLM consumption
"""

from typing import List, Dict, Optional
import json
import sys
from pathlib import Path

# Add Data_Layer to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Data_Layer"))


class RAGEngine:
    """RAG pipeline for context retrieval and augmented generation"""
    
    def __init__(self, storage_manager=None):
        """
        Initialize RAG engine
        
        Args:
            storage_manager: UnifiedStorageManager instance
        """
        self.storage = storage_manager
    
    def retrieve(self, query: str, top_k: int = 5, filters: Dict = None,
                 search_type: str = 'text') -> List[Dict]:
        """
        Retrieve relevant context for query
        
        Args:
            query: User query
            top_k: Number of results to retrieve
            filters: Optional filters (source, date range, etc.)
            search_type: 'text', 'visual', or 'both'
            
        Returns:
            List of relevant documents with text content
        """
        if self.storage is None:
            print("⚠️  No storage manager connected")
            return []
        
        # Search storage (now returns enriched results with text)
        results = self.storage.search(query, top_k=top_k, search_type=search_type)
        
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
        
        # Filter by type (text/visual)
        if 'type' in filters:
            filtered = [r for r in filtered if r.get('type') == filters['type']]
        
        # Filter by minimum score
        if 'min_score' in filters:
            min_score = filters['min_score']
            filtered = [r for r in filtered if r.get('score', 0) >= min_score]
        
        return filtered
    
    def build_context(self, results: List[Dict], max_tokens: int = 2000) -> str:
        """
        Build context string from results
        
        Args:
            results: Retrieved documents (enriched with text content)
            max_tokens: Maximum context length (approximate)
            
        Returns:
            Formatted context string
        """
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough approximation
        
        for i, result in enumerate(results, 1):
            # Get text from enriched result
            text = result.get('text', result.get('content', ''))
            
            # For visual results without OCR text, still include the image path
            if not text and result.get('type') == 'visual' and result.get('path'):
                text = f"[Image file: {result['path']}]"
            
            if not text:
                continue
                
            source = result.get('source', 'Unknown')
            score = result.get('score', 0.0)
            result_type = result.get('type', 'text')
            created_at = result.get('created_at', '')
            
            # Extract useful metadata for context
            metadata = result.get('metadata', {})
            meta_parts = []
            if isinstance(metadata, dict):
                title = metadata.get('title', '')
                url = metadata.get('url', '')
                domain = metadata.get('domain', '')
                image_path = metadata.get('image_path', '') or metadata.get('full_path', '')
                if title:
                    meta_parts.append(f"Title: {title}")
                if domain:
                    meta_parts.append(f"Domain: {domain}")
                elif url:
                    meta_parts.append(f"URL: {url}")
                if image_path:
                    meta_parts.append(f"Image Path: {image_path}")
            
            # Include image path from visual results directly
            if result.get('path'):
                meta_parts.append(f"Image Path: {result['path']}")
            
            # Format result entry
            header = f"[{i}] Source: {source} | Type: {result_type} | Relevance: {score:.2f}"
            if created_at:
                header += f" | Date: {created_at[:10]}"
            
            part = header + "\n"
            if meta_parts:
                part += " | ".join(meta_parts) + "\n"
            part += text + "\n"
            
            # Check if adding this would exceed limit
            if total_chars + len(part) > max_chars:
                break
            
            context_parts.append(part)
            total_chars += len(part)
        
        if not context_parts:
            return ""
        
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
            system_prompt = (
                "You are a helpful AI assistant with access to the user's personal knowledge base. "
                "Use the provided context to answer the user's question accurately. "
                "If the context doesn't contain relevant information, say so honestly."
            )
        
        prompt = f"""{system_prompt}

Context:
{context}

User Question: {query}

Answer:"""
        
        return prompt
    
    def query(self, query: str, top_k: int = 5, search_type: str = 'text',
              max_context_tokens: int = 2000) -> Dict:
        """
        Full RAG query - retrieve + build context in one call.
        
        Args:
            query: User query
            top_k: Number of results
            search_type: 'text', 'visual', or 'both'
            max_context_tokens: Max context size
            
        Returns:
            Dict with 'context', 'results', 'num_results'
        """
        results = self.retrieve(query, top_k=top_k, search_type=search_type)
        context = self.build_context(results, max_tokens=max_context_tokens)
        
        return {
            'context': context,
            'results': results,
            'num_results': len(results),
        }
    
    def get_stats(self) -> Dict:
        """Get RAG pipeline statistics"""
        if self.storage is None:
            return {'status': 'not_initialized', 'message': 'No storage manager connected'}
        
        try:
            stats = self.storage.get_stats()
            stats['status'] = 'ready'
            stats['text_embeddings_ready'] = self.storage._text_embeddings_ready()
            stats['visual_embeddings_ready'] = self.storage._visual_embeddings_ready()
            return stats
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


def test_rag_engine():
    """Test RAG engine"""
    print("\n🧪 Testing RAG Engine\n" + "="*50)
    
    # Create mock results (enriched format)
    mock_results = [
        {
            'text': 'This is a sample document about AI.',
            'source': 'browser',
            'score': 0.95,
            'type': 'text',
            'metadata': {'title': 'AI Overview', 'url': 'https://example.com/ai'},
        },
        {
            'text': 'Another document discussing machine learning.',
            'source': 'documents',
            'score': 0.87,
            'type': 'text',
            'metadata': {'title': 'ML Guide'},
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
