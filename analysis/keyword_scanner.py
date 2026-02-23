import logging
from config.product_context import ProductContext

logger = logging.getLogger(__name__)

class KeywordScanner:
    def __init__(self, snippet_radius: int = 400):
        self.snippet_radius = snippet_radius

    def scan_for_context(self, massive_corpus: str, context: ProductContext) -> str:
        logger.info("Scanning full site download for specific product keywords and competitors...")
        search_terms = []
        if context.rfp_keywords: search_terms.extend(context.rfp_keywords)
        if context.direct_competitors: search_terms.extend(context.direct_competitors)
        if context.primary_buyer_titles: search_terms.extend(context.primary_buyer_titles)
        search_terms.extend(["budget", "strategic plan", "RFP", "LMS", "SIS"])
        search_terms = [t.strip().lower() for t in search_terms if t.strip()]

        if not search_terms: return massive_corpus[:40000]

        matches = []
        corpus_lower = massive_corpus.lower()
        
        for term in set(search_terms):
            start = 0
            while True:
                idx = corpus_lower.find(term, start)
                if idx == -1: break
                s_start = max(0, idx - self.snippet_radius)
                s_end = min(len(massive_corpus), idx + len(term) + self.snippet_radius)
                matches.append(massive_corpus[s_start:s_end].strip())
                start = idx + len(term)

        if not matches: return massive_corpus[:40000]

        condensed_corpus = "\n\n...[SNIPPET]...\n\n".join(list(set(matches)))
        logger.info(f"Keyword search yielded {len(matches)} highly-relevant text blocks.")
        return condensed_corpus[:40000]
