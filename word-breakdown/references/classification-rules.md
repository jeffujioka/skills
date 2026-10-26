# Classification Rules

## Supported Classifications

| Classification | Key Signals | Subdirectory | Filename Pattern |
|---|---|---|---|
| verb | Infinitive ending in -en/-eln/-ern, describes an action/state | Verben/ | `{infinitive}.md` |
| adjective | Describes quality/property of a noun, can be declined, has comparison forms | Adjektive/ | `{base form}.md` |
| noun | Names a thing/concept/person, has grammatical gender (der/die/das) | Substantive/ | `{article} {Capitalized}.md` |
| modal verb | One of: dürfen, können, mögen, müssen, sollen, wollen | Modalverb/ | `{infinitive}.md` |
| pronoun | Replaces or references a noun (man, jemand, etwas, etc.) | Pronomen/ | `{word}.md` |
| adverb | Modifies a verb/sentence/adjective, does not decline, no comparison (usually) | Adverbien/ | `{word}.md` |

## Ambiguity Rules

Many German words belong to multiple categories. When a word has multiple valid classifications:

1. Generate a separate note for EACH classification
2. Warn the user about the multiple senses
3. Cross-link the notes via `related` frontmatter

### Common Ambiguity Patterns

- **Adjective + Adverb**: Most German adjectives can function adverbially (e.g., `bestimmt`, `regelmäßig`). Only create BOTH notes if the word has meaningfully different semantics in each role. If the adverbial usage is just the adjective modifying a verb (standard behavior), create only the adjective note.
- **Verb participle → Adjective**: Past participles used as adjectives (e.g., `bestimmt` from `bestimmen`). Create both if independently useful.
- **Noun derived from verb**: (e.g., `die Erläuterung` from `erläutern`). Create both and link via Word Family.

## Edge Cases

- **Interjections/particles** (danke, bitte): Classify as adverb. Add a Note section explaining the particle/interjection usage.
- **Compound nouns**: Treat as a single noun. Optionally link component words in Word Family if they exist.
- **Reflexive verbs** (sich entspannen): Filename uses infinitive without `sich`. The `reflexive: true` property is set in frontmatter.
- **Separable verbs** (aufstehen, ankommen): Filename uses the full infinitive. The `separable: true` property is set in frontmatter.
- **Words with prefix un-**: If the base word exists, link via `related`. If not, note the derivation in Pattern/Note section.

## Article Detection for Nouns

Determine grammatical gender using linguistic knowledge:
- Common patterns: -ung → die, -keit/-heit → die, -ment → das, -er → often der
- Always verify — patterns have exceptions
- Prepend the correct article (der/die/das) to the filename

## Level Override

If the user specifies a CEFR level before the word (e.g., `B1 unterstützen`):
- Use that level in tags: `subject/classes/deutsch/{level}/{category}`
- Use that level in the study path: `Study/Deutschkurs {Level} Enhanced/`
- If the target directory doesn't exist, warn the user and ask whether to create it or use the default

## Batch Processing

When multiple words are provided (comma-separated or one per line):
- Process each word independently
- Cross-link words that belong to the same word family
- Report a combined summary at the end
