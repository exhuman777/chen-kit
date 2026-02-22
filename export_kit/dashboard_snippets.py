"""
CHEN-KIT Dashboard Snippets
Kluczowe fragmenty do skopiowania do własnego projektu
"""

# =============================================================================
# 1. IMPORTS & SETUP (na górze dashboard.py)
# =============================================================================

# Optional semantic search
try:
    from search import SemanticIndex, is_available as semantic_available
    SEMANTIC_ENABLED = semantic_available()
except ImportError:
    SEMANTIC_ENABLED = False
    SemanticIndex = None

# Global search index
SEARCH_INDEX = None

# =============================================================================
# 2. INITIALIZE SEARCH INDEX (po załadowaniu dokumentów)
# =============================================================================

def init_search_index(recipes, rules, transcripts):
    """Initialize semantic search index"""
    global SEARCH_INDEX
    if SEMANTIC_ENABLED:
        print("[APP] Loading semantic search model...")
        SEARCH_INDEX = SemanticIndex()
        count = SEARCH_INDEX.index_all(recipes, rules, transcripts)
        print(f"[APP] Indexed {count} documents for semantic search")


# =============================================================================
# 3. MARKDOWN TO HTML HELPER
# =============================================================================

def md_to_html(text):
    """Convert basic markdown to HTML (bold only)"""
    import re
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text


# =============================================================================
# 4. RAG CHAT API ENDPOINT (w do_POST)
# =============================================================================

