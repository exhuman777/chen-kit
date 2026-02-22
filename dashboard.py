#!/usr/bin/env python3
"""
CHEN-KIT v2.0 - Personal Kitchen Knowledge System
Run: python3 dashboard.py
Open: http://localhost:5555
"""

import os
import re
import json
import socket
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, quote
from collections import Counter

# Optional semantic search
try:
    from search import SemanticIndex, is_available as semantic_available
    SEMANTIC_ENABLED = semantic_available()
except ImportError:
    SEMANTIC_ENABLED = False
    SemanticIndex = None

BASE = Path(__file__).parent
INVENTORY = BASE / "inventory"
RECIPES = BASE / "recipes"
RULES = BASE / "rules"
TRANSCRIPTS = BASE / "transcripts"
SHOPLIST_FILE = BASE / ".shoplist.json"
CORE_RULES_FILE = RULES / "00-glowne-zasady.md"

# PL→EN translation maps (complete phrases only, no word-by-word)
TITLE_TRANSLATIONS = {
    'Główne Zasady Żywieniowe': 'Core Nutritional Rules',
    'Główne Zasady Diety': 'Core Diet Rules',
    'Praktyki TCM i Zdrowie Organów': 'TCM Practices & Organ Health',
    'Ajurweda: Balans i Trawienie': 'Ayurveda: Balance & Digestion',
    'Źródła Białka Roślinnego': 'Plant Protein Sources',
    'Przyprawy w Ajurwedzie': 'Ayurvedic Spices',
    'Reset Układu Nerwowego': 'Nervous System Reset',
    'Składniki i Techniki Kulinarne': 'Ingredients & Culinary Techniques',
    'Składniki Leczniczych Zup': 'Healing Soup Ingredients',
    'Moczenie Stóp (TCM)': 'Foot Soaking (TCM)',
    'Herbaty na Młodość': 'Anti-Aging Teas',
    'Właściwości Fasolki Adzuki': 'Adzuki Bean Properties',
    'Równowaga po Podróży': 'Post-Travel Balance',
    'Wsparcie Płuc i Yin': 'Lung & Yin Support',
    'Zimne Dłonie i Stopy': 'Cold Hands & Feet',
    'Ajurwedyjski Napar CCF': 'Ayurvedic CCF Infusion',
    'Moczenie Roślin Strączkowych': 'Soaking Legumes',
    'Podstawy Kitchari': 'Kitchari Basics',
    'Ghee i Oleje': 'Ghee & Oils',
    'Zasady Śniadania': 'Breakfast Rules',
    'Zasady Kolacji': 'Dinner Rules',
    'Przygotowanie Tofu': 'Tofu Preparation',
    'Daktyle - Naturalny Słodzik': 'Dates - Natural Sweetener',
    'Daktyle – Naturalny Słodzik': 'Dates – Natural Sweetener',
    'Zdrowe Zamienniki': 'Healthy Substitutes',
}

SECTION_TRANSLATIONS = {
    'Zasady': 'Rules',
    'Zakazy': 'Prohibitions',
    'Praktyki': 'Practices',
    'Zasady Posiłków': 'Meal Rules',
    'Napoje i Dodatki': 'Drinks & Supplements',
    'Rytuały Wieczorne (Moczenie Stóp)': 'Evening Rituals (Foot Soaking)',
    'Płuca (Niedobór Yin)': 'Lungs (Yin Deficiency)',
    'Nerki i Witalność': 'Kidneys & Vitality',
    'Ogień Trawienny (Agni)': 'Digestive Fire (Agni)',
    'Balansowanie Vata': 'Balancing Vata',
    'Budowanie Ojas (Esencja Życia)': 'Building Ojas (Life Essence)',
    'Tryb Przetrwania': 'Survival Mode',
    'Źródła Białka (Wegańskie)': 'Protein Sources (Vegan)',
    'Bulion Mocy (Wzmacnianie Zupy)': 'Power Broth (Soup Enhancement)',
    'Zioła Anti-Aging (Herbaty)': 'Anti-Aging Herbs (Teas)',
    'Notes': 'Notes',
    'Mindset': 'Mindset',
}

def tr_title(text, lang='pl'):
    """Translate a title if lang=en, else return as-is"""
    if lang == 'en':
        return TITLE_TRANSLATIONS.get(text, text)
    return text

def tr_section(text, lang='pl'):
    """Translate a section header if lang=en, else return as-is"""
    if lang == 'en':
        return SECTION_TRANSLATIONS.get(text, text)
    return text

# Words to ignore in matching (common adjectives, units, etc.)
IGNORE_WORDS = {
    'swieze', 'swiezy', 'swieza', 'mielony', 'mielona', 'mielone',
    'suszone', 'suszony', 'suszona', 'cale', 'caly', 'cala',
    'male', 'maly', 'mala', 'duze', 'duzy', 'duza',
    'czerwone', 'czerwony', 'czerwona', 'biale', 'bialy', 'biala',
    'zolte', 'zolty', 'zolta', 'czarne', 'czarny', 'czarna',
    'lyzka', 'lyzki', 'lyzek', 'szklanka', 'szklanki',
    'gram', 'sztuk', 'sztuki', 'opakowanie', 'puszka', 'sloik',
    'okolo', 'kilka', 'garsc', 'troche', 'duzo', 'malo',
    'wedzone', 'wedzony', 'wedzona', 'prazone', 'prazony', 'prazona',
    'naturalne', 'naturalny', 'naturalna', 'ekologiczne', 'bio',
    'pelnoziarniste', 'pelnoziarnisty', 'razowe', 'razowy',
    'zimnotloczony', 'nierafinowany', 'extra', 'virgin'
}

def parse_md(path):
    content = path.read_text(encoding='utf-8')
    result = {'name': path.stem, 'content': content, 'items': [], 'meta': {}, 'sections': {}}

    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if m:
        result['title'] = m.group(1)

    for m in re.finditer(r'^(\w+):\s*(.+)$', content, re.MULTILINE):
        result['meta'][m.group(1).lower()] = m.group(2)

    for m in re.finditer(r'^-\s*\[[ x]\]\s*(.+)$', content, re.MULTILINE):
        result['items'].append(m.group(1).strip())

    current = None
    for line in content.split('\n'):
        if line.startswith('## '):
            current = line[3:].strip()
            result['sections'][current] = []
        elif current and line.strip():
            result['sections'][current].append(line.strip())

    return result

def load_folder(folder):
    if not folder.exists():
        return []
    return [parse_md(f) for f in sorted(folder.glob("*.md")) if not f.name.startswith('_')]

def get_inventory():
    items = set()
    for inv in load_folder(INVENTORY):
        items.update(inv['items'])
    return items

def get_inventory_by_category():
    categories = {}
    for inv in load_folder(INVENTORY):
        for section, lines in inv.get('sections', {}).items():
            if section not in categories:
                categories[section] = []
            for line in lines:
                if line.startswith('- '):
                    categories[section].append(line[2:].strip().replace('[ ] ', ''))
    return categories

def extract_key_words(text):
    """Extract meaningful words, ignoring common adjectives and units"""
    words = []
    for w in text.lower().replace(',', ' ').replace('(', ' ').replace(')', ' ').split():
        w = w.strip()
        if len(w) > 3 and w not in IGNORE_WORDS and not w.isdigit():
            # Remove trailing numbers like "400g"
            w = re.sub(r'\d+g?$', '', w)
            if len(w) > 3:
                words.append(w)
    return words

def ingredient_match(item, inventory):
    """Smart ingredient matching - matches on key nouns, not adjectives"""
    item_words = extract_key_words(item)
    if not item_words:
        return False

    for inv in inventory:
        inv_lower = inv.lower()
        inv_words = extract_key_words(inv)

        # Check if main ingredient word matches
        for word in item_words:
            # Direct substring match on the key word
            if word in inv_lower:
                return True
            # Check reverse - inv word in item
            for inv_word in inv_words:
                if inv_word in item.lower() and len(inv_word) > 4:
                    return True
    return False

def score_recipe(recipe, inventory):
    if not recipe['items']:
        return 0
    found = sum(1 for item in recipe['items'] if ingredient_match(item, inventory))
    return int(found / len(recipe['items']) * 100)

def get_recipe_tags_stats(recipes):
    tags = Counter()
    for r in recipes:
        tag_str = r['meta'].get('tags', '')
        for tag in re.split(r'[,\s]+', tag_str):
            tag = tag.strip().lower()
            if tag:
                tags[tag] += 1
    return tags

def get_rules_summary(rules):
    do_items = []
    dont_items = []
    for r in rules:
        for section, lines in r.get('sections', {}).items():
            sec_lower = section.lower()
            if sec_lower in ['do', 'knowledge base', 'zasady', 'praktyki']:
                for line in lines:
                    if line.startswith('- '):
                        do_items.append(line[2:].strip().replace('[ ] ', ''))
            elif sec_lower in ['dont', "don't", 'unikaj', 'zakazy']:
                for line in lines:
                    if line.startswith('- '):
                        dont_items.append(line[2:].strip().replace('[ ] ', ''))
    return do_items, dont_items

# Load data — Polish (default)
ALL_RECIPES = load_folder(RECIPES)
ALL_INVENTORY = get_inventory()
ALL_RULES = load_folder(RULES)
ALL_INV_DATA = load_folder(INVENTORY)
ALL_TRANSCRIPTS = load_folder(TRANSCRIPTS)
INV_BY_CAT = get_inventory_by_category()
TAGS_STATS = get_recipe_tags_stats(ALL_RECIPES)
RULES_DO, RULES_DONT = get_rules_summary(ALL_RULES)

# Load English translations if available
RECIPES_EN = RECIPES / "en"
RULES_EN = RULES / "en"
INVENTORY_EN = INVENTORY / "en"

def load_en_data():
    """Load English translated data if en/ folders exist"""
    data = {'recipes': [], 'rules': [], 'inv_data': [], 'inventory': set(), 'inv_by_cat': {}}
    if RECIPES_EN.exists() and any(RECIPES_EN.glob("*.md")):
        data['recipes'] = load_folder(RECIPES_EN)
    if RULES_EN.exists() and any(RULES_EN.glob("*.md")):
        data['rules'] = load_folder(RULES_EN)
    if INVENTORY_EN.exists() and any(INVENTORY_EN.glob("*.md")):
        data['inv_data'] = [parse_md(f) for f in sorted(INVENTORY_EN.glob("*.md")) if not f.name.startswith('_')]
        for inv in data['inv_data']:
            data['inventory'].update(inv['items'])
        for inv in data['inv_data']:
            for section, lines in inv.get('sections', {}).items():
                if section not in data['inv_by_cat']:
                    data['inv_by_cat'][section] = []
                for line in lines:
                    if line.startswith('- '):
                        data['inv_by_cat'][section].append(line[2:].strip().replace('[ ] ', ''))
    return data

EN_DATA = load_en_data()

def get_data(lang='pl'):
    """Return the right dataset based on language"""
    if lang == 'en':
        return {
            'recipes': EN_DATA['recipes'] or ALL_RECIPES,
            'rules': EN_DATA['rules'] or ALL_RULES,
            'inventory': EN_DATA['inventory'] or ALL_INVENTORY,
            'inv_by_cat': EN_DATA['inv_by_cat'] or INV_BY_CAT,
            'tags_stats': get_recipe_tags_stats(EN_DATA['recipes']) if EN_DATA['recipes'] else TAGS_STATS,
            'rules_do': get_rules_summary(EN_DATA['rules'])[0] if EN_DATA['rules'] else RULES_DO,
            'rules_dont': get_rules_summary(EN_DATA['rules'])[1] if EN_DATA['rules'] else RULES_DONT,
        }
    return {
        'recipes': ALL_RECIPES,
        'rules': ALL_RULES,
        'inventory': ALL_INVENTORY,
        'inv_by_cat': INV_BY_CAT,
        'tags_stats': TAGS_STATS,
        'rules_do': RULES_DO,
        'rules_dont': RULES_DONT,
    }

