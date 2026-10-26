# Input/Output Examples

## Example 1: Simple verb

**Input:** `/word-breakdown lernen`

**Actions:**
1. Classify: verb
2. Check duplicate: `obsidian search query="lernen" path="Study/Deutschkurs A2 Enhanced/Verben/"`
3. Read template: `obsidian read path="Templates/Deutsch Verb.md"`
4. Create note: `obsidian create name="lernen" path="Study/Deutschkurs A2 Enhanced/Verben/lernen.md" silent`
5. Update index: append wikilink to `Study/Deutschkurs A2 Enhanced/Verben.md`
6. Search related: scan for word family connections

**Output:**

```
Created: Study/Deutschkurs A2 Enhanced/Verben/lernen.md
  → Classification: verb
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Verben]]
  → Related: (none found)
```

## Example 2: Noun (auto-detect article)

**Input:** `/word-breakdown Spiegel`

**Actions:**
1. Classify: noun (masculine → der)
2. Check duplicate: search for "der Spiegel" in Substantive/
3. Read template: `obsidian read path="Templates/Deutsch Noun.md"`
4. Create note with filename `der Spiegel.md`
5. Update Substantive.md index

**Output:**

```
Created: Study/Deutschkurs A2 Enhanced/Substantive/der Spiegel.md
  → Classification: noun (der — masculine)
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Substantive]]
  → Related: (none found)
```

## Example 3: Ambiguous word

**Input:** `/word-breakdown bestimmt`

**Actions:**
1. Classify: adjective AND adverb (distinct meanings)
2. Create both notes
3. Cross-link via `related` frontmatter
4. Update both index notes

**Output:**

```
⚠️ "bestimmt" has multiple classifications:

Created: Study/Deutschkurs A2 Enhanced/Adjektive/bestimmt.md
  → Classification: adjective ("certain, specific")
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Adjektive]]

Created: Study/Deutschkurs A2 Enhanced/Adverbien/bestimmt.md
  → Classification: adverb ("certainly, surely")
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Adverbien]]

→ Cross-linked: both notes reference each other in `related`
→ Related: [[Study/Deutschkurs A2 Enhanced/Verben/bestimmen]] (word family)
```

## Example 4: With user-provided examples

**Input:**

```
/word-breakdown regelmäßig
Ich lerne regelmäßig.
Die Treffen sind regelmäßig.
Ich mache regelmäßig Pausen.
```

**Actions:**
1. Classify: adjective
2. Incorporate 3 user sentences into Examples table (positions 1-3)
3. Generate 7 more examples to reach 10

**Output:**

```
Created: Study/Deutschkurs A2 Enhanced/Adjektive/regelmäßig.md
  → Classification: adjective
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Adjektive]]
  → User examples: 3 incorporated (+ 7 generated)
  → Related: [[Study/Deutschkurs A2 Enhanced/Adjektive/unregelmäßig]] (antonym)
```

## Example 5: Batch mode

**Input:** `/word-breakdown danken, dankbar, die Dankbarkeit`

**Output:**

```
Batch: 3 words processed

Created: Study/Deutschkurs A2 Enhanced/Verben/danken.md
  → Classification: verb
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Verben]]

Created: Study/Deutschkurs A2 Enhanced/Adjektive/dankbar.md
  → Classification: adjective
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Adjektive]]

Created: Study/Deutschkurs A2 Enhanced/Substantive/die Dankbarkeit.md
  → Classification: noun (die — feminine)
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Substantive]]

→ Word family linked: danken ↔ dankbar ↔ die Dankbarkeit
```

## Example 6: Duplicate detected

**Input:** `/word-breakdown betrachten`

**Output:**

```
⚠️ Note already exists: Study/Deutschkurs A2 Enhanced/Verben/betrachten.md

Current note has:
  - 3 meanings (to look at, to observe, to consider)
  - 10 examples
  - Note section comparing betrachten/anschauen/sehen

Regenerate? [y/n]
```

If user says yes → regenerate, show diff of changes.

## Example 7: Level override

**Input:** `/word-breakdown B1 unterstützen`

**Actions:**
1. Level override detected: B1
2. Tags use `subject/classes/deutsch/b1/verben`
3. Study path: `Study/Deutschkurs B1 Enhanced/Verben/`
4. If directory doesn't exist: warn and ask

**Output:**

```
Created: Study/Deutschkurs B1 Enhanced/Verben/unterstützen.md
  → Classification: verb
  → Level: B1 (override)
  → Index updated: [[Study/Deutschkurs B1 Enhanced/Verben]]
```

## Example 8: Edge case (particle/interjection)

**Input:** `/word-breakdown danke`

**Output:**

```
Created: Study/Deutschkurs A2 Enhanced/Adverbien/danke.md
  → Classification: adverb (note: functions primarily as interjection/particle)
  → Index updated: [[Study/Deutschkurs A2 Enhanced/Adverbien]]
  → Related: [[Study/Deutschkurs A2 Enhanced/Verben/danken]] (word family)
```
