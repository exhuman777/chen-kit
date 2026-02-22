# Knowledge Base - Expansion Guide

## Overview

The Knowledge Base is designed as a personal wiki for health, wellness, and lifestyle knowledge. It supports multiple domains and is easily expandable.

## Structure

```
rules/
├── 01-core-diet.md          # Core dietary principles
├── 02-ayurveda-basics.md    # Ayurvedic fundamentals
├── 03-tcm-principles.md     # TCM basics
├── 04-tofu-preparation.md   # Specific techniques
└── ...
```

## Domains

| Domain | Description |
|--------|-------------|
| `diet` | Dietary rules, restrictions, substitutes |
| `health` | General health, wellness practices |
| `ayurveda` | Ayurvedic principles, doshas, practices |
| `tcm` | Traditional Chinese Medicine |
| `yoga` | Yoga practices, asanas, philosophy |
| `meditation` | Meditation techniques, mindfulness |

## Article Template

```markdown
# [Title]
category: [domain]/[subdomain]

## Zasady
Core principles and recommendations:
- [ ] Principle 1
- [ ] Principle 2

## Zakazy
Things to avoid:
- [ ] Avoid this
- [ ] Don't do that

## Praktyki
Practical applications:
- [ ] Practice 1
- [ ] Practice 2

## Notes
Additional context, sources, personal observations.
```

## Section Types

| Section | Color | Purpose |
|---------|-------|---------|
| `Zasady` | Green | Positive rules, recommendations |
| `Zakazy` | Red | Prohibitions, things to avoid |
| `Praktyki` | Default | Practical applications |
| `Notes` | Gray | Context, observations |

## Naming Convention

Files are sorted alphabetically. Use number prefixes for ordering:
- `01-` through `09-` for core/fundamental content
- `10-` through `19-` for specific topics
- `20-` through `29-` for advanced/detailed content

## Categories

### Diet
- `diet/core` - Core dietary rules
- `diet/fats` - Fat consumption rules
- `diet/protein` - Protein sources, combinations
- `diet/ingredients` - Specific ingredient guidelines
- `diet/substitutes` - Healthy alternatives
- `diet/preparation` - Cooking techniques
- `diet/meals` - Meal planning guidelines

### Health
- `health/ayurveda` - Ayurvedic practices
- `health/tcm` - Traditional Chinese Medicine
- `health/wellness` - General wellness
- `health/drinks` - Beverage guidelines

### Wellness (future)
- `wellness/yoga` - Yoga practices
- `wellness/meditation` - Meditation techniques
- `wellness/breathing` - Pranayama, breathwork
- `wellness/sleep` - Sleep hygiene

## Cross-referencing

Use keywords in items to enable search linking:
```markdown
- [ ] Tofu: marinate 30min before cooking
```
The word "Tofu" becomes searchable and links to related recipes.

## Best Practices

1. **One topic per file** - Keep articles focused
2. **Use consistent categories** - Follow domain/subdomain pattern
3. **Include Notes** - Add personal observations
4. **Keep items actionable** - Start with verbs
5. **Link keywords** - Use searchable terms

## Adding New Content

1. Create new file: `rules/XX-topic-name.md`
2. Set category in header
3. Add sections (Zasady, Zakazy, Notes)
4. Dashboard auto-reloads on edit save