# Initialize semantic search index
SEARCH_INDEX = None
if SEMANTIC_ENABLED:
    try:
        print("[CHEN-KIT] Loading semantic search model...")
        SEARCH_INDEX = SemanticIndex()
        count = SEARCH_INDEX.index_all(ALL_RECIPES, ALL_RULES, ALL_TRANSCRIPTS)
        print(f"[CHEN-KIT] Indexed {count} documents for semantic search")
    except Exception as e:
        print(f"[CHEN-KIT] Semantic search disabled: {e}")
        SEARCH_INDEX = None

def load_shoplist():
    """Load shopping lists or return default"""
    if SHOPLIST_FILE.exists():
        try:
            return json.loads(SHOPLIST_FILE.read_text(encoding='utf-8'))
        except:
            pass
    return {'lists': [{'name': 'Shopping List', 'items': []}]}

def save_shoplist(data):
    """Save shopping lists to file"""
    SHOPLIST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def md_to_html(text):
    """Convert basic markdown to HTML (bold only)"""
    import re
    # Convert **text** to <strong>text</strong>
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    return text

def get_core_rules():
    """Parse core diet rules from 00-glowne-zasady.md"""
    if not CORE_RULES_FILE.exists():
        return {'meals': {}, 'forbidden': [], 'notes': []}

    content = CORE_RULES_FILE.read_text(encoding='utf-8')
    rules = {'meals': {}, 'forbidden': [], 'notes': [], 'drinks': []}

    current_section = None
    for line in content.split('\n'):
        if line.startswith('## '):
            current_section = line[3:].strip().lower()
        elif line.startswith('- [ ]') or line.startswith('- [x]'):
            item = line.replace('- [ ]', '').replace('- [x]', '').strip()
            if current_section == 'zasady posiłków':
                if 'śniadanie' in item.lower() or 'sniadanie' in item.lower():
                    rules['meals']['breakfast'] = item
                elif 'obiad' in item.lower():
                    rules['meals']['lunch'] = item
                elif 'kolacja' in item.lower():
                    rules['meals']['dinner'] = item
            elif current_section == 'zakazy':
                rules['forbidden'].append(item)
            elif current_section == 'napoje i dodatki':
                rules['drinks'].append(item)
            elif current_section == 'notes':
                rules['notes'].append(item)

    return rules

HTML = '''<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CHEN-KIT</title>
<link href="https://fonts.googleapis.com/css2?family=VT323&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'SF Mono', 'Fira Code', monospace;
    background: #0d1117;
    color: #c9d1d9;
    min-height: 100vh;
}
a { color: #58a6ff; text-decoration: none; }
a:hover { text-decoration: underline; }

.header {
    background: #161b22;
    padding: 15px 20px;
    border-bottom: 1px solid #30363d;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.logo { font-size: 14px; color: #8b949e; letter-spacing: 2px; }
.stats-row { display: flex; gap: 25px; }
.stat { text-align: center; }
.stat-value { font-size: 20px; font-weight: bold; color: #58a6ff; }
.stat-label { font-size: 9px; color: #8b949e; text-transform: uppercase; }

.nav {
    display: flex;
    background: #161b22;
    border-bottom: 1px solid #30363d;
    padding: 0 20px;
}
.nav a {
    color: #8b949e;
    padding: 10px 18px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-bottom: 2px solid transparent;
}
.nav a:hover { color: #c9d1d9; text-decoration: none; }
.nav a.active { color: #58a6ff; border-bottom: 2px solid #f85149; }

.search-box {
    padding: 12px 20px;
    background: #161b22;
    border-bottom: 1px solid #30363d;
}
.search-box input {
    width: 100%;
    padding: 10px 15px;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #c9d1d9;
    font-family: inherit;
    font-size: 14px;
}
.search-box input:focus { outline: none; border-color: #58a6ff; }
.search-box input::placeholder { color: #484f58; }

.main-layout {
    display: grid;
    grid-template-columns: 340px 1fr 300px;
    height: calc(100vh - 130px);
}
.sidebar {
    border-right: 1px solid #30363d;
    overflow-y: auto;
    background: #0d1117;
}
.content {
    padding: 20px;
    overflow-y: auto;
    background: #0d1117;
}
.right-panel {
    border-left: 1px solid #30363d;
    overflow-y: auto;
    background: #161b22;
    padding: 15px;
}

/* Mobile responsive */
@media (max-width: 900px) {
    .main-layout { grid-template-columns: 1fr; height: auto; }
    .sidebar { display: none; }
    .right-panel { display: none; }
    .header { flex-direction: column; gap: 10px; text-align: center; }
    .nav { flex-wrap: wrap; justify-content: center; padding: 10px; }
    .nav a { padding: 8px 12px; font-size: 10px; }
    .content { padding: 15px; }
    .stats-row { flex-wrap: wrap; justify-content: center; }
}

/* Retro pager style */
body.retro {
    background: #0a0a0a;
    font-family: 'VT323', 'Courier New', monospace;
}
body.retro::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(rgba(0,255,136,0.03) 50%, transparent 50%);
    background-size: 100% 4px;
    pointer-events: none;
    z-index: 9999;
}
body.retro .header { background: #0a0a0a; border-color: #00ff88; }
body.retro .nav { background: #0a0a0a; border-color: #00ff88; }
body.retro .nav a { color: #8b949e; }
body.retro .nav a.active { color: #00ff88; border-color: #00ff88; text-shadow: 0 0 10px rgba(0,255,136,0.5); }
body.retro .stat-value { color: #00ff88; text-shadow: 0 0 10px rgba(0,255,136,0.3); }
body.retro a { color: #00ff88; }
body.retro .panel { border-color: #00ff88; background: #0a0a0a; }
body.retro .list-item:hover { background: rgba(0,255,136,0.1); }
body.retro .list-item.selected { border-color: #00ff88; background: rgba(0,255,136,0.1); }
body.retro .category { background: #111; color: #00ff88; }
body.retro h2, body.retro h3 { color: #00ff88; }
body.retro .rule-item.do { border-color: #00ff88; }
body.retro .rule-item.dont { border-color: #ff4444; }
body.retro .search-box input { background: #0a0a0a; border-color: #00ff88; color: #00ff88; }
body.retro .btn-save { background: #00ff88; color: #0a0a0a; }

.list-item {
    padding: 12px 15px;
    border-bottom: 1px solid #21262d;
    cursor: pointer;
}
.list-item:hover { background: #161b22; }
.list-item.selected { background: #1f6feb22; border-left: 3px solid #58a6ff; }
.list-item .title { color: #c9d1d9; font-size: 13px; line-height: 1.3; }
.list-item .meta { font-size: 11px; color: #8b949e; margin-top: 4px; }

.category {
    background: #21262d;
    padding: 10px 15px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #8b949e;
    position: sticky;
    top: 0;
}
.inv-item {
    padding: 8px 15px 8px 25px;
    border-bottom: 1px solid #21262d;
    color: #8b949e;
    font-size: 12px;
}

.panel {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 15px;
}
.panel h2 {
    font-size: 18px;
    color: #c9d1d9;
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #30363d;
}
.panel h3 {
    font-size: 12px;
    color: #f85149;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 15px 0 10px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 15px;
    margin-bottom: 20px;
}
.stat-card {
    background: #21262d;
    padding: 15px;
    border-radius: 6px;
    text-align: center;
}
.stat-card .num { font-size: 28px; font-weight: bold; color: #58a6ff; }
.stat-card .label { font-size: 10px; color: #8b949e; text-transform: uppercase; margin-top: 5px; }

.tags-cloud { display: flex; flex-wrap: wrap; gap: 8px; }
.tag {
    background: #21262d;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 11px;
    color: #8b949e;
}
.tag .count { color: #58a6ff; margin-left: 5px; }

.ingredient { padding: 6px 0; font-size: 13px; display: flex; align-items: center; }
.ingredient .check { margin-right: 10px; font-size: 14px; }
.has { color: #3fb950; }
.missing { color: #8b949e; }
.missing .check { color: #f85149; }

.step { padding: 8px 0; color: #8b949e; font-size: 13px; line-height: 1.5; }

.rule-item {
    padding: 8px 0;
    font-size: 11px;
    color: #8b949e;
    border-bottom: 1px solid #21262d;
}
.rule-item.do { border-left: 3px solid #3fb950; padding-left: 10px; }
.rule-item.dont { border-left: 3px solid #f85149; padding-left: 10px; }

.cat-stat {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    font-size: 12px;
    border-bottom: 1px solid #21262d;
}
.cat-stat .name { color: #8b949e; }
.cat-stat .count { color: #58a6ff; }

.rp-section { margin-bottom: 20px; }
.rp-section h4 {
    font-size: 10px;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
    padding-bottom: 5px;
    border-bottom: 1px solid #30363d;
}

.search-info {
    background: #1f6feb22;
    border: 1px solid #1f6feb;
    border-radius: 6px;
    padding: 10px 15px;
    margin-bottom: 15px;
    font-size: 13px;
    color: #58a6ff;
}

.cat-link {
    cursor: pointer;
    transition: color 0.2s;
}
.cat-link:hover {
    color: #58a6ff !important;
}

.suggestions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
}
.sugg {
    background: #21262d;
    padding: 5px 12px;
    border-radius: 15px;
    font-size: 11px;
    color: #8b949e;
    cursor: pointer;
    transition: all 0.2s;
}
.sugg:hover { background: #30363d; color: #c9d1d9; }
.sugg.hot { border: 1px solid #f85149; color: #f85149; }
.sugg.tag { border: 1px solid #58a6ff; color: #58a6ff; }

.edit-btn {
    display: inline-block;
    padding: 6px 14px;
    background: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #8b949e;
    font-size: 12px;
    cursor: pointer;
    text-decoration: none;
    margin-right: 8px;
    transition: all 0.2s;
}
.edit-btn:hover { background: #30363d; color: #c9d1d9; border-color: #58a6ff; }

.edit-form {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 15px;
}
.edit-form textarea {
    width: 100%;
    min-height: 300px;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    color: #c9d1d9;
    font-family: 'SF Mono', monospace;
    font-size: 13px;
    padding: 15px;
    resize: vertical;
}
.edit-form textarea:focus { outline: none; border-color: #58a6ff; }
.edit-form .actions { margin-top: 15px; display: flex; gap: 10px; }
.btn-save {
    background: #238636;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    color: white;
    font-size: 13px;
    cursor: pointer;
}
.btn-save:hover { background: #2ea043; }
.btn-cancel {
    background: transparent;
    border: 1px solid #30363d;
    padding: 8px 20px;
    border-radius: 6px;
    color: #8b949e;
    font-size: 13px;
    cursor: pointer;
    text-decoration: none;
}
.btn-cancel:hover { border-color: #8b949e; color: #c9d1d9; }

.shop-item:hover { background: #161b22; }
.shop-checked { opacity: 0.7; }
</style>
</head>
<body>

<div class="header">
    <div class="logo"><pre style="font-size:10px;line-height:1.1;margin:0;color:#58a6ff">┌─┐┬ ┬┌─┐┌┐┌   ┬┌─┬┌┬┐
│  ├─┤├┤ │││───├┴┐│ │
└─┘┴ ┴└─┘┘└┘   ┴ ┴┴ ┴ </pre><span style="font-size:9px;color:#8b949e">v2.0</span></div>
    <div class="stats-row">
        <div class="stat"><div class="stat-value">{{RECIPES}}</div><div class="stat-label">Recipes</div></div>
        <div class="stat"><div class="stat-value">{{INVENTORY}}</div><div class="stat-label">Inventory</div></div>
        <div class="stat"><div class="stat-value">{{KNOWLEDGE}}</div><div class="stat-label">Knowledge</div></div>
        <div class="stat"><div class="stat-value">{{CANMAKE}}</div><div class="stat-label">Ready</div></div>
        <button onclick="toggleRetro()" id="style-toggle" style="background:#21262d;border:1px solid #30363d;border-radius:4px;color:#8b949e;padding:5px 10px;font-size:10px;cursor:pointer;font-family:inherit">◐ RETRO</button>
        <button onclick="toggleLang()" id="lang-toggle" style="background:#21262d;border:1px solid #30363d;border-radius:4px;color:#f0883e;padding:5px 10px;font-size:10px;cursor:pointer;font-family:inherit;font-weight:bold">PL</button>
    </div>
</div>

<div class="nav">
    <a href="/?view=home&lang={{LANG}}" class="{{NAV_HOME}}">⌂ Home</a>
    <a href="/?lang={{LANG}}" class="{{NAV_RECIPES}}">Recipes</a>
    <a href="/?view=inventory&lang={{LANG}}" class="{{NAV_INVENTORY}}">Inventory</a>
    <a href="/?view=knowledge&lang={{LANG}}" class="{{NAV_KNOWLEDGE}}">Knowledge</a>
    <a href="/?view=shoplist&lang={{LANG}}" class="{{NAV_SHOPLIST}}">🛒 Shop List</a>
    <a href="/constellation" style="color:#f0883e">✦ Constellation</a>
    <a href="/?view=about&lang={{LANG}}" class="{{NAV_ABOUT}}" style="margin-left:auto">About</a>
</div>

<div class="search-box">
    <form action="/" method="get" style="display:flex;gap:10px;align-items:center">
        <input type="hidden" name="view" value="{{VIEW}}">
        <input type="hidden" name="lang" value="{{LANG}}">
        <input type="text" name="q" placeholder="Search recipes, ingredients..." value="{{QUERY}}" autofocus style="flex:1">
        {{SEMANTIC_TOGGLE}}
    </form>
</div>

<div class="main-layout">
    <div class="sidebar">
        {{SIDEBAR}}
    </div>
    <div class="content">
        {{CONTENT}}
    </div>
    <div class="right-panel">
        {{RIGHT_PANEL}}
    </div>
</div>

<script>
// Style toggle
function toggleRetro() {
    document.body.classList.toggle('retro');
    const btn = document.getElementById('style-toggle');
    if (document.body.classList.contains('retro')) {
        btn.textContent = '◉ RETRO';
        btn.style.background = '#00ff88';
        btn.style.color = '#0a0a0a';
        localStorage.setItem('chen-kit-retro', '1');
    } else {
        btn.textContent = '◐ RETRO';
        btn.style.background = '#21262d';
        btn.style.color = '#8b949e';
        localStorage.removeItem('chen-kit-retro');
    }
}
// Restore retro mode from localStorage
if (localStorage.getItem('chen-kit-retro')) {
    document.body.classList.add('retro');
    document.getElementById('style-toggle').textContent = '◉ RETRO';
    document.getElementById('style-toggle').style.background = '#00ff88';
    document.getElementById('style-toggle').style.color = '#0a0a0a';
}

// PL/EN language toggle — server-side translation via lang= param
function toggleLang() {
    const url = new URL(window.location.href);
    const current = url.searchParams.get('lang') || 'pl';
    const next = current === 'en' ? 'pl' : 'en';
    url.searchParams.set('lang', next);
    window.location.href = url.toString();
}
// Update button state from URL
(function() {
    const url = new URL(window.location.href);
    const lang = url.searchParams.get('lang') || 'pl';
    const btn = document.getElementById('lang-toggle');
    if (btn) {
        btn.textContent = lang.toUpperCase();
        btn.style.color = lang === 'en' ? '#3fb950' : '#f0883e';
    }
})();

// Keyboard navigation
(function() {
    const sidebar = document.querySelector('.sidebar');
    const items = Array.from(sidebar.querySelectorAll('a[href]'));
    let currentIdx = items.findIndex(a => a.querySelector('.selected'));
    if (currentIdx < 0) currentIdx = 0;

    function highlight(idx) {
        items.forEach((item, i) => {
            const div = item.querySelector('.list-item');
            if (div) {
                if (i === idx) {
                    div.classList.add('selected');
                    item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                } else {
                    div.classList.remove('selected');
                }
            }
        });
    }

    document.addEventListener('keydown', e => {
        // Ignore if typing in input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        if (e.key === 'ArrowDown' || e.key === 'j') {
            e.preventDefault();
            currentIdx = Math.min(currentIdx + 1, items.length - 1);
            highlight(currentIdx);
        } else if (e.key === 'ArrowUp' || e.key === 'k') {
            e.preventDefault();
            currentIdx = Math.max(currentIdx - 1, 0);
            highlight(currentIdx);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (items[currentIdx]) items[currentIdx].click();
        } else if (e.key === '/') {
            e.preventDefault();
            document.querySelector('.search-box input')?.focus();
        }
    });

    // Click to update currentIdx
    items.forEach((item, i) => {
        item.addEventListener('click', () => { currentIdx = i; });
    });
})();
</script>
</body>
</html>'''

