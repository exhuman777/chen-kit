```
 ██████╗██╗  ██╗███████╗███╗   ██╗      ██╗  ██╗██╗████████╗
██╔════╝██║  ██║██╔════╝████╗  ██║      ██║ ██╔╝██║╚══██╔══╝
██║     ███████║█████╗  ██╔██╗ ██║█████╗█████╔╝ ██║   ██║
██║     ██╔══██║██╔══╝  ██║╚██╗██║╚════╝██╔═██╗ ██║   ██║
╚██████╗██║  ██║███████╗██║ ╚████║      ██║  ██╗██║   ██║
 ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝      ╚═╝  ╚═╝╚═╝   ╚═╝
```

<p align="center">
  <strong>CHEN-KIT v2.0</strong>
</p>

<p align="center">
  <em>Personal Kitchen Knowledge System</em>
</p>

<p align="center">
  <a href="#one-liner-install">Install</a> &middot;
  <a href="#features">Features</a> &middot;
  <a href="#adding-your-own-content">Customize</a> &middot;
  <a href="#deploy">Deploy</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/dependencies-zero-purple" alt="zero dependencies" />
  <img src="https://img.shields.io/badge/python-stdlib%20only-brightgreen" alt="stdlib only" />
  <img src="https://img.shields.io/badge/recipes-145+-blue" alt="145+ recipes" />
  <img src="https://img.shields.io/badge/language-PL%20%2F%20EN-orange" alt="PL / EN" />
</p>

---

**Your recipes, your rules, your kitchen -- all in one place.**

Single-file Python server. No frameworks, no npm, no Docker. Just `python3 dashboard.py` and you're cooking. All data lives in markdown files you own and control.

---

## One-Liner Install

```bash
git clone https://github.com/exhuman777/chen-kit.git && cd chen-kit && python3 dashboard.py
```

Open http://localhost:5555 -- done. Custom port: `PORT=8080 python3 dashboard.py`

---

## Features

```
Dashboard ──▶ Recipes (145+ PL/EN, CRUD, ingredient matching)
          ──▶ Inventory (categories, add/remove inline)
          ──▶ Knowledge Base (diet rules, TCM, Ayurveda, 25+ articles)
          ──▶ Shop List (multiple lists, check-off, progress)
          ──▶ Constellation (3D Three.js visualization)
          ──▶ About (credits, project info)
```

- **Smart matching** -- auto-checks which recipes you can make from current inventory
- **Keyboard nav** -- `j/k` arrows to browse, `/` to search, `Enter` to select
- **Retro mode** -- toggle green-on-black CRT aesthetic
- **PL/EN toggle** -- full bilingual interface and content
- **Network accessible** -- binds to `0.0.0.0`, any device on your LAN can connect
- **CRUD** -- create, edit, delete recipes and knowledge articles in-browser
- **Optional semantic search** -- `pip install -r requirements.txt` for AI-powered fuzzy matching

---

## Folder Structure

```
chen-kit/
├── dashboard.py          # Server (single file, stdlib only)
├── constellation.html    # 3D visualization
├── start.sh              # Launcher script
├── recipes/              # Markdown recipe files
│   └── en/               # English translations
├── inventory/            # Inventory by category
│   └── en/               # English translations
├── rules/                # Knowledge base articles
│   └── en/               # English translations
├── transcripts/          # Voice transcripts (optional)
├── search.py             # Semantic search (optional)
└── requirements.txt      # For optional semantic search
```

---

## Adding Your Own Content

### Recipes

Drop a `.md` file in `recipes/` or use the **+ New Recipe** button:

```markdown
# Recipe: Your Recipe Name

tags: dinner, quick
time: 30min

## Ingredients
- [ ] 200g rice
- [ ] 1 onion
- [ ] 2 cloves garlic

## Steps
1. Cook the rice
2. Saute the onion and garlic
3. Combine and serve
```

### Knowledge Articles

Drop a `.md` file in `rules/`:

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

Drop a `.md` file in `inventory/`:

```markdown
# Pantry

## Grains
- [ ] Rice
- [ ] Oats

## Spices
- [ ] Turmeric
- [ ] Cumin
```

---

## Deploy

### Local (macOS auto-start)

```bash
cp ai.rufus.chen-kit.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/ai.rufus.chen-kit.plist
```

Starts on boot, stays alive if it crashes. Unload with `launchctl unload`.

### Zo.computer

1. Upload as User Service
2. Entrypoint: `python3 dashboard.py`
3. Port: `5555` (or set `PORT` env var)

### Any server

```bash
PORT=5555 python3 dashboard.py
```

No build step. No containers. Runs anywhere Python 3 exists.

---

## Credits

**Exhuman** -- [IG @exhto](https://instagram.com/exhto) &middot; [X @3xhuman](https://x.com/3xhuman)

Built with [Claude](https://claude.ai) by Anthropic

## License

MIT
