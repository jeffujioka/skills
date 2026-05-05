---
name: word-breakdown
description: "Create German study notes in Obsidian from a word. Auto-classifies part of speech, generates trilingual content (DE/EN/PT-BR), writes to vault via obsidian-cli. Triggers on: /word-breakdown, German vocabulary, neue Wörter, Vokabeln."
---

# Word Breakdown

Generate German study notes in Obsidian. Classifies words, fills templates, updates indexes, finds connections.

## Prerequisites

- Obsidian must be running (required by obsidian-cli)
- Read `config.yaml` for vault_path, study_path, default_level, templates_path, and templates mapping

## Input Parsing

The user invokes with: `/word-breakdown [level?] word1[, word2, ...] [example sentences]`

**Parse rules:**
1. If the first token matches a CEFR level (A1, A2, B1, B2, C1, C2 — case-insensitive), use it as the level override. Otherwise use `default_level` from config.
2. Words are comma-separated OR one per line (first line only for comma mode).
3. Lines after the first word (that are not additional comma-separated words) are treated as user-provided example sentences for the LAST word mentioned.
4. If a word starts with an article (der/die/das), treat it as a noun with the article already specified.

**Examples:**
- `/word-breakdown lernen` → one word, default level
- `/word-breakdown B1 unterstützen` → one word, level B1
- `/word-breakdown danken, dankbar, die Dankbarkeit` → three words, default level
- `/word-breakdown regelmäßig\nIch lerne regelmäßig.` → one word + 1 example sentence

## Workflow

For each word in the input, execute these steps:

### Step 1: Classify

Use German linguistic knowledge to determine all applicable parts of speech. Read `references/classification-rules.md` for rules and edge cases.

If the word has multiple valid classifications with meaningfully different semantics, note all of them and proceed to generate a note for EACH.

### Step 2: Check for Duplicates

```bash
obsidian search query="{word}" path="{study_path}/{subdirectory}/"
```

If a note already exists:
- Show the user what the current note contains (read via `obsidian read`)
- Ask: "Regenerate? [y/n]"
- If yes: regenerate and show what changed (diff summary)
- If no: skip this word

### Step 3: Read Template from Vault

Read the appropriate Obsidian template from the vault using `obsidian-cli`:

```bash
obsidian read path="{templates_path}/{template_name}.md"
```

Map classification to template name using `config.yaml` → `templates` mapping:
- verb → `Deutsch Verb`
- adjective → `Deutsch Adjective`
- noun → `Deutsch Noun`
- modal_verb → `Deutsch Modal Verb`
- pronoun → `Deutsch Pronoun`
- adverb → `Deutsch Adverb`

The template defines the structure (sections, tables, frontmatter fields). Use it as the skeleton for the generated note.

### Step 4: Generate Note Content

Fill the template structure with content using German linguistic knowledge.

**Content generation rules:**
- All translations in 3 languages: Deutsch, English (US), Português (BR)
- Exactly 10 example sentences in the Examples table
- User-provided sentences go first (translated to the other 2 languages)
- Generate remaining sentences to reach 10, varying tense/subject/context
- Optional sections (marked with `<!-- Optional: ... -->` in templates): ONLY include if relevant to the specific word
- Recall callouts: ONLY generate for words with subtle distinctions or common learner traps
- Remove HTML comments from the template (they are instructions, not content)

**Frontmatter:**
- `source: AI`
- `area: [study]`
- `project:` (empty)
- `related:` — populated in Step 6
- `tags:` — use level from input parsing
- `part_of_speech:` — the classification
- Type-specific fields (auxiliary, separable, reflexive, gender, pronoun_type, adverb_type) — fill if present in template

### Step 5: Create the Note

```bash
obsidian create name="{filename}" path="{study_path}/{subdirectory}/{filename}.md" content="{full note content}" silent
```

Filename rules:
- Verbs: infinitive (e.g., `lernen`)
- Nouns: `{article} {Capitalized}` (e.g., `die Erläuterung`)
- All others: base form (e.g., `regelmäßig`)

### Step 6: Find Related Links

Search within `{study_path}/` for connections:

```bash
obsidian search query="{word stem}" path="{study_path}/"
```

Look for:
- Word family: verb ↔ noun ↔ adjective derivations (danken ↔ dankbar ↔ die Dankbarkeit)
- Antonyms: un- prefix pairs (regelmäßig ↔ unregelmäßig)
- Same-root words: already noted in vault

For each found connection:
- Add to the new note's `related` frontmatter
- Update the found note's `related` frontmatter to link back:
  ```bash
  obsidian read file="{related note}"
  ```
  Then edit to add the new wikilink to its `related` list.

### Step 7: Update Category Index

Append the new wikilink to the category index note:

```bash
obsidian read file="{category index}"
```

Then edit to:
1. Add `- [[Study/Deutschkurs {Level} Enhanced/{Subdirectory}/{filename}|{word}]]` under `## Word Notes`
2. Add the wikilink to `related` in the index frontmatter

### Step 8: Report Summary

Output a concise summary per word created. Format:

For single word:
```
Created: {full path}
  → Classification: {type}
  → Index updated: [[{index path}]]
  → Related: {links or "(none found)"}
```

For ambiguous words, prefix with:
```
⚠️ "{word}" has multiple classifications:
```

For batch, wrap with:
```
Batch: {n} words processed
{individual summaries}
→ Word family linked: {connections}
```

## Language

Match the user's language. If they write in Portuguese, respond in Portuguese. If English, respond in English. If mixed, follow the mix. The NOTE content is always trilingual regardless.

## Error Handling

- If Obsidian is not running: tell the user to open Obsidian first
- If study_path directory doesn't exist: warn and ask whether to create it
- If a level override targets a non-existent directory: warn and offer to use default or create
- If `obsidian` CLI is not available: suggest installing it and link to https://help.obsidian.md/cli