def build_suggestions(query=''):
    """Build search suggestions based on popular tags and ingredients"""
    suggestions = []
    # Top tags
    for tag, count in TAGS_STATS.most_common(5):
        suggestions.append(('tag', tag))
    # High-availability recipes
    scored = sorted([(score_recipe(r, ALL_INVENTORY), r) for r in ALL_RECIPES], reverse=True, key=lambda x: x[0])
    for pct, r in scored[:3]:
        if pct >= 80:
            title = r.get('title', r['name']).replace('Recipe: ', '')[:20]
            suggestions.append(('hot', title))
    return suggestions

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        """Handle edit form submissions and meal plan saves"""
        global ALL_RECIPES, ALL_INVENTORY, ALL_RULES, ALL_INV_DATA, ALL_TRANSCRIPTS, INV_BY_CAT, TAGS_STATS, RULES_DO, RULES_DONT, SEARCH_INDEX, EN_DATA

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Handle clear all inventory
        if parsed.path == '/api/clear_inventory':
            for inv_file in INVENTORY.glob("*.md"):
                content = inv_file.read_text(encoding='utf-8')
                # Keep headers and structure, remove all checklist items
                new_lines = []
                for line in content.split('\n'):
                    if line.startswith('- ['):
                        continue
                    new_lines.append(line)
                inv_file.write_text('\n'.join(new_lines), encoding='utf-8')
            ALL_INVENTORY = get_inventory()
            ALL_INV_DATA = load_folder(INVENTORY)
            INV_BY_CAT = get_inventory_by_category()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())
            return

        # Handle create new recipe
        if parsed.path == '/api/create_recipe':
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            name = body.get('name', '').strip()
            if name:
                slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                file_path = RECIPES / f"{slug}.md"
                if not file_path.exists():
                    template = f"""# Recipe: {name}

tags: [edit-tags]
time: 30min

## Ingredients
- [ ] ingredient 1
- [ ] ingredient 2

## Steps
1. Step one
2. Step two
"""
                    file_path.write_text(template, encoding='utf-8')
                    ALL_RECIPES = load_folder(RECIPES)
                    TAGS_STATS = get_recipe_tags_stats(ALL_RECIPES)
                    if SEMANTIC_ENABLED and SEARCH_INDEX:
                        SEARCH_INDEX = SemanticIndex()
                        SEARCH_INDEX.index_all(ALL_RECIPES, ALL_RULES, ALL_TRANSCRIPTS)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'id': slug if name else ''}).encode())
            return

        # Handle delete recipe
        if parsed.path == '/api/delete_recipe':
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            file_id = body.get('id', '')
            file_path = RECIPES / f"{file_id}.md"
            if file_path.exists():
                file_path.unlink()
                ALL_RECIPES = load_folder(RECIPES)
                TAGS_STATS = get_recipe_tags_stats(ALL_RECIPES)
                if SEMANTIC_ENABLED and SEARCH_INDEX:
                    SEARCH_INDEX = SemanticIndex()
                    SEARCH_INDEX.index_all(ALL_RECIPES, ALL_RULES, ALL_TRANSCRIPTS)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())
            return

        # Handle create new knowledge article
        if parsed.path == '/api/create_knowledge':
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            name = body.get('name', '').strip()
            category = body.get('category', 'general').strip()
            if name:
                slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                file_path = RULES / f"{slug}.md"
                if not file_path.exists():
                    template = f"""# {name}

category: {category}
tags: general
priority: 3

## Do
- [ ] Add your recommendations here

## Don't
- [ ] Add your prohibitions here

## Notes
Additional notes go here.
"""
                    file_path.write_text(template, encoding='utf-8')
                    ALL_RULES = load_folder(RULES)
                    RULES_DO, RULES_DONT = get_rules_summary(ALL_RULES)
                    if SEMANTIC_ENABLED and SEARCH_INDEX:
                        SEARCH_INDEX = SemanticIndex()
                        SEARCH_INDEX.index_all(ALL_RECIPES, ALL_RULES, ALL_TRANSCRIPTS)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'id': slug if name else ''}).encode())
            return

        # Handle delete knowledge article
        if parsed.path == '/api/delete_knowledge':
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            file_id = body.get('id', '')
            file_path = RULES / f"{file_id}.md"
            if file_path.exists():
                file_path.unlink()
                ALL_RULES = load_folder(RULES)
                RULES_DO, RULES_DONT = get_rules_summary(ALL_RULES)
                if SEMANTIC_ENABLED and SEARCH_INDEX:
                    SEARCH_INDEX = SemanticIndex()
                    SEARCH_INDEX.index_all(ALL_RECIPES, ALL_RULES, ALL_TRANSCRIPTS)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True}).encode())
            return

        # Handle shopping list API
        if parsed.path == '/api/shoplist':
            content_length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(content_length).decode('utf-8'))
            action = body.get('action', '')
            shoplist = load_shoplist()
            lists = shoplist.get('lists', [])

            if action == 'create_list':
                name = body.get('name', 'New List').strip()
                lists.append({'name': name, 'items': []})
            elif action == 'rename_list':
                idx = body.get('list_idx', 0)
                if 0 <= idx < len(lists):
                    lists[idx]['name'] = body.get('name', lists[idx]['name']).strip()
            elif action == 'delete_list':
                idx = body.get('list_idx', 0)
                if 0 <= idx < len(lists):
                    lists.pop(idx)
            elif action == 'add_item':
                idx = body.get('list_idx', 0)
                text = body.get('text', '').strip()
                if 0 <= idx < len(lists) and text:
                    lists[idx]['items'].append({'text': text, 'checked': False})
            elif action == 'toggle_item':
                li = body.get('list_idx', 0)
                ii = body.get('item_idx', 0)
                if 0 <= li < len(lists) and 0 <= ii < len(lists[li]['items']):
                    lists[li]['items'][ii]['checked'] = not lists[li]['items'][ii]['checked']
            elif action == 'delete_item':
                li = body.get('list_idx', 0)
                ii = body.get('item_idx', 0)
                if 0 <= li < len(lists) and 0 <= ii < len(lists[li]['items']):
                    lists[li]['items'].pop(ii)

            shoplist['lists'] = lists
            save_shoplist(shoplist)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'shoplist': shoplist}).encode())
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        post_params = parse_qs(post_data)

        # Handle inventory add
        if 'add_inv' in params:
            cat = post_params.get('category', [''])[0]
            item = post_params.get('item', [''])[0].strip()
            if cat and item:
                # Find the inventory file that has this category
                for inv_file in INVENTORY.glob("*.md"):
                    content = inv_file.read_text(encoding='utf-8')
                    if f'## {cat}' in content:
                        # Add item to this category
                        lines = content.split('\n')
                        new_lines = []
                        in_section = False
                        added = False
                        for line in lines:
                            new_lines.append(line)
                            if line.strip() == f'## {cat}':
                                in_section = True
                            elif in_section and not added:
                                if line.startswith('## ') or line == '':
                                    new_lines.insert(-1, f'- [ ] {item}')
                                    added = True
                                    in_section = False
                        if not added:
                            new_lines.append(f'- [ ] {item}')
                        inv_file.write_text('\n'.join(new_lines), encoding='utf-8')
                        break
                # Reload
                ALL_INVENTORY = get_inventory()
                INV_BY_CAT = get_inventory_by_category()
            self.send_response(302)
            self.send_header('Location', f'/?view=inventory&cat={quote(cat)}')
            self.end_headers()
            return

        # Handle inventory delete
        if 'del_inv' in params:
            cat = params.get('cat', [''])[0]
            item = params.get('del_inv', [''])[0]
            if cat and item:
                for inv_file in INVENTORY.glob("*.md"):
                    content = inv_file.read_text(encoding='utf-8')
                    # Remove the item line
                    new_content = content.replace(f'- [ ] {item}\n', '').replace(f'- [x] {item}\n', '')
                    if new_content != content:
                        inv_file.write_text(new_content, encoding='utf-8')
                        break
                ALL_INVENTORY = get_inventory()
                INV_BY_CAT = get_inventory_by_category()
            self.send_response(302)
            self.send_header('Location', f'/?view=inventory&cat={quote(cat)}')
            self.end_headers()
            return

        if 'edit' in params and 'content' in post_params:
            file_id = params['edit'][0]
            new_content = post_params['content'][0]
            file_type = params.get('type', ['recipe'])[0]

            # Determine file path
            if file_type == 'recipe':
                file_path = RECIPES / f"{file_id}.md"
            elif file_type == 'inventory':
                file_path = INVENTORY / f"{file_id}.md"
            else:
                file_path = RULES / f"{file_id}.md"

            # Save file
            if file_path.exists():
                file_path.write_text(new_content, encoding='utf-8')
                # Reload data
                ALL_RECIPES = load_folder(RECIPES)
                ALL_INVENTORY = get_inventory()
                ALL_RULES = load_folder(RULES)
                ALL_INV_DATA = load_folder(INVENTORY)
                ALL_TRANSCRIPTS = load_folder(TRANSCRIPTS)
                INV_BY_CAT = get_inventory_by_category()
                TAGS_STATS = get_recipe_tags_stats(ALL_RECIPES)
                RULES_DO, RULES_DONT = get_rules_summary(ALL_RULES)
                EN_DATA = load_en_data()
                # Reindex for semantic search
                if SEMANTIC_ENABLED and SEARCH_INDEX:
                    SEARCH_INDEX = SemanticIndex()
                    SEARCH_INDEX.index_all(ALL_RECIPES, ALL_RULES, ALL_TRANSCRIPTS)

            # Redirect back
            self.send_response(302)
            self.send_header('Location', f'/?id={file_id}')
            self.end_headers()
            return

        self.send_response(400)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        # Serve constellation view
        if parsed.path == '/constellation':
            self.serve_constellation()
            return

        params = parse_qs(parsed.query)

        view = params.get('view', ['recipes'])[0]
        query = params.get('q', [''])[0]
        selected = params.get('id', [''])[0]
        edit_id = params.get('edit', [''])[0]
        edit_type = params.get('type', ['recipe'])[0]
        semantic_mode = params.get('sem', [''])[0] == '1' and SEARCH_INDEX is not None
        lang = params.get('lang', ['pl'])[0]  # pl or en
        d = get_data(lang)

        sidebar_html = ""
        content_html = ""
        right_panel_html = ""  # Built later with selection context

        nav = {'NAV_HOME': '', 'NAV_RECIPES': '', 'NAV_INVENTORY': '', 'NAV_KNOWLEDGE': '', 'NAV_SHOPLIST': '', 'NAV_ABOUT': ''}

        can_make = sum(1 for r in d['recipes'] if score_recipe(r, d['inventory']) >= 70)

        # Handle edit mode
        if edit_id:
            content_html = self.render_edit_form(edit_id, edit_type)
            # Show sidebar based on type
            if edit_type == 'recipe':
                nav['NAV_RECIPES'] = 'active'
                for r in d['recipes']:
                    title = r.get('title', r['name']).replace('Recipe: ', '')
                    sel = 'selected' if r['name'] == edit_id else ''
                    sidebar_html += f'''<div class="list-item {sel}"><div class="title">{title}</div></div>'''
            elif edit_type == 'inventory':
                nav['NAV_INVENTORY'] = 'active'
            else:
                nav['NAV_RULES'] = 'active'

        elif view == 'home':
            nav['NAV_HOME'] = 'active'
            # Show core rules in sidebar
            for r in d['rules']:
                title = tr_title(r.get('title', r['name']).replace('# ', '').strip(), lang)[:35]
                sel = 'selected' if r['name'] == selected else ''
                sidebar_html += f'''<a href="/?view=home&id={r['name']}&lang={lang}" style="text-decoration:none;color:inherit">
                    <div class="list-item {sel}">
                        <div class="title">{title}</div>
                    </div></a>'''

            if selected:
                rule = next((r for r in d['rules'] if r['name'] == selected), None)
                if rule:
                    content_html = self.render_knowledge_article(rule, lang=lang)
            else:
                content_html = self.render_home(d, lang=lang)

        elif view == 'recipes' or query:
            nav['NAV_RECIPES'] = 'active'
            recipes = d['recipes']
            search_info = ""
            if query:
                if semantic_mode and SEARCH_INDEX:
                    # Semantic search
                    results = SEARCH_INDEX.search(query, top_k=30, doc_type='recipe')
                    matched_names = {r['name'] for r in results}
                    recipes = [r for r in d['recipes'] if r['name'] in matched_names]
                    # Sort by semantic score
                    score_map = {r['name']: r['score'] for r in results}
                    recipes = sorted(recipes, key=lambda r: score_map.get(r['name'], 0), reverse=True)
                    search_info = f" (semantic, {len(recipes)} hits)"
                else:
                    # Keyword search
                    q_lower = query.lower()
                    recipes = [r for r in recipes if q_lower in r['content'].lower()]

            # Build sidebar with search query preserved in links
            for r in recipes:
                title = r.get('title', r['name']).replace('Recipe: ', '')
                tags = r['meta'].get('tags', '')
                time_str = r['meta'].get('time', '')
                meta_str = f"{tags}" + (f" · {time_str}" if time_str else "")
                sel = 'selected' if r['name'] == selected else ''
                # Preserve query in link
                link_query = f"&q={quote(query)}" if query else ""
                sidebar_html += f'''<a href="/?id={r['name']}{link_query}" style="text-decoration:none;color:inherit">
                    <div class="list-item {sel}">
                        <div class="title">{title}</div>
                        <div class="meta">{meta_str}</div>
                    </div></a>'''

            if selected:
                recipe = next((r for r in d['recipes'] if r['name'] == selected), None)
                if recipe:
                    content_html = self.render_recipe(recipe, d=d)
            elif query and recipes:
                # Show first matching recipe when searching
                content_html = f'<div class="search-info">Found {len(recipes)} recipes for "{query}"{search_info}</div>'
                content_html += self.render_recipe(recipes[0], d=d)
            elif query and not recipes:
                content_html = f'<div class="panel"><h2>No results</h2><p>No recipes found for "{query}"</p></div>'
            else:
                content_html = self.render_recipes_overview(d)

        elif view == 'inventory':
            nav['NAV_INVENTORY'] = 'active'
            cat_filter = params.get('cat', [''])[0]

            for section, items in d['inv_by_cat'].items():
                is_active = section == cat_filter
                style = 'background:#1f6feb22;color:#58a6ff' if is_active else ''
                sidebar_html += f'<a href="/?view=inventory&cat={quote(section)}&lang={lang}" style="text-decoration:none"><div class="category" style="{style}">{section} ({len(items)})</div></a>'
                if is_active or not cat_filter:
                    shown = items if is_active else items[:10]
                    for item in shown:
                        sidebar_html += f'<div class="inv-item">{item}</div>'
                    if not is_active and len(items) > 10:
                        sidebar_html += f'<div class="inv-item" style="color:#58a6ff">+{len(items)-10} more...</div>'

            if cat_filter:
                content_html = self.render_category_detail(cat_filter, d['inv_by_cat'].get(cat_filter, []))
            else:
                content_html = self.render_inventory_overview(d)

        elif view == 'shoplist':
            nav['NAV_SHOPLIST'] = 'active'
            shoplist = load_shoplist()
            lists = shoplist.get('lists', [])
            selected_list = int(params.get('list', ['0'])[0])

            for i, lst in enumerate(lists):
                checked = sum(1 for item in lst.get('items', []) if item.get('checked'))
                total = len(lst.get('items', []))
                sel = 'selected' if i == selected_list else ''
                sidebar_html += f'''<a href="/?view=shoplist&list={i}" style="text-decoration:none;color:inherit">
                    <div class="list-item {sel}">
                        <div class="title">{lst["name"]}</div>
                        <div class="meta">{checked}/{total} items</div>
                    </div></a>'''

            content_html = self.render_shoplist(shoplist, selected_list)

        elif view == 'about':
            nav['NAV_ABOUT'] = 'active'
            content_html = self.render_about()

        elif view == 'knowledge' or view == 'rules':
            nav['NAV_KNOWLEDGE'] = 'active'

            # Filter rules by query if provided
            rules_to_show = d['rules']
            kb_search_info = ""
            if query:
                if semantic_mode and SEARCH_INDEX:
                    # Semantic search
                    results = SEARCH_INDEX.search(query, top_k=20, doc_type='rule')
                    matched_names = {r['name'] for r in results}
                    rules_to_show = [r for r in d['rules'] if r['name'] in matched_names]
                    score_map = {r['name']: r['score'] for r in results}
                    rules_to_show = sorted(rules_to_show, key=lambda r: score_map.get(r['name'], 0), reverse=True)
                    kb_search_info = " (semantic)"
                else:
                    q_lower = query.lower()
                    rules_to_show = [r for r in d['rules'] if
                        q_lower in r['content'].lower() or
                        q_lower in r['meta'].get('tags', '').lower() or
                        q_lower in r['meta'].get('category', '').lower()]

            # Group rules by domain for sidebar
            domains = {}
            for r in rules_to_show:
                cat = r['meta'].get('category', 'general')
                domain = cat.split('/')[0] if '/' in cat else cat
                if domain not in domains:
                    domains[domain] = []
                domains[domain].append(r)

            # Show search info if filtering
            if query:
                sidebar_html += f'<div style="padding:10px 15px;background:#1f6feb22;color:#58a6ff;font-size:12px">🔍 "{query}" ({len(rules_to_show)}){kb_search_info}</div>'
                sidebar_html += f'<a href="/?view=knowledge" style="padding:8px 15px;display:block;color:#8b949e;font-size:11px">✕ clear</a>'

            for domain, rules in sorted(domains.items()):
                sidebar_html += f'<div class="category">{domain.upper()}</div>'
                for r in rules:
                    title = r.get('title', r['name']).replace('Diet Rule Template', '').replace('# ', '').strip()
                    if not title:
                        title = r['name']
                    title = tr_title(title, lang)
                    sel = 'selected' if r['name'] == selected else ''
                    sidebar_html += f'''<a href="/?view=knowledge&id={r['name']}&lang={lang}" style="text-decoration:none;color:inherit">
                        <div class="list-item {sel}">
                            <div class="title">{title[:40]}</div>
                        </div></a>'''

            if selected:
                rule = next((r for r in d['rules'] if r['name'] == selected), None)
                if rule:
                    content_html = self.render_knowledge_article(rule, lang=lang)
            elif query and rules_to_show:
                content_html = f'<div class="search-info">Found {len(rules_to_show)} articles for "{query}"</div>'
                content_html += self.render_knowledge_article(rules_to_show[0], lang=lang)
            elif query and not rules_to_show:
                content_html = f'<div class="panel"><h2>No results</h2><p>No articles found for "{query}"</p></div>'
            else:
                content_html = self.render_knowledge_overview(d, lang=lang)

        # Build suggestions HTML
        sugg_html = ''
        if not query:
            for sugg_type, sugg_text in build_suggestions():
                cls = 'hot' if sugg_type == 'hot' else 'tag'
                sugg_html += f'<a href="/?q={quote(sugg_text)}" class="sugg {cls}">{sugg_text}</a>'

        # Build right panel with selection context
        if not right_panel_html:  # Not overridden by view
            selected_type = 'rule' if view in ('knowledge', 'rules') else 'recipe'
            right_panel_html = self.build_right_panel(selected, selected_type, d)

        # Build HTML
        html = HTML.replace('{{RECIPES}}', str(len(d['recipes'])))
        html = html.replace('{{INVENTORY}}', str(len(d['inventory'])))
        html = html.replace('{{KNOWLEDGE}}', str(len(d['rules'])))
        html = html.replace('{{CANMAKE}}', str(can_make))
        html = html.replace('{{SIDEBAR}}', sidebar_html)
        html = html.replace('{{CONTENT}}', content_html)
        html = html.replace('{{RIGHT_PANEL}}', right_panel_html)
        html = html.replace('{{QUERY}}', query)
        html = html.replace('{{VIEW}}', view)
        html = html.replace('{{LANG}}', lang)
        html = html.replace('{{SUGGESTIONS}}', sugg_html)

        # Semantic search toggle
        if SEARCH_INDEX:
            sem_checked = 'checked' if semantic_mode else ''
            toggle_html = f'''<label style="display:flex;align-items:center;gap:5px;color:#8b949e;font-size:11px;white-space:nowrap">
                <input type="checkbox" name="sem" value="1" {sem_checked} style="accent-color:#58a6ff">
                Semantic
            </label>'''
        else:
            toggle_html = ''
        html = html.replace('{{SEMANTIC_TOGGLE}}', toggle_html)

        for k, v in nav.items():
            html = html.replace('{{' + k + '}}', v)

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())

    def build_right_panel(self, selected_name=None, selected_type=None, d=None):
        html = ""

        # Related documents (if semantic search is available and item selected)
        if SEARCH_INDEX and selected_name:
            related = SEARCH_INDEX.get_related(selected_type or 'recipe', selected_name, top_k=5)
            if related:
                html += '<div class="rp-section"><h4>Related</h4>'
                for rel_id in related:
                    parts = rel_id.split(':', 1)
                    if len(parts) == 2:
                        rel_type, rel_name = parts
                        # Find display title
                        if rel_type == 'recipe':
                            doc = next((r for r in (d or get_data())['recipes'] if r['name'] == rel_name), None)
                            view = ''
                        else:
                            doc = next((r for r in (d or get_data())['rules'] if r['name'] == rel_name), None)
                            view = 'view=knowledge&'
                        if doc:
                            title = doc.get('title', rel_name).replace('Recipe: ', '').replace('# ', '')[:35]
                            icon = '📖' if rel_type == 'rule' else '🍽'
                            html += f'<div class="cat-stat"><a href="/?{view}id={rel_name}" style="color:#c9d1d9">{icon} {title}</a></div>'
                html += '</div>'

        # Quick links
        html += '<div class="rp-section"><h4>Quick Access</h4>'
        html += '<div class="cat-stat"><a href="/?view=inventory" style="color:#c9d1d9">Inventory</a><span class="count">→</span></div>'
        html += '<div class="cat-stat"><a href="/?view=rules" style="color:#c9d1d9">Knowledge Base</a><span class="count">→</span></div>'
        html += '<div class="cat-stat"><a href="/?view=shoplist" style="color:#c9d1d9">🛒 Shop List</a><span class="count">→</span></div>'
        html += '<div class="cat-stat"><a href="/constellation" style="color:#a371f7">✦ Constellation</a><span class="count">→</span></div>'
        html += '</div>'

        # Top tags for search
        html += '<div class="rp-section"><h4>Search by Tags</h4>'
        html += '<div class="tags-cloud">'
        tags_stats = (d or get_data())['tags_stats']
        for tag, count in tags_stats.most_common(10):
            html += f'<a href="/?q={quote(tag)}" class="tag">{tag}</a>'
        html += '</div></div>'

        return html

    def serve_constellation(self):
        import json
        # Build data for constellation
        data = {
            'recipes': [],
            'rules': []
        }

        pl_data = get_data('pl')
        for r in pl_data['recipes']:
            title = r.get('title', r['name']).replace('Recipe: ', '')
            tags = r['meta'].get('tags', '').replace('[', '').replace(']', '')
            tag_list = [t.strip() for t in re.split(r'[,\s]+', tags) if t.strip()]
            ingredients = []
            if 'Ingredients' in r.get('sections', {}):
                for line in r['sections']['Ingredients']:
                    ing = line.lstrip('- [ ] ').strip()
                    # Extract key word
                    words = extract_key_words(ing)
                    if words:
                        ingredients.append(words[0].capitalize())
                    elif ing:
                        ingredients.append(ing[:20])

            data['recipes'].append({
                'title': title,
                'tags': tag_list,
                'ingredients': ingredients[:10]  # Limit to 10
            })

        for r in pl_data['rules']:
            title = r.get('title', r['name']).replace('# ', '').strip()
            cat = r['meta'].get('category', 'general')
            tags_str = r['meta'].get('tags', '')
            rule_tags = [t.strip() for t in re.split(r'[,\s]+', tags_str) if t.strip()]
            priority = r['meta'].get('priority', '3')
            data['rules'].append({
                'title': title,
                'category': cat,
                'tags': rule_tags,
                'priority': priority
            })

        # Load and inject data
        html_path = BASE / 'constellation.html'
        html = html_path.read_text(encoding='utf-8')
        html = html.replace('{{DATA}}', json.dumps(data, ensure_ascii=False))

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode())

    def render_home(self, d=None, lang='pl'):
        """Main home page with diet rules and quick stats"""
        if d is None:
            d = get_data(lang)
        core = get_core_rules()

        # ASCII boiling pot animation
        html = '''<div class="panel" style="border:none;background:transparent;text-align:center;padding:10px">
            <div id="pot-canvas" style="
                line-height:1.15;
                letter-spacing:0.12em;
                color:#58a6ff;
                user-select:none;
                font-size:12px;
                text-shadow:0 0 8px rgba(88,166,255,0.4);
                font-family:'SF Mono',monospace;
                white-space:pre;
                display:inline-block;
            "></div>
            <script>
            (function(){
                const canvas = document.getElementById('pot-canvas');
                let width = 45, height = 28, grid = [], time = 0, bubbles = [];

                function initGrid() {
                    grid = [];
                    for (let y = 0; y < height; y++) {
                        let row = [];
                        for (let x = 0; x < width; x++) row.push(' ');
                        grid.push(row);
                    }
                }

                function render() {
                    let html = '';
                    for (let y = 0; y < height; y++) {
                        for (let x = 0; x < width; x++) html += grid[y][x];
                        html += '\\n';
                    }
                    canvas.textContent = html;
                }

                function update() {
                    initGrid();
                    const t = time * 0.1;
                    const potLeft = 8, potRight = 36, potTop = 6, potBottom = 20, waterTop = 10;

                    // Handles
                    grid[potTop + 2][potLeft - 2] = '●';
                    grid[potTop + 2][potLeft - 1] = '═';
                    grid[potTop + 2][potRight + 1] = '═';
                    grid[potTop + 2][potRight + 2] = '●';

                    // Pot body
                    for (let x = potLeft; x <= potRight; x++) {
                        grid[potTop][x] = '─';
                        grid[potBottom][x] = '═';
                    }
                    for (let y = potTop; y <= potBottom; y++) {
                        grid[y][potLeft] = '│';
                        grid[y][potRight] = '│';
                    }
                    grid[potTop][potLeft] = '┌';
                    grid[potTop][potRight] = '┐';
                    grid[potBottom][potLeft] = '╘';
                    grid[potBottom][potRight] = '╛';

                    // Lid wobble
                    const lidWobble = Math.sin(t * 2) * 0.5;
                    const lidY = Math.floor(potTop - 1 + lidWobble);
                    for (let x = potLeft + 2; x <= potRight - 2; x++) {
                        grid[lidY][x] = '▀';
                    }
                    grid[lidY - 1][Math.floor((potLeft + potRight) / 2)] = '○';

                    // Boiling water
                    for (let x = potLeft + 1; x < potRight; x++) {
                        const wave = Math.sin(x * 0.4 + t * 3) * 0.5;
                        const surfaceY = Math.floor(waterTop + wave);
                        grid[surfaceY][x] = '~';
                    }

                    // Fill water
                    for (let y = waterTop + 1; y < potBottom; y++) {
                        for (let x = potLeft + 1; x < potRight; x++) {
                            if (grid[y][x] === ' ') grid[y][x] = '░';
                        }
                    }

                    // Bubbles
                    if (time % 4 === 0) {
                        const chars = ['o', 'O', '°', '○'];
                        bubbles.push({
                            x: potLeft + 3 + Math.random() * (potRight - potLeft - 6),
                            y: potBottom - 2,
                            speed: 0.15 + Math.random() * 0.2,
                            char: chars[Math.floor(Math.random() * chars.length)]
                        });
                    }
                    bubbles = bubbles.filter(b => {
                        b.y -= b.speed;
                        b.x += Math.sin(time * 0.2 + b.x) * 0.1;
                        const bx = Math.floor(b.x), by = Math.floor(b.y);
                        if (by > waterTop && by < potBottom && bx > potLeft && bx < potRight) {
                            grid[by][bx] = b.char;
                            return true;
                        }
                        return by > waterTop - 1;
                    });

                    // Steam
                    const steamChars = ['░', '▒', '·', '∙'];
                    for (let i = 0; i < 8; i++) {
                        const side = i < 4 ? potLeft + 4 : potRight - 4;
                        const phase = i * 1.5;
                        const steamY = lidY - 1 - ((t * 0.3 + phase) % 5);
                        const wobble = Math.sin(t * 0.4 + phase) * 1.2;
                        const steamX = Math.floor(side + wobble);
                        if (steamY >= 0 && steamY < lidY - 1 && steamX > 0 && steamX < width) {
                            const idx = Math.floor((lidY - 1 - steamY) / 5 * (steamChars.length - 1));
                            grid[Math.floor(steamY)][steamX] = steamChars[idx];
                        }
                    }

                    // Stove
                    for (let x = potLeft - 1; x <= potRight + 1; x++) grid[potBottom + 2][x] = '▬';

                    // Flames
                    const flames = ['▲', '△', '^'];
                    for (let i = 0; i < 6; i++) {
                        const fx = potLeft + 3 + i * 4 + Math.sin(t * 3 + i) * 0.3;
                        const flicker = Math.floor(Math.abs(Math.sin(t * 4 + i * 2)) * flames.length);
                        if (fx > potLeft && fx < potRight) {
                            grid[potBottom + 1][Math.floor(fx)] = flames[flicker];
                        }
                    }

                    time++;
                }

                function animate() {
                    update();
                    render();
                    requestAnimationFrame(animate);
                }

                initGrid();
                requestAnimationFrame(animate);
            })();
            </script>
        </div>'''

        html += '<div class="panel" style="border-left:3px solid #58a6ff">'
        html += '<h2>🍽️ Core Diet Rules</h2>'
        html += f'<a href="/?edit=00-glowne-zasady&type=rules" class="edit-btn" style="float:right;margin-top:-35px">✎ Edytuj</a>'

        # Meal rules - prominent display
        html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin:20px 0">'

        meal_colors = {'breakfast': '#f0883e', 'lunch': '#3fb950', 'dinner': '#a371f7'}
        meal_icons = {'breakfast': '🌅', 'lunch': '☀️', 'dinner': '🌙'}
        meal_names = {'breakfast': 'Breakfast', 'lunch': 'Lunch', 'dinner': 'Dinner'}

        for meal_type in ['breakfast', 'lunch', 'dinner']:
            rule = core['meals'].get(meal_type, '—')
            # Extract just the description part after ':'
            if ':' in rule:
                desc = rule.split(':', 1)[1].strip()
            else:
                desc = rule
            color = meal_colors[meal_type]
            icon = meal_icons[meal_type]
            name = meal_names[meal_type]

            html += f'''<div style="background:#21262d;padding:15px;border-radius:8px;border-top:3px solid {color}">
                <div style="font-size:20px;margin-bottom:8px">{icon}</div>
                <div style="color:{color};font-size:12px;text-transform:uppercase;font-weight:bold">{name}</div>
                <div style="color:#c9d1d9;font-size:13px;margin-top:8px;line-height:1.4">{md_to_html(desc)}</div>
            </div>'''

        html += '</div></div>'

        # Forbidden section
        if core['forbidden']:
            html += '<div class="panel" style="border-left:3px solid #f85149">'
            html += '<h2 style="color:#f85149">⛔ Prohibited</h2>'
            for item in core['forbidden']:
                html += f'<div class="rule-item dont">{md_to_html(item)}</div>'
            html += '</div>'

        # Drinks/additions
        if core['drinks']:
            html += '<div class="panel" style="border-left:3px solid #3fb950">'
            html += '<h2 style="color:#3fb950">🍵 Drinks & Supplements</h2>'
            for item in core['drinks']:
                html += f'<div class="rule-item do">{md_to_html(item)}</div>'
            html += '</div>'

        # Quick stats
        ready_100 = sum(1 for r in d['recipes'] if score_recipe(r, d['inventory']) == 100)
        html += '<div class="panel"><h2>📊 Quick Overview</h2>'
        html += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px">'
        html += f'''<div style="background:#21262d;padding:15px;border-radius:6px;text-align:center">
            <div style="color:#58a6ff;font-size:28px;font-weight:bold">{len(d['recipes'])}</div>
            <div style="color:#8b949e;font-size:10px">Recipes</div>
        </div>'''
        html += f'''<div style="background:#21262d;padding:15px;border-radius:6px;text-align:center">
            <div style="color:#3fb950;font-size:28px;font-weight:bold">{ready_100}</div>
            <div style="color:#8b949e;font-size:10px">Ready</div>
        </div>'''
        html += f'''<div style="background:#21262d;padding:15px;border-radius:6px;text-align:center">
            <div style="color:#a371f7;font-size:28px;font-weight:bold">{len(d['rules'])}</div>
            <div style="color:#8b949e;font-size:10px">Knowledge</div>
        </div>'''
        html += f'''<div style="background:#21262d;padding:15px;border-radius:6px;text-align:center">
            <div style="color:#f0883e;font-size:28px;font-weight:bold">{len(d['inventory'])}</div>
            <div style="color:#8b949e;font-size:10px">Inventory</div>
        </div>'''
        html += '</div></div>'

        # Quick KB preview
        html += '<div class="panel"><h2>📚 Knowledge Base</h2>'
        html += '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px">'
        for r in d['rules'][:6]:
            title = r.get('title', r['name']).replace('# ', '').strip()[:40]
            cat = r['meta'].get('category', '')
            tags = r['meta'].get('tags', '')[:40]
            html += f'''<a href="/?view=knowledge&id={r['name']}" style="text-decoration:none">
                <div style="background:#21262d;padding:12px;border-radius:6px;border-left:2px solid #58a6ff">
                    <div style="color:#c9d1d9;font-size:12px;font-weight:bold">{title}</div>
                    <div style="color:#8b949e;font-size:10px;margin-top:4px">{cat}</div>
                </div></a>'''
        html += '</div></div>'

        return html

    def render_recipes_overview(self, d=None):
        if d is None:
            d = get_data()
        # Calculate stats
        ready_100 = sum(1 for r in d['recipes'] if score_recipe(r, d['inventory']) == 100)
        ready_70 = sum(1 for r in d['recipes'] if score_recipe(r, d['inventory']) >= 70)
        avg_ingredients = sum(len(r['items']) for r in d['recipes']) // max(len(d['recipes']), 1)

        # Count by category
        cat_counts = {}
        for tag, count in d['tags_stats'].most_common(20):
            cat_counts[tag] = count

        html = '<div class="panel"><div style="display:flex;justify-content:space-between;align-items:center"><h2>┌─ Recipes Overview ─┐</h2>'
        html += '<button onclick="createNewRecipe()" style="background:#238636;border:none;border-radius:6px;color:white;padding:8px 16px;cursor:pointer;font-size:12px;font-family:inherit">+ New Recipe</button></div>'

        # Main stats grid
        html += '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-bottom:20px">'
        html += f'''<div style="background:#21262d;padding:15px;border-radius:6px;text-align:center">
            <div style="color:#58a6ff;font-size:28px;font-weight:bold">{len(d['recipes'])}</div>
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase">Total</div>
        </div>'''
        html += f'''<div style="background:#21262d;padding:15px;border-radius:6px;text-align:center">
            <div style="color:#3fb950;font-size:28px;font-weight:bold">{ready_100}</div>
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase">100% Ready</div>
        </div>'''
        html += f'''<div style="background:#21262d;padding:15px;border-radius:6px;text-align:center">
            <div style="color:#f0883e;font-size:28px;font-weight:bold">{ready_70}</div>
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase">70%+ Ready</div>
        </div>'''
        html += f'''<div style="background:#21262d;padding:15px;border-radius:6px;text-align:center">
            <div style="color:#a371f7;font-size:28px;font-weight:bold">~{avg_ingredients}</div>
            <div style="color:#8b949e;font-size:10px;text-transform:uppercase">Avg Ingr.</div>
        </div>'''
        html += '</div></div>'

        # Tags visualization
        html += '<div class="panel"><h2>Tags</h2>'
        html += '<div style="display:flex;flex-wrap:wrap;gap:10px">'
        max_count = max(cat_counts.values()) if cat_counts else 1
        for tag, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
            # Size based on count
            size = 11 + int((count / max_count) * 8)
            html += f'<a href="/?q={tag}" style="text-decoration:none;font-size:{size}px;color:#8b949e;padding:5px 10px;background:#21262d;border-radius:15px">{tag} <span style="color:#58a6ff">{count}</span></a>'
        html += '</div></div>'

        # Top ingredients used
        ingredient_counts = {}
        for r in d['recipes']:
            for item in r['items']:
                words = extract_key_words(item)
                if words:
                    key = words[0].lower()
                    ingredient_counts[key] = ingredient_counts.get(key, 0) + 1

        html += '<div class="panel"><h2>Most Used Ingredients</h2>'
        html += '<div style="column-count:2;column-gap:20px">'
        for ing, count in sorted(ingredient_counts.items(), key=lambda x: -x[1])[:20]:
            in_inv = '✓' if any(ing in i.lower() for i in d['inventory']) else '✗'
            color = '#3fb950' if in_inv == '✓' else '#f85149'
            html += f'<div style="padding:4px 0;font-size:12px"><span style="color:{color}">{in_inv}</span> <a href="/?q={ing}" style="color:#c9d1d9">{ing.capitalize()}</a> <span style="color:#8b949e">({count})</span></div>'
        html += '</div></div>'

        # Recent/random recipes
        html += '<div class="panel"><h2>Quick Access</h2>'
        import random
        sample = random.sample(d['recipes'], min(5, len(d['recipes'])))
        for r in sample:
            title = r.get('title', r['name']).replace('Recipe: ', '')
            pct = score_recipe(r, d['inventory'])
            indicator = '✓' if pct >= 70 else '◐' if pct >= 50 else '✗'
            color = '#3fb950' if pct >= 70 else '#f0883e' if pct >= 50 else '#8b949e'
            html += f'<div style="padding:8px 0;border-bottom:1px solid #21262d"><span style="color:{color}">{indicator}</span> <a href="/?id={r["name"]}" style="color:#c9d1d9">{title}</a></div>'
        html += '</div>'

        html += '''<script>
async function createNewRecipe() {
    const name = prompt('Recipe name:');
    if (!name) return;
    const res = await fetch('/api/create_recipe', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name})
    });
    const data = await res.json();
    if (data.id) window.location.href = '/?edit=' + data.id + '&type=recipe';
}
</script>'''

        return html

    def render_inventory_overview(self, d=None):
        if d is None:
            d = get_data()
        html = '<div class="panel"><div style="display:flex;justify-content:space-between;align-items:center"><h2>Inventory Overview</h2>'
        html += '<button onclick="clearAllInventory()" style="background:#f85149;border:none;border-radius:6px;color:white;padding:8px 16px;cursor:pointer;font-size:12px;font-family:inherit">🗑 Clear All</button></div>'
        html += '<div class="stats-grid">'
        html += f'<div class="stat-card"><div class="num">{len(d["inventory"])}</div><div class="label">Total Items</div></div>'
        html += f'<div class="stat-card"><div class="num">{len(d["inv_by_cat"])}</div><div class="label">Categories</div></div>'
        spices = len(d['inv_by_cat'].get('Przyprawy', d['inv_by_cat'].get('Spices', [])))
        html += f'<div class="stat-card"><div class="num">{spices}</div><div class="label">Spices</div></div>'
        html += '</div>'

        html += '<h3>Click a category on the left</h3>'
        for cat, items in sorted(d['inv_by_cat'].items(), key=lambda x: -len(x[1])):
            html += f'<a href="/?view=inventory&cat={quote(cat)}" style="text-decoration:none"><div class="cat-stat cat-link"><span class="name">{cat}</span><span class="count">{len(items)}</span></div></a>'
        html += '</div>'

        html += '''<script>
async function clearAllInventory() {
    if (!confirm('Delete ALL inventory items? This gives you a fresh start. Categories will remain but all items will be removed.')) return;
    await fetch('/api/clear_inventory', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}'});
    location.reload();
}
</script>'''
        return html

    def render_category_detail(self, cat, items):
        html = f'<div class="panel"><h2>{cat}</h2>'
        html += f'<p style="color:#8b949e;margin-bottom:15px">{len(items)} items</p>'

        # Add form
        html += f'''<form method="POST" action="/?add_inv=1" style="margin-bottom:20px;display:flex;gap:10px">
            <input type="hidden" name="category" value="{cat}">
            <input type="text" name="item" placeholder="Add item..." style="flex:1;padding:8px 12px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-family:inherit">
            <button type="submit" class="btn-save" style="padding:8px 15px">+</button>
        </form>'''

        for item in sorted(items):
            html += f'''<div class="ingredient" style="display:flex;justify-content:space-between;align-items:center;padding:8px 0">
                <span>{item}</span>
                <a href="/?view=inventory&cat={quote(cat)}&del_inv={quote(item)}" style="color:#f85149;font-size:12px" onclick="return confirm('Delete {item}?')">✕</a>
            </div>'''
        html += '</div>'
        return html

    def render_knowledge_overview(self, d=None, lang='pl'):
        if d is None:
            d = get_data(lang)
        # Group by FULL subcategory path (e.g. diet/core, health/tcm)
        subcategories = {}
        all_tags = Counter()
        for r in d['rules']:
            cat = r['meta'].get('category', 'general')
            if cat not in subcategories:
                subcategories[cat] = {'rules': [], 'do': [], 'dont': []}
            subcategories[cat]['rules'].append(r)

            # Collect tags
            tags_str = r['meta'].get('tags', '')
            for tag in re.split(r'[,\s]+', tags_str):
                tag = tag.strip().lower()
                if tag and len(tag) > 2:
                    all_tags[tag] += 1

            # Collect do/dont from this rule
            for section, lines in r.get('sections', {}).items():
                sec_lower = section.lower()
                for line in lines:
                    if line.startswith('- '):
                        item = line[2:].strip().replace('[ ] ', '')
                        if sec_lower in ['zakazy', 'dont', "don't", 'unikaj']:
                            subcategories[cat]['dont'].append(item)
                        elif sec_lower in ['zasady', 'do', 'praktyki', 'knowledge base']:
                            subcategories[cat]['do'].append(item)

        html = '<div class="panel"><div style="display:flex;justify-content:space-between;align-items:center"><h2>┌─ Knowledge Base ─┐</h2>'
        html += '<button onclick="createNewArticle()" style="background:#238636;border:none;border-radius:6px;color:white;padding:8px 16px;cursor:pointer;font-size:12px;font-family:inherit">+ New Article</button></div>'
        html += f'<p style="color:#8b949e;margin-bottom:20px">{len(d["rules"])} articles · {len(d["rules_dont"])} prohibitions · {len(d["rules_do"])} recommendations</p>'

        # Tags cloud for search
        html += '<div style="margin-bottom:20px"><h3 style="color:#f0883e;font-size:11px;margin-bottom:10px">SEARCH BY TAGS</h3>'
        html += '<div style="display:flex;flex-wrap:wrap;gap:6px">'
        for tag, count in all_tags.most_common(20):
            html += f'<a href="/?view=knowledge&q={tag}" style="text-decoration:none;background:#21262d;padding:4px 10px;border-radius:12px;font-size:11px;color:#8b949e">{tag} <span style="color:#f0883e">{count}</span></a>'
        html += '</div></div></div>'

        # Domain color map — orange shades + white-gray
        domain_colors = {
            'diet': '#f0883e', 'health': '#e8a04e', 'wellness': '#d4956a',
            'general': '#8b949e', 'ayurveda': '#cc7832', 'tcm': '#b8682e'
        }
        domain_icons = {
            'diet': '🥗', 'health': '💚', 'wellness': '✨',
            'general': '📋', 'ayurveda': '🕉️', 'tcm': '☯️'
        }

        # Subcategory cards — full path (e.g. diet/core, health/tcm)
        html += '<div class="panel"><h2>📂 Categories</h2>'
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-bottom:20px">'
        for cat_path, data in sorted(subcategories.items()):
            count = len(data['rules'])
            domain = cat_path.split('/')[0] if '/' in cat_path else cat_path
            subcat = cat_path.split('/')[1].upper() if '/' in cat_path else cat_path.upper()
            color = domain_colors.get(domain, '#58a6ff')
            icon = domain_icons.get(domain, '📄')
            html += f'''<a href="/?view=knowledge&q={quote(cat_path)}" style="text-decoration:none">
                <div style="background:#21262d;padding:14px;border-radius:6px;border-left:3px solid {color};cursor:pointer;transition:background 0.2s" onmouseover="this.style.background='#30363d'" onmouseout="this.style.background='#21262d'">
                    <div style="color:#8b949e;font-size:9px;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">{icon} {domain}</div>
                    <div style="color:{color};font-size:14px;font-weight:bold;letter-spacing:0.5px">{subcat}</div>
                    <div style="color:#c9d1d9;font-size:11px;margin-top:4px">{count} article{"s" if count != 1 else ""}</div>
                </div></a>'''
        html += '</div></div>'

        # All articles list with priority sorting
        html += '<div class="panel"><h2>📚 All Articles</h2>'
        sorted_rules = sorted(d['rules'], key=lambda r: (int(r['meta'].get('priority', 5)), r.get('title', r['name'])))
        for r in sorted_rules:
            title = tr_title(r.get('title', r['name']).replace('# ', '').strip(), lang)
            cat = r['meta'].get('category', '')
            tags_str = r['meta'].get('tags', '')
            priority = r['meta'].get('priority', '')
            domain = cat.split('/')[0] if '/' in cat else cat
            color = domain_colors.get(domain, '#58a6ff')

            priority_badge = ''
            if priority == '1':
                priority_badge = '<span style="background:#f85149;color:white;padding:2px 6px;border-radius:4px;font-size:9px;margin-right:8px">CRITICAL</span>'

            # Show tags inline
            tags_html = ''
            if tags_str:
                for tag in re.split(r'[,\s]+', tags_str.strip()):
                    tag = tag.strip()
                    if tag:
                        tags_html += f'<span style="background:#21262d;padding:1px 6px;border-radius:8px;font-size:9px;color:#8b949e;margin-left:4px">{tag}</span>'

            html += f'''<a href="/?view=knowledge&id={r['name']}" style="text-decoration:none">
                <div style="padding:12px;border-bottom:1px solid #21262d;display:flex;align-items:center;gap:10px">
                    <div style="width:4px;height:30px;background:{color};border-radius:2px"></div>
                    <div style="flex:1">
                        <div style="color:#c9d1d9;font-size:13px">{priority_badge}{title}{tags_html}</div>
                        <div style="color:#8b949e;font-size:10px;margin-top:3px">{cat}</div>
                    </div>
                </div></a>'''
        html += '</div>'

        # Quick reference - Prohibitions
        if d['rules_dont']:
            html += '<div class="panel" style="border-left:3px solid #f85149"><h2 style="color:#f85149">⛔ Prohibitions</h2>'
            for item in d['rules_dont'][:15]:
                html += f'<div class="rule-item dont">{md_to_html(item)}</div>'
            if len(d['rules_dont']) > 15:
                html += f'<div style="color:#8b949e;font-size:11px;margin-top:10px">+{len(d["rules_dont"])-15} more</div>'
            html += '</div>'

        # Quick reference - Recommendations
        if d['rules_do']:
            html += '<div class="panel" style="border-left:3px solid #3fb950"><h2 style="color:#3fb950">✓ Recommendations</h2>'
            for item in d['rules_do'][:15]:
                html += f'<div class="rule-item do">{md_to_html(item)}</div>'
            if len(d['rules_do']) > 15:
                html += f'<div style="color:#8b949e;font-size:11px;margin-top:10px">+{len(d["rules_do"])-15} more</div>'
            html += '</div>'

        html += '''<script>
async function createNewArticle() {
    const name = prompt('Article title:');
    if (!name) return;
    const category = prompt('Category path (e.g. diet/core, health/tcm, wellness/mental):', 'general');
    if (category === null) return;
    const res = await fetch('/api/create_knowledge', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: name, category: category || 'general'})
    });
    const data = await res.json();
    if (data.id) window.location.href = '/?edit=' + data.id + '&type=rules';
}
</script>'''

        return html

    def render_knowledge_article(self, r, lang='pl'):
        title = r.get('title', r['name']).replace('Diet Rule Template', '').replace('# ', '').strip()
        if not title:
            title = r['name']
        title = tr_title(title, lang)
        cat = r['meta'].get('category', '')

        html = f'<div class="panel"><h2>{title}</h2>'
        if cat:
            html += f'<p style="color:#58a6ff;font-size:11px;margin-bottom:15px">📁 {cat}</p>'

        for section, lines in r.get('sections', {}).items():
            sec_lower = section.lower()
            is_do = sec_lower in ['do', 'knowledge base', 'zasady', 'praktyki']
            is_dont = sec_lower in ['dont', "don't", 'unikaj', 'zakazy']
            display_section = tr_section(section, lang)

            if is_dont:
                html += f'<h3 style="color:#f85149">⛔ {display_section}</h3>'
            elif is_do:
                html += f'<h3 style="color:#3fb950">✓ {display_section}</h3>'
            else:
                html += f'<h3>{display_section}</h3>'

            for line in lines:
                if line.startswith('- '):
                    item = line[2:].strip().replace('[ ] ', '')
                    item = md_to_html(item)
                    # Make ingredients/keywords clickable
                    words = extract_key_words(item)
                    if words and len(words[0]) > 4:
                        item_html = f'<a href="/?q={words[0]}" style="color:inherit">{item}</a>'
                    else:
                        item_html = item
                    cls = 'do' if is_do else 'dont' if is_dont else ''
                    html += f'<div class="rule-item {cls}">{item_html}</div>'
                else:
                    html += f'<div class="step">{md_to_html(line)}</div>'

        # Notes section if exists
        if 'Notes' in r.get('sections', {}) or 'notes' in r['content'].lower():
            notes = r.get('sections', {}).get('Notes', [])
            if notes:
                html += '<h3 style="color:#8b949e">📝 Notes</h3>'
                for note in notes:
                    html += f'<div class="step" style="font-style:italic">{md_to_html(note)}</div>'

        html += f'''<div style="margin-top:20px;padding-top:15px;border-top:1px solid #30363d;display:flex;gap:8px;align-items:center">
            <a href="/?edit={r['name']}&type=rules" class="edit-btn">✎ Edit</a>
            <button onclick="deleteKnowledge('{r['name']}')" style="background:none;border:1px solid #f85149;border-radius:6px;color:#f85149;padding:6px 14px;cursor:pointer;font-size:12px;font-family:inherit">🗑 Delete</button>
        </div>'''
        html += '''<script>
async function deleteKnowledge(id) {
    if (!confirm('Delete this article permanently?')) return;
    await fetch('/api/delete_knowledge', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: id})
    });
    window.location.href = '/?view=knowledge';
}
</script>'''
        html += '</div>'
        return html

    def render_recipe(self, r, show_availability=False, d=None):
        title = r.get('title', r['name']).replace('Recipe: ', '')
        html = f'<div class="panel"><h2>{title}</h2>'

        meta = []
        if 'tags' in r['meta']:
            meta.append(f"Tags: {r['meta']['tags']}")
        if 'time' in r['meta']:
            meta.append(f"Time: {r['meta']['time']}")
        if meta:
            html += f'<p style="color:#8b949e;margin-bottom:15px">{" | ".join(meta)}</p>'

        if 'Ingredients' in r.get('sections', {}):
            html += "<h3>Ingredients</h3>"
            for line in r['sections']['Ingredients']:
                item = line.lstrip('- [ ] ')
                words = extract_key_words(item)
                search_word = words[0] if words else ''

                if show_availability:
                    inv = (d or get_data())['inventory']
                    has = ingredient_match(item, inv)
                    icon = '<span class="check">✓</span>' if has else '<span class="check">✗</span>'
                    cls = 'has' if has else 'missing'
                    link = f'<a href="/?q={search_word}" style="color:inherit">{item}</a>' if search_word else item
                    html += f'<div class="ingredient {cls}">{icon}{link}</div>'
                else:
                    link = f'<a href="/?q={search_word}" style="color:#c9d1d9">{item}</a>' if search_word else item
                    html += f'<div class="ingredient">{link}</div>'

        if 'Steps' in r.get('sections', {}):
            html += "<h3>Steps</h3>"
            for i, line in enumerate(r['sections']['Steps'], 1):
                html += f'<div class="step">{line}</div>'

        # Edit & Delete buttons
        html += f'''<div style="margin-top:20px;padding-top:15px;border-top:1px solid #30363d;display:flex;gap:8px;align-items:center">
            <a href="/?edit={r['name']}&type=recipe" class="edit-btn">✎ Edit Recipe</a>
            <button onclick="deleteRecipe('{r['name']}')" style="background:none;border:1px solid #f85149;border-radius:6px;color:#f85149;padding:6px 14px;cursor:pointer;font-size:12px;font-family:inherit">🗑 Delete</button>
        </div>'''
        html += '''<script>
async function deleteRecipe(id) {
    if (!confirm('Delete this recipe permanently?')) return;
    await fetch('/api/delete_recipe', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({id: id})
    });
    window.location.href = '/';
}
</script>'''

        html += '</div>'
        return html

    def render_shoplist(self, shoplist, selected_idx=0):
        """Render shopping list management view"""
        lists = shoplist.get('lists', [])
        if selected_idx >= len(lists):
            selected_idx = 0

        current_list = lists[selected_idx] if lists else None

        html = '<div style="max-width:900px;margin:0 auto">'
        html += '<div class="panel">'

        # Header with list selector
        html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
        html += '<h2>🛒 Shop List</h2>'
        html += '<div style="display:flex;gap:8px;align-items:center">'
        html += '<select id="list-select" onchange="switchList(this.value)" style="background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;padding:8px 12px;font-family:inherit;font-size:13px">'
        for i, lst in enumerate(lists):
            checked = sum(1 for item in lst.get('items', []) if item.get('checked'))
            total = len(lst.get('items', []))
            sel = 'selected' if i == selected_idx else ''
            html += f'<option value="{i}" {sel}>{lst["name"]} ({checked}/{total})</option>'
        html += '</select>'
        html += '<button onclick="createList()" style="background:#238636;border:none;border-radius:6px;color:white;padding:8px 14px;cursor:pointer;font-size:12px;font-family:inherit">+ New List</button>'
        html += '</div></div>'

        if current_list:
            items = current_list.get('items', [])
            checked_count = sum(1 for item in items if item.get('checked'))
            total_count = len(items)

            # List header with rename/delete
            html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;padding-bottom:15px;border-bottom:1px solid #30363d">'
            html += f'<div style="display:flex;align-items:center;gap:12px">'
            html += f'<span style="font-size:18px;font-weight:bold;color:#c9d1d9" id="list-name">{current_list["name"]}</span>'
            html += '<button onclick="renameList()" style="background:none;border:none;color:#8b949e;cursor:pointer;font-size:12px">✎</button>'
            if len(lists) > 1:
                html += '<button onclick="deleteList()" style="background:none;border:none;color:#f85149;cursor:pointer;font-size:12px">✕ Delete</button>'
            html += '</div>'
            html += f'<div style="color:#8b949e;font-size:12px"><span style="color:#3fb950">{checked_count}</span> / {total_count}</div>'
            html += '</div>'

            # Add item input
            html += '''<div style="display:flex;gap:8px;margin-bottom:20px">
                <input type="text" id="new-item" placeholder="Add item..."
                    style="flex:1;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-family:inherit;font-size:13px"
                    onkeypress="if(event.key==='Enter')addItem()">
                <button onclick="addItem()" style="background:#238636;border:none;border-radius:6px;color:white;padding:10px 18px;cursor:pointer;font-size:13px;font-family:inherit">+</button>
            </div>'''

            # Items list
            html += '<div id="items-list">'
            for idx, item in enumerate(items):
                is_checked = item.get('checked', False)
                text = item.get('text', '')
                check_bg = '#3fb950' if is_checked else 'transparent'
                check_border = '#3fb950' if is_checked else '#30363d'
                check_mark = '<span style="color:white;font-size:13px">✓</span>' if is_checked else ''
                text_color = '#8b949e' if is_checked else '#c9d1d9'
                text_deco = 'text-decoration:line-through;' if is_checked else ''
                html += f'''<div class="shop-item" style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid #21262d">
                    <div onclick="toggleItem({idx})" style="width:22px;height:22px;border:2px solid {check_border};border-radius:4px;cursor:pointer;display:flex;align-items:center;justify-content:center;background:{check_bg};flex-shrink:0">{check_mark}</div>
                    <span style="flex:1;color:{text_color};font-size:14px;{text_deco}">{text}</span>
                    <button onclick="deleteItem({idx})" style="background:none;border:none;color:#f85149;cursor:pointer;font-size:14px;padding:4px 8px;opacity:0.5" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.5">✕</button>
                </div>'''
            html += '</div>'

            if not items:
                html += '<div style="text-align:center;padding:40px;color:#8b949e">Empty list — add items above</div>'

            # Progress bar
            if total_count > 0:
                pct = int(checked_count / total_count * 100)
                html += f'''<div style="margin-top:20px;padding-top:15px;border-top:1px solid #30363d">
                    <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                        <span style="color:#8b949e;font-size:11px">Progress</span>
                        <span style="color:#3fb950;font-size:11px">{pct}%</span>
                    </div>
                    <div style="background:#21262d;border-radius:4px;height:6px;overflow:hidden">
                        <div style="background:#3fb950;height:100%;width:{pct}%;border-radius:4px;transition:width 0.3s"></div>
                    </div>
                </div>'''
        else:
            html += '<div style="text-align:center;padding:40px;color:#8b949e">No lists — create your first one</div>'

        html += '</div></div>'

        # JavaScript for CRUD operations
        html += '<script>\n'
        html += 'const currentListIdx = ' + str(selected_idx) + ';\n'
        html += '''
function switchList(idx) {
    window.location.href = '/?view=shoplist&list=' + idx;
}

async function shoplistAction(body) {
    const res = await fetch('/api/shoplist', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
    });
    return await res.json();
}

async function createList() {
    const name = prompt('New list name:');
    if (!name) return;
    await shoplistAction({action: 'create_list', name: name});
    location.reload();
}

async function renameList() {
    const name = prompt('New name:', document.getElementById('list-name').textContent);
    if (!name) return;
    await shoplistAction({action: 'rename_list', list_idx: currentListIdx, name: name});
    location.reload();
}

async function deleteList() {
    if (!confirm('Delete this list?')) return;
    await shoplistAction({action: 'delete_list', list_idx: currentListIdx});
    window.location.href = '/?view=shoplist';
}

async function addItem() {
    const input = document.getElementById('new-item');
    const text = input.value.trim();
    if (!text) return;
    await shoplistAction({action: 'add_item', list_idx: currentListIdx, text: text});
    location.reload();
}

async function toggleItem(itemIdx) {
    await shoplistAction({action: 'toggle_item', list_idx: currentListIdx, item_idx: itemIdx});
    location.reload();
}

async function deleteItem(itemIdx) {
    await shoplistAction({action: 'delete_item', list_idx: currentListIdx, item_idx: itemIdx});
    location.reload();
}
'''
        html += '</script>'

        return html

    def render_about(self):
        """Render About page with credits and project info"""
        html = '''<div style="max-width:800px;margin:0 auto">
        <div class="panel" style="text-align:center;border:none;background:transparent;padding:30px 20px 10px">
            <pre style="font-size:14px;line-height:1.2;color:#58a6ff;text-shadow:0 0 12px rgba(88,166,255,0.3);display:inline-block">
┌─┐┬ ┬┌─┐┌┐┌   ┬┌─┬┌┬┐
│  ├─┤├┤ │││───├┴┐│ │
└─┘┴ ┴└─┘┘└┘   ┴ ┴┴ ┴</pre>
            <div style="color:#8b949e;font-size:12px;margin-top:8px;letter-spacing:2px">v2.0 — PERSONAL KITCHEN KNOWLEDGE SYSTEM</div>
            <div style="color:#f0883e;font-size:14px;margin-top:12px;font-style:italic">"Your recipes, your rules, your kitchen — all in one place"</div>
        </div>

        <div class="panel">
            <h2 style="color:#58a6ff">What is CHEN-KIT?</h2>
            <div style="color:#c9d1d9;font-size:13px;line-height:1.8">
                <p>CHEN-KIT is a personal kitchen knowledge system that runs entirely on your machine. No cloud, no accounts, no tracking — just your data in markdown files served through a local dashboard.</p>
            </div>
            <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:20px">
                <div style="background:#21262d;padding:14px;border-radius:6px;border-left:3px solid #3fb950">
                    <div style="color:#3fb950;font-size:11px;text-transform:uppercase;font-weight:bold;margin-bottom:6px">Recipes</div>
                    <div style="color:#8b949e;font-size:12px">Store, search, and track ingredient availability for your recipes</div>
                </div>
                <div style="background:#21262d;padding:14px;border-radius:6px;border-left:3px solid #58a6ff">
                    <div style="color:#58a6ff;font-size:11px;text-transform:uppercase;font-weight:bold;margin-bottom:6px">Knowledge Base</div>
                    <div style="color:#8b949e;font-size:12px">Diet rules, TCM, Ayurveda, nutritional guidelines — all searchable</div>
                </div>
                <div style="background:#21262d;padding:14px;border-radius:6px;border-left:3px solid #f0883e">
                    <div style="color:#f0883e;font-size:11px;text-transform:uppercase;font-weight:bold;margin-bottom:6px">Inventory</div>
                    <div style="color:#8b949e;font-size:12px">Track what you have, auto-match against recipe ingredients</div>
                </div>
                <div style="background:#21262d;padding:14px;border-radius:6px;border-left:3px solid #a371f7">
                    <div style="color:#a371f7;font-size:11px;text-transform:uppercase;font-weight:bold;margin-bottom:6px">Constellation</div>
                    <div style="color:#8b949e;font-size:12px">3D visualization of recipe-ingredient-knowledge connections</div>
                </div>
            </div>
        </div>

        <div class="panel">
            <h2 style="color:#58a6ff">Built With</h2>
            <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:10px">
                <span style="background:#21262d;padding:6px 14px;border-radius:20px;font-size:12px;color:#3fb950;border:1px solid #30363d">Python stdlib</span>
                <span style="background:#21262d;padding:6px 14px;border-radius:20px;font-size:12px;color:#f0883e;border:1px solid #30363d">Zero dependencies</span>
                <span style="background:#21262d;padding:6px 14px;border-radius:20px;font-size:12px;color:#a371f7;border:1px solid #30363d">Three.js constellation</span>
                <span style="background:#21262d;padding:6px 14px;border-radius:20px;font-size:12px;color:#58a6ff;border:1px solid #30363d">Markdown files</span>
                <span style="background:#21262d;padding:6px 14px;border-radius:20px;font-size:12px;color:#8b949e;border:1px solid #30363d">PL/EN bilingual</span>
            </div>
        </div>

        <div class="panel" style="border-left:3px solid #f0883e">
            <h2 style="color:#f0883e">Authors</h2>
            <div style="display:flex;align-items:center;gap:20px;margin-top:15px">
                <div style="width:60px;height:60px;background:#21262d;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:28px;border:2px solid #f0883e">E</div>
                <div>
                    <div style="color:#c9d1d9;font-size:16px;font-weight:bold">Exhuman</div>
                    <div style="margin-top:8px;display:flex;gap:12px">
                        <a href="https://instagram.com/exhto" target="_blank" style="color:#f0883e;font-size:13px">IG @exhto</a>
                        <a href="https://x.com/3xhuman" target="_blank" style="color:#58a6ff;font-size:13px">X @3xhuman</a>
                    </div>
                </div>
            </div>
            <div style="margin-top:20px;padding-top:15px;border-top:1px solid #30363d;color:#8b949e;font-size:12px">
                Built with <a href="https://claude.ai" target="_blank">Claude</a> by Anthropic
            </div>
        </div>

        <div class="panel" style="text-align:center">
            <div style="color:#8b949e;font-size:12px">
                Open source · <a href="https://github.com/exhuman777/chen-kit" target="_blank">GitHub</a> · MIT License
            </div>
        </div>
        </div>'''
        return html

    def render_edit_form(self, file_id, file_type):
        """Render edit form for a file"""
        if file_type == 'recipe':
            file_path = RECIPES / f"{file_id}.md"
        elif file_type == 'inventory':
            file_path = INVENTORY / f"{file_id}.md"
        else:
            file_path = RULES / f"{file_id}.md"

        if not file_path.exists():
            return '<div class="panel"><h2>File not found</h2></div>'

        content = file_path.read_text(encoding='utf-8')
        back_url = f'/?id={file_id}' if file_type == 'recipe' else f'/?view={file_type}&id={file_id}'

        html = f'''<div class="panel"><h2>Edit: {file_id}</h2>
        <form method="POST" action="/?edit={file_id}&type={file_type}" class="edit-form">
            <textarea name="content">{content}</textarea>
            <div class="actions">
                <button type="submit" class="btn-save">Save Changes</button>
                <a href="{back_url}" class="btn-cancel">Cancel</a>
            </div>
        </form>
        </div>'''
        return html

def get_lan_ip():
    """Detect local network IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '127.0.0.1'

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5555))
    lan_ip = get_lan_ip()
    print("""
  ┌─┐┬ ┬┌─┐┌┐┌   ┬┌─┬┌┬┐
  │  ├─┤├┤ │││───├┴┐│ │
  └─┘┴ ┴└─┘┘└┘   ┴ ┴┴ ┴  v2.0
  ════════════════════════════""")
    print(f"  Recipes:    {len(ALL_RECIPES)}")
    print(f"  Inventory:  {len(ALL_INVENTORY)}")
    print(f"  Knowledge:  {len(ALL_RULES)}")
    print(f"  Shop Lists: {len(load_shoplist().get('lists', []))}")
    print(f"\n  Keys: ↑↓jk nav | Enter select | / search")
    print(f"\n  → Local:   http://localhost:{port}")
    print(f"  → Network: http://{lan_ip}:{port}")
    print(f"\n  Ctrl+C to stop\n")

    HTTPServer(('', port), Handler).serve_forever()
