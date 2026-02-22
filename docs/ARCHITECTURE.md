# CHEN-KIT Architecture

## Overview

Single-file Python web server with no external dependencies (except Three.js for constellation).

## Components

```
┌─────────────────────────────────────────────────────┐
│                    dashboard.py                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              Data Layer                       │   │
│  │  - parse_md()     - load_folder()            │   │
│  │  - get_inventory() - get_inventory_by_cat()  │   │
│  │  - load_mealplan() - save_mealplan()         │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │              Logic Layer                      │   │
│  │  - score_recipe()  - ingredient_match()      │   │
│  │  - extract_key_words()                       │   │
│  │  - categorize_recipe()                       │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │              HTTP Handler                     │   │
│  │  - do_GET()  - do_POST()                     │   │
│  │  - Views: recipes, donext, mealplan,         │   │
│  │           inventory, knowledge               │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │              Render Layer                     │   │
│  │  - render_recipes_overview()                 │   │
│  │  - render_donext_single()                    │   │
│  │  - render_mealplan_calendar()                │   │
│  │  - render_inventory_overview()               │   │
│  │  - render_knowledge_overview()               │   │
│  │  - render_knowledge_article()                │   │
│  │  - render_recipe()                           │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Data Flow

```
Markdown Files → parse_md() → In-memory dicts → Render → HTML
     ↑                                                    │
     └────────────── POST handlers ←──────────────────────┘
```

## Globals

| Variable | Type | Description |
|----------|------|-------------|
| `ALL_RECIPES` | list[dict] | Parsed recipe files |
| `ALL_INVENTORY` | set | All inventory items |
| `ALL_RULES` | list[dict] | Parsed knowledge articles |
| `INV_BY_CAT` | dict | Inventory grouped by category |
| `TAGS_STATS` | Counter | Recipe tag counts |
| `RULES_DO` | list | All "do" items from rules |
| `RULES_DONT` | list | All "don't" items from rules |

## Ingredient Matching

Smart matching ignores common words:
```python
IGNORE_WORDS = {
    'swieze', 'mielony', 'suszone', ...  # adjectives
    'lyzka', 'szklanka', 'gram', ...     # units
    'naturalne', 'ekologiczne', ...      # qualifiers
}
```

Matching logic:
1. Extract key words from ingredient
2. Check if any key word matches inventory item
3. Return True if match found

## Views

| View | URL | Handler |
|------|-----|---------|
| Recipes | `/` | `render_recipes_overview()` |
| Do Next | `/?view=donext` | `render_donext_single()` |
| Meal Plan | `/?view=mealplan` | `render_mealplan_calendar()` |
| Inventory | `/?view=inventory` | `render_inventory_overview()` |
| Knowledge | `/?view=knowledge` | `render_knowledge_overview()` |
| Constellation | `/constellation` | `serve_constellation()` |

## POST Endpoints

| Action | URL | Params |
|--------|-----|--------|
| Save meal | `/?save_mealplan=1` | day_idx, meal_type, recipe |
| Add day | `/?add_day=1` | - |
| Remove day | `/?remove_day=N` | - |
| Add inventory | `/?add_inv=1` | category, item |
| Delete inventory | `/?del_inv=item&cat=cat` | - |
| Edit file | `/?edit=id&type=type` | content |

## Styling

CSS is embedded in HTML template. Key colors:
- Background: `#0d1117` (dark)
- Panel: `#161b22`
- Border: `#30363d`
- Text: `#c9d1d9`
- Accent: `#58a6ff` (blue)
- Success: `#3fb950` (green)
- Warning: `#f0883e` (orange)
- Error: `#f85149` (red)

## Extending

### Add new view:
1. Add nav link in HTML template
2. Add nav key in `nav` dict
3. Add `elif view == 'newview':` handler
4. Create `render_newview()` method

### Add new data type:
1. Create folder (e.g., `notes/`)
2. Add constant: `NOTES = BASE / "notes"`
3. Add loader: `ALL_NOTES = load_folder(NOTES)`
4. Create view and render methods
