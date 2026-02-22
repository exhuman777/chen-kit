# CHEN-KIT Export Kit

Reusable components for semantic search, 3D visualization, and RAG chat.

## Files

```
export_kit/
├── search.py              # SemanticIndex - embeddings + ChromaDB
├── constellation.html     # Three.js 3D graph visualization
├── dashboard_snippets.py  # Code snippets to integrate into your app
├── ingest.py              # CLI tool for content ingestion
├── ingest_core.py         # Core ingestion logic (Blueprint system)
└── blueprints/            # Template schemas for content types
    ├── recipes.blueprint.md
    ├── rules.blueprint.md
    ├── inventory.blueprint.md
    └── transcripts.blueprint.md
```

## Dependencies

```bash
pip install sentence-transformers chromadb requests beautifulsoup4 watchdog
```

## Quick Start

### 1. Semantic Search

```python
from search import SemanticIndex, is_available

if is_available():
    idx = SemanticIndex()

    # Index documents (list of dicts with 'name', 'title', 'content', 'meta', 'sections')
    idx.index_recipe(recipe_dict)
    idx.index_rule(rule_dict)

    # Search
    results = idx.search("tofu breakfast", top_k=10, doc_type='recipe')
    # Returns: [{id, score, type, name, title, ...}]

    # Find related
    related = idx.get_related('recipe', 'shakshuka', top_k=5)
```

### 2. Constellation (3D Graph)

```python
import json

# Build data
data = {
    'recipes': [
        {'title': 'Shakshuka', 'tags': ['breakfast'], 'ingredients': ['eggs', 'tomatoes']}
    ],
    'rules': [
        {'title': 'No sugar + flour combo'}
    ]
}

# Inject into HTML
html = open('constellation.html').read()
html = html.replace('{{DATA}}', json.dumps(data))
```

### 3. RAG Chat

```python
# In your HTTP handler:
from dashboard_snippets import handle_chat_api

result = handle_chat_api(query, ALL_RECIPES, ALL_RULES, SEARCH_INDEX)
# Returns: {'response': '...', 'sources': ['doc1', 'doc2']}
```

### 4. Ingest (Content Processing)

```bash
# Transcribe audio
python ingest.py audio voice_memo.m4a

# Process URL
python ingest.py url https://example.com/recipe

# Process text
python ingest.py text notes.txt

# Watch inbox folder
python ingest.py watch
```

## Model Info

- **Embeddings**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
  - Multilingual (PL + EN)
  - 384 dimensions
  - ~120MB model size

- **Vector Store**: ChromaDB (in-memory, cosine similarity)

- **Audio**: Whisper CLI (`/opt/homebrew/bin/whisper-cli`)
  - Model: `~/whisper-models/ggml-small-q5_1.bin`

## Architecture

```
User Query
    │
    ▼
┌─────────────────┐
│ SentenceTransformer │  ← Encode query
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    ChromaDB     │  ← Cosine similarity search
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Claude CLI     │  ← Generate response with context
└────────┬────────┘
         │
         ▼
    Response
```

## Constellation Structure

```
Three.js Scene
    │
    ├── Outer Sphere (r=350): Recipes (pink)
    │       │
    │       └── Fibonacci distribution
    │
    ├── Middle Sphere (r=180): Ingredients (green)
    │       │
    │       └── Connected to recipes that use them
    │
    └── Inner Sphere (r=60): Tags (blue)
            │
            └── Connected to recipes with that tag

Edges connect recipes ↔ ingredients and recipes ↔ tags
```
