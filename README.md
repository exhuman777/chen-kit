# CHEN-KIT v2.0

Personal Kitchen Knowledge System — recipes, inventory, diet rules, and knowledge base in one local dashboard.

```
┌─┐┬ ┬┌─┐┌┐┌   ┬┌─┬┌┬┐
│  ├─┤├┤ │││───├┴┐│ │
└─┘┴ ┴└─┘┘└┘   ┴ ┴┴ ┴
```

## One-Liner Install

```bash
git clone https://github.com/exhuman777/chen-kit.git && cd chen-kit && python3 dashboard.py
```

Open http://localhost:5555 — that's it. Zero dependencies, pure Python stdlib.

### Custom port

```bash
PORT=8080 python3 dashboard.py
```

### Using the launcher

```bash
./start.sh
```

## Features

- **Recipes** — Store, search, edit. Ingredient availability auto-matched against inventory
- **Inventory** — Track what you have by category. Add/remove items inline
- **Knowledge Base** — Diet rules, TCM, Ayurveda, nutritional guidelines (PL/EN bilingual)
- **Shop List** — Multiple lists with check-off, progress tracking
- **Constellation** — 3D Three.js visualization of recipe-ingredient-knowledge connections
- **Keyboard nav** — `j/k` or arrow keys to browse, `/` to search, `Enter` to select
- **Retro mode** — Toggle green-on-black CRT aesthetic
- **PL/EN toggle** — Switch interface language
- **CRUD** — Create, edit, delete recipes and knowledge articles in-browser
- **Network accessible** — Binds to `0.0.0.0`, accessible from any device on your LAN

## Folder Structure

```
kitchen/
├── dashboard.py          # Main server (single file, stdlib only)
├── constellation.html    # 3D visualization
├── start.sh              # Launcher script
├── recipes/              # Markdown recipe files
│   └── en/               # English translations
├── inventory/            # Markdown inventory files
│   └── en/               # English translations
├── rules/                # Knowledge base articles
│   └── en/               # English translations
├── transcripts/          # Voice transcripts (optional)
├── search.py             # Semantic search (optional)
└── requirements.txt      # For optional semantic search
```

## Adding Your Own Content

### Recipes

Create a `.md` file in `recipes/`:

```markdown
# Recipe: Your Recipe Name

tags: dinner, quick
time: 30min

## Ingredients
- [ ] 200g rice
- [ ] 1 onion

## Steps
1. Cook the rice
2. Chop the onion
```

Or use the **+ New Recipe** button in the dashboard.

### Knowledge Articles

Create a `.md` file in `rules/`:

```markdown
# Article Title

category: health/nutrition
tags: vitamins, minerals
priority: 2

## Do
- [ ] Eat leafy greens daily

## Don't
- [ ] Skip breakfast
```

### Inventory

Create a `.md` file in `inventory/`:

```markdown
# Pantry

## Grains
- [ ] Rice
- [ ] Oats

## Spices
- [ ] Turmeric
- [ ] Cumin
```

## Optional: Semantic Search

Install dependencies for AI-powered search:

```bash
pip install -r requirements.txt
```

This enables fuzzy/semantic matching across recipes and knowledge articles.

## Auto-Start on macOS

Copy the launchd plist to auto-start CHEN-KIT on boot:

```bash
cp ai.rufus.chen-kit.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/ai.rufus.chen-kit.plist
```

To stop:

```bash
launchctl unload ~/Library/LaunchAgents/ai.rufus.chen-kit.plist
```

## Deploy on Zo.computer

1. Upload the `kitchen/` folder as a User Service
2. Set entrypoint: `python3 dashboard.py`
3. Set port: `5555` (or configure via `PORT` env var)

## Credits

**Exhuman** — [IG @exhto](https://instagram.com/exhto) · [X @3xhuman](https://x.com/3xhuman)

Built with [Claude](https://claude.ai) by Anthropic

## License

MIT
