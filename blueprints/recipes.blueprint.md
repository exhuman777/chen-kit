# Blueprint: Recipe
target_folder: recipes
classification_keywords: [recipe, przepis, gotuj, cook, składniki, ingredients, posiłek, meal, danie, dish]
embedding_weight: 0.7

## Required Fields
- title: "# Recipe: [Name]"
- tags: "tags: [breakfast/lunch/dinner/snack/dessert]"

## Optional Fields
- time: "time: [duration]"
- source: "source: [origin]"

## Required Sections
### Ingredients
format: "- [ ] [quantity] [ingredient]"
min_items: 2

### Steps
format: "1. [action]"
min_items: 1

## Optional Sections
- Notes
- Variations
- Tips

## Validation Rules
- ingredients must use "- [ ]" checkbox format
- tags should be comma-separated
- time should include units (min/h)

## Example
```markdown
# Recipe: Shakshuka
tags: breakfast, vegetarian, quick
time: 20 min

## Ingredients
- [ ] 2 jajka
- [ ] 1 puszka pomidorów
- [ ] 1 cebula
- [ ] przyprawy (kminek, papryka)

## Steps
1. Podsmaż cebulę na oleju
2. Dodaj pomidory i przyprawy
3. Zrób wgłębienia i wbij jajka
4. Gotuj pod przykryciem 5 min

## Notes
Podawaj z chlebem
```
