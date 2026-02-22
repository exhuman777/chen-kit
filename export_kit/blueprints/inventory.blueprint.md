# Blueprint: Inventory
target_folder: inventory
classification_keywords: [inventory, zakupy, mamy, kupiliśmy, shopping, lista, pantry, spiżarnia]
embedding_weight: 0.5

## Required Fields
- title: "# Inventory: [Location/Date]"
- updated: "updated: [YYYY-MM-DD]"

## Required Sections
### [Category Name]
format: "- [ ] [item name] [optional ~quantity]"
dynamic: true

## Common Categories
- Kasze i Ziarno
- Maki
- Przyprawy
- Oleje
- Herbaty
- Warzywa
- Owoce

## Validation Rules
- items must use "- [ ]" checkbox format
- quantity notation: ~500g, ~1kg, ~2szt

## Example
```markdown
# Inventory: Kuchnia
updated: 2024-01-15

## Kasze i Ziarno
- [ ] ryż basmati ~1kg
- [ ] kasza jaglana ~500g
- [ ] quinoa ~300g

## Przyprawy
- [ ] kurkuma
- [ ] imbir mielony
- [ ] kminek
```
