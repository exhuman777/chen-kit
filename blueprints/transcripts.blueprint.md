# Blueprint: Transcript
target_folder: transcripts
classification_keywords: [transcript, notatka, memo, voice, nagranie, myśli, thoughts, random]
embedding_weight: 0.6

## Required Fields
- title: "# [Topic/Date]"

## Optional Fields
- date: "date: [YYYY-MM-DD]"
- source: "source: [voice memo/meeting/lecture]"

## Content
Free-form text, no required sections.
Paragraphs separated by blank lines.

## Validation Rules
- must have title
- content length > 50 characters

## Example
```markdown
# Notatki z wykładu o trawieniu
date: 2024-01-15
source: voice memo

Dzisiaj słuchałam o tym jak ważne jest trawienie w ajurwedzie.
Agni - ogień trawienny - jest kluczowy dla zdrowia.

Główne punkty:
- Nie pij zimnych napojów podczas posiłków
- Jedz główny posiłek w południe
- Unikaj jedzenia gdy jesteś zestresowany
```
