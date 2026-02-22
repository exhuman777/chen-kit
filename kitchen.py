#!/usr/bin/env python3
"""
KITCHEN v1.0 - Home Food Management System
MS-DOS style CLI for recipes, inventory, and meal planning
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Set
import textwrap

BASE = Path(__file__).parent
INVENTORY = BASE / "inventory"
RECIPES = BASE / "recipes"
RULES = BASE / "rules"
TRANSCRIPTS = BASE / "transcripts"
BOOKS = BASE / "books"

# ============================================================================
#  ASCII UI
# ============================================================================

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def box(title: str, width: int = 60):
    print("+" + "-" * (width - 2) + "+")
    print("|" + title.center(width - 2) + "|")
    print("+" + "-" * (width - 2) + "+")

def line(width: int = 60):
    print("+" + "-" * (width - 2) + "+")

def menu_item(key: str, text: str):
    print(f"  [{key}] {text}")

def prompt(text: str = ">") -> str:
    return input(f"\n{text} ").strip()

def pause():
    input("\n[Press ENTER to continue]")

def header():
    clear()
    print("""
+============================================================+
|    _  _____ _____ ____ _   _ _____ _   _                   |
|   | |/ /_ _|_   _/ ___| | | | ____| \ | |                  |
|   | ' / | |  | || |   | |_| |  _| |  \| |                  |
|   | . \ | |  | || |___|  _  | |___| |\  |                  |
|   |_|\_\___| |_| \____|_| |_|_____|_| \_|  v1.0            |
|                                                            |
|            Home Food Management System                     |
+============================================================+
""")

# ============================================================================
#  FILE PARSING
# ============================================================================

def parse_md(path: Path) -> Dict:
    """Parse markdown file with frontmatter-like headers"""
    content = path.read_text(encoding='utf-8')
    result = {
        'path': path,
        'name': path.stem,
        'content': content,
        'items': [],
        'meta': {}
    }

    # Extract title
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        result['title'] = title_match.group(1)

    # Extract metadata (key: value lines after title)
    for match in re.finditer(r'^(\w+):\s*(.+)$', content, re.MULTILINE):
        result['meta'][match.group(1).lower()] = match.group(2)

    # Extract checklist items
    for match in re.finditer(r'^-\s*\[[ x]\]\s*(.+)$', content, re.MULTILINE):
        result['items'].append(match.group(1).strip())

    # Extract sections
    sections = {}
    current_section = None
    for line in content.split('\n'):
        if line.startswith('## '):
            current_section = line[3:].strip()
            sections[current_section] = []
        elif current_section and line.strip():
            sections[current_section].append(line.strip())
    result['sections'] = sections

    return result

def load_folder(folder: Path) -> List[Dict]:
    """Load all .md files from folder"""
    if not folder.exists():
        return []
    files = []
    for f in sorted(folder.glob("*.md")):
        if not f.name.startswith('_'):
            files.append(parse_md(f))
    return files

# ============================================================================
#  INVENTORY
# ============================================================================

def get_all_inventory_items() -> Set[str]:
    """Get all inventory items as a set"""
    items = set()
    for inv in load_folder(INVENTORY):
        items.update(inv['items'])
    return items

def show_inventory():
    clear()
    box("INVENTORY", 60)

    files = load_folder(INVENTORY)
    if not files:
        print("\n  No inventory files found.")
        print(f"  Add .md files to: {INVENTORY}")
        pause()
        return

    for inv in files:
        print(f"\n  {inv.get('title', inv['name']).upper()}")
        print("  " + "-" * 40)

        for section, lines in inv.get('sections', {}).items():
            print(f"\n  [{section}]")
            for line in lines:
                if line.startswith('- '):
                    print(f"    {line[2:]}")

    print(f"\n  Total items: {len(get_all_inventory_items())}")
    pause()

def search_inventory():
    clear()
    box("SEARCH INVENTORY", 60)

    query = prompt("Search term:").lower()
    if not query:
        return

    items = get_all_inventory_items()
    matches = [i for i in items if query in i.lower()]

    print(f"\n  Found {len(matches)} matches:\n")
    for item in sorted(matches):
        print(f"    - {item}")

    pause()

# ============================================================================
#  RECIPES
# ============================================================================

def show_recipes():
    clear()
    box("RECIPES", 60)

    recipes = load_folder(RECIPES)
    if not recipes:
        print("\n  No recipes found.")
        print(f"  Add .md files to: {RECIPES}")
        pause()
        return

    for i, r in enumerate(recipes, 1):
        tags = r['meta'].get('tags', '')
        time = r['meta'].get('time', '')
        title = r.get('title', r['name']).replace('Recipe: ', '')
        print(f"\n  {i}. {title}")
        if tags:
            print(f"     tags: {tags}")
        if time:
            print(f"     time: {time}")

    choice = prompt("Enter number to view (or ENTER to go back):")
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(recipes):
            view_recipe(recipes[idx])

def view_recipe(recipe: Dict):
    clear()
    box(recipe.get('title', recipe['name']).upper(), 60)

    # Meta
    for k, v in recipe['meta'].items():
        print(f"  {k}: {v}")

    # Sections
    for section, lines in recipe.get('sections', {}).items():
        print(f"\n  {section.upper()}")
        print("  " + "-" * 40)
        for line in lines:
            print(f"  {line}")

    # Check inventory
    print("\n  INVENTORY CHECK")
    print("  " + "-" * 40)
    inventory = get_all_inventory_items()
    for item in recipe['items']:
        # Simple fuzzy match
        found = any(item.lower() in inv.lower() or inv.lower() in item.lower()
                   for inv in inventory)
        status = "[X]" if found else "[ ]"
        print(f"  {status} {item}")

    pause()

def search_recipes():
    clear()
    box("SEARCH RECIPES", 60)

    query = prompt("Search term:").lower()
    if not query:
        return

    recipes = load_folder(RECIPES)
    matches = []
    for r in recipes:
        if query in r['content'].lower():
            matches.append(r)

    print(f"\n  Found {len(matches)} matches:\n")
    for r in matches:
        title = r.get('title', r['name']).replace('Recipe: ', '')
        print(f"    - {title}")

    pause()

# ============================================================================
#  RULES
# ============================================================================

def show_rules():
    clear()
    box("DIET RULES & KNOWLEDGE", 60)

    rules = load_folder(RULES)
    if not rules:
        print("\n  No rules defined yet.")
        print(f"  Add .md files to: {RULES}")
        pause()
        return

    for i, r in enumerate(rules, 1):
        title = r.get('title', r['name'])
        cat = r['meta'].get('category', '')
        print(f"\n  {i}. {title}")
        if cat:
            print(f"     [{cat}]")

    choice = prompt("Enter number to view (or ENTER to go back):")
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(rules):
            view_rule(rules[idx])

def view_rule(rule: Dict):
    clear()
    title = rule.get('title', rule['name'])
    box(title.upper(), 60)

    for section, lines in rule.get('sections', {}).items():
        print(f"\n  {section.upper()}")
        print("  " + "-" * 40)
        for line in lines:
            wrapped = textwrap.wrap(line, width=54)
            for w in wrapped:
                print(f"  {w}")

    pause()

# ============================================================================
#  TRANSCRIPTS
# ============================================================================

def show_transcripts():
    clear()
    box("TRANSCRIPTS", 60)

    transcripts = load_folder(TRANSCRIPTS)
    if not transcripts:
        print("\n  No transcripts found.")
        pause()
        return

    for i, t in enumerate(transcripts, 1):
        name = t['name'][:45] + "..." if len(t['name']) > 45 else t['name']
        print(f"  {i}. {name}")

    choice = prompt("Enter number to view (or ENTER to go back):")
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(transcripts):
            view_transcript(transcripts[idx])

def view_transcript(t: Dict):
    clear()
    box(t['name'][:50], 60)

    lines = t['content'].split('\n')
    page_size = 20
    offset = 0

    while True:
        clear()
        box(f"{t['name'][:40]} [{offset+1}-{min(offset+page_size, len(lines))}/{len(lines)}]", 60)

        for line in lines[offset:offset+page_size]:
            print(f"  {line[:56]}")

        print("\n  [N]ext  [P]rev  [Q]uit")
        choice = prompt(">").lower()

        if choice == 'n' and offset + page_size < len(lines):
            offset += page_size
        elif choice == 'p' and offset > 0:
            offset -= page_size
        elif choice == 'q':
            break

# ============================================================================
#  MEAL PROPOSAL
# ============================================================================

def propose_meal():
    clear()
    box("MEAL PROPOSAL ENGINE", 60)

    inventory = get_all_inventory_items()
    recipes = load_folder(RECIPES)
    rules = load_folder(RULES)

    if not recipes:
        print("\n  No recipes to propose from.")
        print(f"  Add recipes to: {RECIPES}")
        pause()
        return

    print(f"\n  Inventory: {len(inventory)} items")
    print(f"  Recipes:   {len(recipes)} available")
    print(f"  Rules:     {len(rules)} active")

    # Score recipes by available ingredients
    scored = []
    for r in recipes:
        if not r['items']:
            continue

        available = 0
        for item in r['items']:
            if any(item.lower() in inv.lower() or inv.lower() in item.lower()
                   for inv in inventory):
                available += 1

        score = available / len(r['items']) if r['items'] else 0
        scored.append((score, r))

    scored.sort(reverse=True, key=lambda x: x[0])

    print("\n  RECOMMENDED (by ingredient availability):")
    print("  " + "-" * 40)

    for score, r in scored[:5]:
        title = r.get('title', r['name']).replace('Recipe: ', '')
        pct = int(score * 100)
        bar = "#" * (pct // 10) + "." * (10 - pct // 10)
        print(f"\n  {title}")
        print(f"  [{bar}] {pct}% ingredients available")

    if not scored:
        print("\n  No recipes with ingredients found.")
        print("  Add ingredients to your recipes!")

    pause()

# ============================================================================
#  MAIN MENU
# ============================================================================

def main_menu():
    while True:
        header()

        menu_item("1", "Inventory      - View what you have")
        menu_item("2", "Recipes        - Browse recipes")
        menu_item("3", "Rules          - Diet rules & knowledge")
        menu_item("4", "Transcripts    - Voice memo transcripts")
        menu_item("5", "Propose Meal   - AI meal suggestion")
        menu_item("S", "Search         - Search everything")
        menu_item("Q", "Quit")

        line()

        choice = prompt(">").lower()

        if choice == '1':
            inventory_menu()
        elif choice == '2':
            recipes_menu()
        elif choice == '3':
            show_rules()
        elif choice == '4':
            show_transcripts()
        elif choice == '5':
            propose_meal()
        elif choice == 's':
            global_search()
        elif choice == 'q':
            clear()
            print("\n  Goodbye!\n")
            sys.exit(0)

def inventory_menu():
    while True:
        clear()
        box("INVENTORY", 60)
        menu_item("1", "View all")
        menu_item("2", "Search")
        menu_item("B", "Back")

        choice = prompt(">").lower()
        if choice == '1':
            show_inventory()
        elif choice == '2':
            search_inventory()
        elif choice == 'b':
            return

def recipes_menu():
    while True:
        clear()
        box("RECIPES", 60)
        menu_item("1", "Browse all")
        menu_item("2", "Search")
        menu_item("B", "Back")

        choice = prompt(">").lower()
        if choice == '1':
            show_recipes()
        elif choice == '2':
            search_recipes()
        elif choice == 'b':
            return

def global_search():
    clear()
    box("GLOBAL SEARCH", 60)

    query = prompt("Search term:").lower()
    if not query:
        return

    results = []

    # Search all folders
    for folder, label in [(INVENTORY, "INV"), (RECIPES, "RCP"),
                          (RULES, "RUL"), (TRANSCRIPTS, "TRS")]:
        for doc in load_folder(folder):
            if query in doc['content'].lower():
                results.append((label, doc.get('title', doc['name'])))

    print(f"\n  Found {len(results)} matches:\n")
    for label, name in results:
        name_short = name[:45] + "..." if len(name) > 45 else name
        print(f"  [{label}] {name_short}")

    pause()

# ============================================================================
#  ENTRY
# ============================================================================

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        clear()
        print("\n  Interrupted.\n")
        sys.exit(0)
