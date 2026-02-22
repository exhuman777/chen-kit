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
  <a href="#whats-inside">What's Inside</a> &middot;
  <a href="#features">Features</a> &middot;
  <a href="#make-it-yours">Make It Yours</a> &middot;
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

## What's Inside

This isn't an empty template. CHEN-KIT ships with a **complete foundation** built by [@exhto](https://instagram.com/exhto) -- 145 recipes, 25 knowledge articles, full inventory system, all in Polish and English. Clone it and you're already cooking.

### 145 Recipes (PL + EN)

Real recipes, tested and organized. A sample of what's included:

| Category | Examples |
|----------|----------|
| **Bowls & Mains** | Pad Thai, Kitchari, Tofu Scramble, Shepherd's Pie, Moussaka, Stir-Fry |
| **Burgers** | Chickpea & Quinoa Burger, Guacamole Burger, Plantway Burger, Mac & Cheese Burger |
| **Soups** | Pumpkin Soup, Broccoli Ayurveda, Lentil Soup, Power Broth, Pozole |
| **Sweets** | Chocolate Cake, Cinnamon Cookies, Matcha Muffins, Millionaire Bars, Twixy |
| **Drinks** | Golden Milk, Bitcoin Mocktail, Cherry Latte, Pecan Smoothie, Ojas Smoothie |
| **Breakfast** | Coconut Oatmeal, French Toast, Pumpkin Spice Pancakes, Chia Pudding |
| **Wraps & Snacks** | Falafel Tzatziki, Pistachio Tortilla, Wontons, Empanadas, Tamales |

Every recipe has ingredients with checkbox tracking, step-by-step instructions, tags, and time estimates.

### 25 Knowledge Articles

Deep knowledge base covering nutrition, Traditional Chinese Medicine, and Ayurveda:

- **Core Diet Rules** -- meal timing, breakfast/lunch/dinner guidelines, prohibitions
- **TCM Practices & Organ Health** -- lung support, kidney vitality, foot soaking rituals
- **Ayurveda: Balance & Digestion** -- digestive fire (Agni), Vata balancing, building Ojas
- **Plant Protein Sources** -- complete vegan protein guide
- **Ayurvedic Spices** -- healing properties and usage
- **Nervous System Reset** -- recovery practices
- **Healing Soup Ingredients** -- medicinal broth building
- **Anti-Aging Teas** -- herbal formulas for longevity
- **Adzuki Bean Properties** -- TCM superfood deep dive
- **Post-Travel Balance** -- Ayurvedic recovery protocol
- **Kitchari Basics** -- the ultimate healing meal
- **Ghee & Oils** -- when to use what
- **Tofu Preparation** -- techniques for perfect tofu
- **Healthy Substitutes** -- swap guide for common ingredients

All articles have Do/Don't sections, priority levels, and cross-linked tags.

### Inventory System

Pre-built category structure for tracking your kitchen stock -- spices, grains, proteins, vegetables, pantry staples. The dashboard auto-matches your inventory against recipe ingredients so you always know what you can cook right now.

> **This is a perfect foundation.** Use it as-is, customize it, add your own recipes, or strip it down to the structure and fill it with your own knowledge. Built by EXHTO as a real daily-use system, not a demo.

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
├── recipes/              # 145 markdown recipe files
│   └── en/               # English translations (145)
├── inventory/            # Inventory by category
│   └── en/               # English translations
├── rules/                # 25 knowledge base articles
│   └── en/               # English translations (25)
├── transcripts/          # Voice transcripts (optional)
├── search.py             # Semantic search (optional)
└── requirements.txt      # For optional semantic search
```

---

## Make It Yours

Everything is markdown. Add, edit, or delete files -- the dashboard picks them up automatically.

### Add a Recipe

Drop a `.md` file in `recipes/` or use the **+ New Recipe** button in the dashboard:

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

### Add a Knowledge Article

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

### Add Inventory

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

Deploy on [Zo.computer](https://zo.computer) in 3 steps:

```bash
# 1. Clone the repo on your Zo instance
git clone https://github.com/exhuman777/chen-kit.git

# 2. Set up as User Service
cd chen-kit
PORT=5555 python3 dashboard.py
```

3. In Zo dashboard: create a **User Service** with:
   - **Working directory:** `chen-kit/`
   - **Entrypoint:** `python3 dashboard.py`
   - **Port:** `5555`
   - **Environment:** `PORT=5555`

That's it -- accessible at `https://your-zo-instance.zo.computer:5555`

### Any server

```bash
PORT=5555 python3 dashboard.py
```

No build step. No containers. Runs anywhere Python 3 exists.

---

## Credits

Created by **Exhuman** -- [IG @exhto](https://instagram.com/exhto) &middot; [X @3xhuman](https://x.com/3xhuman)

Built with [Claude](https://claude.ai) by Anthropic

## License

MIT
