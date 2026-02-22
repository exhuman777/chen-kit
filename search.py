#!/usr/bin/env python3
"""
CHEN-KIT Semantic Search Module
Local embeddings with ChromaDB vector store
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

# Multilingual model - handles Polish + English
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class SemanticIndex:
    """Vector-based semantic search over markdown content."""

    def __init__(self, persist_dir: Optional[Path] = None):
        if not SEMANTIC_AVAILABLE:
            raise ImportError("Install: pip install sentence-transformers chromadb")

        self.model = SentenceTransformer(MODEL_NAME)

        # In-memory ChromaDB (fast startup, rebuilds each run)
        self.client = chromadb.Client()
        self.collection = self.client.create_collection(
            name="chenkit",
            metadata={"hnsw:space": "cosine"}
        )
        self._connections: Dict[str, List[str]] = {}

    def _chunk_text(self, text: str, max_tokens: int = 400) -> List[str]:
        """Split text into chunks for embedding."""
        # Simple paragraph-based chunking
        paragraphs = re.split(r'\n\n+', text)
        chunks = []
        current = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para.split())
            if current_len + para_len > max_tokens and current:
                chunks.append('\n\n'.join(current))
                current = [para]
                current_len = para_len
            else:
                current.append(para)
                current_len += para_len

        if current:
            chunks.append('\n\n'.join(current))

        return chunks if chunks else [text[:2000]]

    def index_recipe(self, recipe: Dict) -> None:
        """Index a recipe document."""
        doc_id = f"recipe:{recipe['name']}"

        # Combine key fields for embedding
        parts = [recipe.get('title', recipe['name'])]

        if recipe.get('meta', {}).get('tags'):
            parts.append(f"Tags: {recipe['meta']['tags']}")

        if recipe.get('items'):
            parts.append("Skladniki: " + ", ".join(recipe['items'][:15]))

        for section, lines in recipe.get('sections', {}).items():
            if section.lower() in ['steps', 'kroki', 'przygotowanie']:
                parts.append('\n'.join(lines[:10]))

        content = '\n'.join(parts)

        self.collection.add(
            ids=[doc_id],
            documents=[content],
            metadatas=[{
                "type": "recipe",
                "name": recipe['name'],
                "title": recipe.get('title', recipe['name']),
                "tags": recipe.get('meta', {}).get('tags', ''),
                "path": str(recipe.get('path', ''))
            }]
        )

    def index_rule(self, rule: Dict) -> None:
        """Index a knowledge base article, section by section."""
        base_id = f"rule:{rule['name']}"

        # Index full document
        full_content = f"{rule.get('title', rule['name'])}\n\n{rule['content'][:1500]}"

        self.collection.add(
            ids=[base_id],
            documents=[full_content],
            metadatas=[{
                "type": "rule",
                "name": rule['name'],
                "title": rule.get('title', rule['name']),
                "category": rule.get('meta', {}).get('category', ''),
                "section": "",
                "path": str(rule.get('path', ''))
            }]
        )

        # Also index each section for granular search
        for section, lines in rule.get('sections', {}).items():
            if len(lines) < 2:
                continue

            section_id = f"{base_id}:{section}"
            section_content = f"{rule.get('title', '')} - {section}\n" + '\n'.join(lines)

            self.collection.add(
                ids=[section_id],
                documents=[section_content],
                metadatas=[{
                    "type": "rule",
                    "name": rule['name'],
                    "title": rule.get('title', rule['name']),
                    "category": rule.get('meta', {}).get('category', ''),
                    "section": section,
                    "path": str(rule.get('path', ''))
                }]
            )

    def index_transcript(self, transcript: Dict) -> None:
        """Index a transcript with chunking."""
        chunks = self._chunk_text(transcript['content'])

        for i, chunk in enumerate(chunks):
            doc_id = f"transcript:{transcript['name']}:{i}"

            self.collection.add(
                ids=[doc_id],
                documents=[chunk],
                metadatas=[{
                    "type": "transcript",
                    "name": transcript['name'],
                    "title": transcript.get('title', transcript['name']),
                    "chunk": i,
                    "path": str(transcript.get('path', ''))
                }]
            )

    def index_all(self, recipes: List[Dict], rules: List[Dict],
                  transcripts: List[Dict] = None) -> int:
        """Index all documents. Returns count."""
        count = 0

        for r in recipes:
            self.index_recipe(r)
            count += 1

        for r in rules:
            self.index_rule(r)
            count += 1

        if transcripts:
            for t in transcripts:
                self.index_transcript(t)
                count += 1

        self._build_connections(recipes, rules)
        return count

    def search(self, query: str, top_k: int = 10,
               doc_type: str = None) -> List[Dict]:
        """
        Semantic search. Returns list of:
        {id, score, type, name, title, section, path}
        """
        where = {"type": doc_type} if doc_type else None

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["metadatas", "distances"]
        )

        hits = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                meta = results['metadatas'][0][i]
                # ChromaDB returns distances; convert to similarity
                distance = results['distances'][0][i] if results['distances'] else 0
                score = max(0, 1 - distance)  # cosine distance → similarity

                hits.append({
                    "id": doc_id,
                    "score": round(score, 3),
                    **meta
                })

        return hits

    def hybrid_search(self, query: str, keyword_results: List[Dict],
                      top_k: int = 15, semantic_weight: float = 0.7) -> List[Dict]:
        """
        Combine semantic + keyword search results.
        keyword_results: list of {name, type, ...} from existing search
        """
        semantic = self.search(query, top_k=top_k)

        # Build score map
        scores = {}
        for hit in semantic:
            key = (hit['type'], hit['name'])
            scores[key] = hit['score'] * semantic_weight
            scores[f"_meta_{key}"] = hit

        # Add keyword boost
        keyword_weight = 1 - semantic_weight
        for i, kw in enumerate(keyword_results):
            key = (kw.get('type', 'recipe'), kw.get('name', ''))
            boost = keyword_weight * (1 - i * 0.05)  # Decay by position
            scores[key] = scores.get(key, 0) + boost
            if f"_meta_{key}" not in scores:
                scores[f"_meta_{key}"] = {**kw, "score": boost}

        # Sort by combined score
        combined = []
        for key, score in scores.items():
            if not str(key).startswith("_meta_"):
                meta = scores.get(f"_meta_{key}", {})
                combined.append({**meta, "score": round(score, 3)})

        combined.sort(key=lambda x: x.get('score', 0), reverse=True)
        return combined[:top_k]

    def _build_connections(self, recipes: List[Dict], rules: List[Dict]) -> None:
        """Build hyperlink connection map based on shared terms."""
        # Extract key terms from each doc
        doc_terms = {}

        for r in recipes:
            terms = set()
            for item in r.get('items', []):
                # Extract nouns >4 chars
                for word in re.findall(r'\b[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{4,}\b', item.lower()):
                    terms.add(word)
            doc_terms[f"recipe:{r['name']}"] = terms

        for r in rules:
            terms = set()
            for word in re.findall(r'\b[a-zA-ZąćęłńóśźżĄĆĘŁŃÓŚŹŻ]{4,}\b', r['content'].lower()):
                terms.add(word)
            doc_terms[f"rule:{r['name']}"] = terms

        # Find connections (shared terms)
        self._connections = {}
        docs = list(doc_terms.keys())

        for i, doc1 in enumerate(docs):
            connections = []
            for doc2 in docs[i+1:]:
                shared = doc_terms[doc1] & doc_terms[doc2]
                if len(shared) >= 3:  # At least 3 shared terms
                    connections.append(doc2)
            if connections:
                self._connections[doc1] = connections[:5]  # Top 5 connections

    def get_related(self, doc_type: str, name: str, top_k: int = 5) -> List[str]:
        """Get related documents by term overlap."""
        key = f"{doc_type}:{name}"
        return self._connections.get(key, [])[:top_k]


def is_available() -> bool:
    """Check if semantic search dependencies are installed."""
    return SEMANTIC_AVAILABLE
