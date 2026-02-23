import re
import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class Chunk:
    text: str
    source_url: str
    score: float = 0.0

class LocalRAG:
    """
    A lightweight, keyword-based indexing system for filtering 
    relevant segments from large document sets.
    """
    def __init__(self, keywords: List[str]):
        self.keywords = [k.lower() for k in keywords]
        # High-value signals get higher weight
        self.boost_keywords = {
            "rfp": 3.0,
            "request for proposal": 3.0,
            "contract": 2.0,
            "budget": 2.0,
            "procurement": 2.0,
            "adoption": 3.0,
            "pilot": 5.0, # Extremely high value (intent signal)
            "discussion": 4.0, # Qualitative gold mine
            "minutes": 3.0,
            "superintendent's report": 5.0, # Strategic direction
            "presentation": 3.0,
            "initiative": 4.0,
            "challenge": 3.0,
            "concern": 3.0,
            "bids": 2.0,
            "award": 2.0,
            "purchase": 1.0,
            "technology plan": 4.0,
            "strategic plan": 3.0,
            "board consensus": 4.0
        }

    def chunk_documents(self, documents: List[Dict], chunk_size: int = 2000) -> List[Chunk]:
        """Split document text into manageable chunks."""
        chunks = []
        for doc in documents:
            text = doc.get("content", "")
            url = doc.get("url", "unknown")
            if not text: continue
            
            # Simple overlap chunking
            for i in range(0, len(text), chunk_size - 200):
                segment = text[i:i + chunk_size]
                chunks.append(Chunk(text=segment, source_url=url))
        return chunks

    def rank_chunks(self, chunks: List[Chunk], query_context: str = "") -> List[Chunk]:
        """Score and rank chunks based on relevance to product and board signals."""
        scored_chunks = []
        context_words = [w.lower() for w in query_context.split()] if query_context else []
        
        for chunk in chunks:
            text_lower = chunk.text.lower()
            score = 0.0
            
            # 1. Product keyword matches
            for kw in self.keywords:
                if kw in text_lower:
                    score += 10.0 # High base score for product match
            
            # 2. Board signal boost
            for kw, weight in self.boost_keywords.items():
                if kw in text_lower:
                    score += weight
            
            # 3. Contextual word match (optional)
            for word in context_words:
                if len(word) > 3 and word in text_lower:
                    score += 0.5
            
            chunk.score = score
            if score > 0:
                scored_chunks.append(chunk)
                
        # Sort by score descending
        return sorted(scored_chunks, key=lambda x: x.score, reverse=True)

    def get_context_for_claude(self, documents: List[Dict], product_category: str, max_tokens_approx: int = 15000) -> str:
        """The core RAG-lite workflow: Chunk -> Rank -> Assemble."""
        chunks = self.chunk_documents(documents)
        ranked = self.rank_chunks(chunks, query_context=product_category)
        
        # Take the most relevant chunks until we hit the budget
        selected_text = []
        current_len = 0
        char_limit = max_tokens_approx * 3 # Rough conversion
        
        for chunk in ranked:
            snippet = f"\n--- Source: {chunk.source_url} (Score: {chunk.score}) ---\n{chunk.text}\n"
            if current_len + len(snippet) > char_limit:
                break
            selected_text.append(snippet)
            current_len += len(snippet)
            
        return "".join(selected_text) if selected_text else "No explicitly relevant segments found."
