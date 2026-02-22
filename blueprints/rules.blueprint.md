# Blueprint: Knowledge Rule
target_folder: rules
classification_keywords: [rule, zasada, wiedza, knowledge, ayurveda, tcm, health, zdrowie, praktyka, practice]
embedding_weight: 0.8

## Required Fields
- title: "# [Topic Name]"
- category: "category: [domain/type]"

## Optional Fields
- tags: "tags: [keywords]"
- priority: "priority: [1-10]"

## Required Sections
### Do (or Zasady/Praktyki)
format: "- [ ] [practice/rule]"
min_items: 1

## Optional Sections
- Don't (Zakazy/Unikaj)
- Notes
- Sources
- References

## Validation Rules
- category should use domain/subdomain format (e.g., health/tcm, diet/ayurveda)
- practices must use "- [ ]" checkbox format

## Example
```markdown
# Praktyki Poranne TCM
category: health/tcm
tags: morning, routine, energia

## Zasady
- [ ] Wypij ciepłą wodę po przebudzeniu
- [ ] Rozciąganie 10 min przed śniadaniem
- [ ] Głębokie oddychanie przez nos

## Zakazy
- [ ] Nie pij zimnej wody rano
- [ ] Nie jedz ciężkich posiłków przed 10:00

## Notes
Praktyki z tradycyjnej medycyny chińskiej
```