def handle_chat_api(query, ALL_RECIPES, ALL_RULES, SEARCH_INDEX):
    """
    RAG Chat - semantic search + Claude CLI

    Użycie w do_POST:
    if parsed.path == '/api/chat':
        result = handle_chat_api(query, ALL_RECIPES, ALL_RULES, SEARCH_INDEX)
        return json.dumps(result)
    """
    import subprocess
    import json

    context_parts = []
    source_names = []

    if SEARCH_INDEX:
        # Search recipes
        results = SEARCH_INDEX.search(query, top_k=5, doc_type='recipe')
        for hit in results:
            name = hit.get('name', '')
            source_names.append(name)
            recipe = next((r for r in ALL_RECIPES if r['name'] == name), None)
            if recipe:
                context_parts.append(f"## {recipe.get('title', name)}\n{recipe.get('content', '')[:800]}")

        # Search rules
        rule_results = SEARCH_INDEX.search(query, top_k=3, doc_type='rule')
        for hit in rule_results:
            name = hit.get('name', '')
            rule = next((r for r in ALL_RULES if r['name'] == name), None)
            if rule:
                context_parts.append(f"## Zasada: {rule.get('title', name)}\n{rule.get('content', '')[:500]}")

    context = "\n\n---\n\n".join(context_parts) if context_parts else "Brak pasujących dokumentów."

    prompt = f"""Na podstawie poniższego kontekstu z bazy danych, odpowiedz na pytanie użytkownika.
Odpowiadaj zwięźle i konkretnie.

KONTEKST:
{context}

PYTANIE: {query}

ODPOWIEDŹ:"""

    try:
        result = subprocess.run(
            ['claude', '-p', prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        response = result.stdout.strip() if result.returncode == 0 else "Błąd generowania odpowiedzi."
    except Exception as e:
        response = f"Błąd: {str(e)}"

    return {'response': response, 'sources': source_names[:5]}


# =============================================================================
# 5. CONSTELLATION DATA BUILDER
# =============================================================================

def build_constellation_data(recipes, rules):
    """
    Build data for 3D constellation visualization
    Returns JSON-serializable dict for injection into constellation.html
    """
    import re

    data = {'recipes': [], 'rules': []}

    for r in recipes:
        title = r.get('title', r['name']).replace('Recipe: ', '')
        tags = r.get('meta', {}).get('tags', '').replace('[', '').replace(']', '')
        tag_list = [t.strip() for t in re.split(r'[,\s]+', tags) if t.strip()]

        ingredients = []
        if 'Ingredients' in r.get('sections', {}):
            for line in r['sections']['Ingredients'][:10]:
                ing = line.lstrip('- [ ] ').strip()
                if ing:
                    ingredients.append(ing[:25])

        data['recipes'].append({
            'title': title,
            'tags': tag_list,
            'ingredients': ingredients
        })

    for r in rules:
        title = r.get('title', r['name']).replace('# ', '').strip()
        data['rules'].append({'title': title})

    return data


def serve_constellation(recipes, rules, html_template_path):
    """
    Serve constellation HTML with injected data

    html_template_path: Path to constellation.html
    Returns: HTML string ready to send
    """
    import json

    data = build_constellation_data(recipes, rules)
    html = html_template_path.read_text(encoding='utf-8')
    html = html.replace('{{DATA}}', json.dumps(data, ensure_ascii=False))
    return html


# =============================================================================
# 6. CHAT UI (HTML do wstawienia w template)
# =============================================================================

CHAT_BUTTON_HTML = '''
<button onclick="toggleChat()" style="background:#238636;border:none;border-radius:4px;color:white;padding:5px 12px;cursor:pointer;font-size:11px">💬 Chat</button>
'''

CHAT_PANEL_HTML = '''
<!-- RAG Chat Panel -->
<div id="chat-panel" style="display:none;position:fixed;right:20px;bottom:20px;width:400px;max-height:500px;background:#161b22;border:1px solid #30363d;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,0.4);z-index:1000;flex-direction:column">
    <div style="padding:12px 16px;border-bottom:1px solid #30363d;display:flex;justify-content:space-between;align-items:center">
        <span style="font-weight:bold;color:#58a6ff">💬 Chat</span>
        <button onclick="toggleChat()" style="background:none;border:none;color:#8b949e;cursor:pointer;font-size:16px">✕</button>
    </div>
    <div id="chat-messages" style="flex:1;overflow-y:auto;padding:12px;min-height:300px;max-height:350px"></div>
    <div style="padding:12px;border-top:1px solid #30363d;display:flex;gap:8px">
        <input type="text" id="chat-input" placeholder="Zapytaj..." style="flex:1;padding:10px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-family:inherit" onkeypress="if(event.key==='Enter')sendChat()">
        <button onclick="sendChat()" style="background:#238636;border:none;border-radius:6px;color:white;padding:10px 16px;cursor:pointer">➤</button>
    </div>
</div>

<script>
function toggleChat() {
    const panel = document.getElementById('chat-panel');
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
    if (panel.style.display === 'flex') document.getElementById('chat-input').focus();
}

async function sendChat() {
    const input = document.getElementById('chat-input');
    const messages = document.getElementById('chat-messages');
    const query = input.value.trim();
    if (!query) return;

    messages.innerHTML += `<div style="margin-bottom:12px;text-align:right"><div style="display:inline-block;background:#238636;color:white;padding:8px 12px;border-radius:12px 12px 0 12px;max-width:80%">${query}</div></div>`;
    input.value = '';
    messages.scrollTop = messages.scrollHeight;

    const loadingId = 'loading-' + Date.now();
    messages.innerHTML += `<div id="${loadingId}" style="margin-bottom:12px"><div style="display:inline-block;background:#21262d;color:#8b949e;padding:8px 12px;border-radius:12px">⏳ Szukam...</div></div>`;

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query})
        });
        const data = await res.json();
        document.getElementById(loadingId).remove();

        let html = `<div style="margin-bottom:12px"><div style="display:inline-block;background:#21262d;color:#c9d1d9;padding:8px 12px;border-radius:12px;max-width:85%">${data.response.replace(/\\n/g, '<br>')}</div>`;
        if (data.sources && data.sources.length) {
            html += `<div style="font-size:10px;color:#8b949e;margin-top:4px">📚 ${data.sources.slice(0,3).join(', ')}</div>`;
        }
        html += '</div>';
        messages.innerHTML += html;
    } catch(e) {
        document.getElementById(loadingId).remove();
        messages.innerHTML += `<div style="margin-bottom:12px"><div style="display:inline-block;background:#f85149;color:white;padding:8px 12px;border-radius:12px">Błąd: ${e.message}</div></div>`;
    }
    messages.scrollTop = messages.scrollHeight;
}
</script>
'''


# =============================================================================
# 7. SEARCH USAGE EXAMPLES
# =============================================================================

"""
# Basic search
results = SEARCH_INDEX.search("tofu przepis", top_k=10, doc_type='recipe')
for hit in results:
    print(f"{hit['name']}: {hit['score']:.2f}")

# Get related documents
related = SEARCH_INDEX.get_related('recipe', 'shakshuka', top_k=5)

# Hybrid search (semantic + keyword)
results = SEARCH_INDEX.hybrid_search(
    query="śniadanie z jajkiem",
    keyword_results=keyword_matches,  # from your existing search
    semantic_weight=0.7
)
"""
