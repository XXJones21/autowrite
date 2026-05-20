# Session log template

Every career-intake round produces one session log file. The format mirrors a working notebook a research assistant might keep -- structured enough to scan in 30 seconds, loose enough to capture the things that don't fit neatly into bullet form.

## File location

```
<output-dir>/interview-notes/<YYYY-MM-DD>-<round-topic-slug>.md
```

Examples:
- `interview-notes/2026-05-12-current-role.md`
- `interview-notes/2026-05-13-flagship-project.md`
- `interview-notes/2026-05-14-personal-projects.md`

If multiple rounds happen on the same day, the topic slug disambiguates. Do not bundle multiple rounds into a single session log -- each round is a separate file so they can be re-read or revised independently.

## Schema

```markdown
# <YYYY-MM-DD> -- <Round Topic, Title Cased>

<One-paragraph framing of why this round happened and what the candidate was trying to surface. Written in your voice, not the candidate's. 2-3 sentences.>

## Context

- <Background fact about the candidate that bears on this round -- their role, target, constraint, etc.>
- <Another background fact, if relevant>
- <A third, if relevant>

## Working approach

<One paragraph describing how the round was conducted. Mention the interview style ("question at a time, stream-of-consciousness response"), any departures from the default (e.g., "candidate asked to skip quantification questions in this round"), and the question shape used to open the round.>

## Questions and key answers

1. **Q:** <Question 1, verbatim or paraphrased>
   **A:** <Candidate's response, summarized in 1-3 sentences. Use the candidate's own framing for the load-bearing nouns and verbs. Do not editorialize.>
2. **Q:** <Question 2 -- typically a follow-up on a specific claim from answer 1>
   **A:** <Response, same rules.>
3. ... <up to 4-5 Q/A pairs per round; stop logging when answers start repeating>

## Key reframings landed

<3-6 bullets. Insights or framings that emerged from the conversation. These are the things you'd want to remember six months from now if the candidate came back for another round.>

- **<Reframing 1 -- short label>.** <One-sentence explanation in the candidate's framing where possible.>
- **<Reframing 2>.** <Same shape.>
- ...

## Decisions

<Concrete choices made during the round about how to represent the work on the resume. Lean toward decisiveness -- "decided X over Y" rather than "considered X and Y".>

- <Decision 1 -- e.g., "Lead with team-size and tenure on the X bullet; omit headcount on the Y bullet.">
- <Decision 2>
- ...

## What got cut

<Things the candidate mentioned that we explicitly chose not to surface on the resume, with the reason. This section is the memory of what was rejected so we don't revisit it in future rounds.>

- <Cut item 1, with reason -- e.g., "Mentioned the 2019 prototype that didn't ship -- cut because no shipped artifact to back the claim, and the candidate has stronger items.">
- <Cut item 2, with reason>

## Outstanding work

<Checkbox list of things the candidate needs to follow up on. Open URLs to confirm. Start dates to verify. Quantification figures to look up. Anything that blocks finalizing the bullets.>

- [ ] <Follow-up 1>
- [ ] <Follow-up 2>

## Side notes for future sessions

<Anything that didn't fit the structured sections above but is worth keeping. Wry asides the candidate made. Long-tail context about how they think. Memory hooks for the next round. Keep it to a paragraph or two.>

<Free-form prose paragraph(s) here.>
```

## Tone and style guidance

- **Voice:** assistant's voice in the framing sections, candidate's voice in the Q&A and decisions. The mix is intentional -- the log should read like an assistant's notebook, not a transcript.
- **Specificity:** every decision and reframing should be specific enough that someone reading the file in 6 months can tell what the conversation actually decided. "Decided to lead with the AI work" is too vague; "Lead with the AI-engineering identity at top of resume; rewrite the Summary to anchor on context engineering" is right.
- **No filler.** If a section has nothing to say (no cuts happened, no outstanding follow-ups), write the section header with an explicit "None this round" rather than padding.
- **No emojis.**
- **Markdown only.** No tables, no code blocks (unless quoting a verbatim chunk the candidate provided).

## Example

The schema above is self-documenting -- each section header describes the content that belongs underneath it. When writing the first session log for a new candidate, mirror the section ordering exactly; in the body of each section, use the candidate's own framing verbatim where possible, and keep the assistant's voice for the framing/summary sections. A typical round produces a log of roughly 150-400 words.

---

## Variant: resume-ingest session log (Round 0)

Round 0 (resume ingestion -- see [resume-ingest-template.md](resume-ingest-template.md)) produces a session log with a slightly different shape than the Q&A rounds. There is no interactive Q&A in Round 0 -- the assistant parses the resume and asks one structured AskUserQuestion -- so the standard "Questions and key answers" section is replaced by a "Resume parse summary" section. Other sections collapse to "None this round" where they don't apply.

### File location

```
<output-dir>/interview-notes/<YYYY-MM-DD>-resume-ingest.md
```

### Variant schema

```markdown
# <YYYY-MM-DD> -- Resume Ingest

<One-paragraph framing: the candidate provided a resume at <path>; Round 0 parsed it into N seeded bullet files; the decision-question was asked; the candidate chose <branch>. Written in your voice, 2-3 sentences.>

## Context

- Source resume path: <relative path>
- Output directory: <relative path>
- Re-ingest flag: <true | false>
- Roles parsed: <N>
- Projects parsed: <N or "none">
- Custom sections parsed: <list of section slugs or "none">

## Working approach

<One paragraph describing what was parsed: the resume's structure (which sections existed, how roles were shaped, whether dates were present), any edge cases (PDF intake required conversion, a section was unusual, a role had no bullets in the source), and the marker line + frontmatter conventions applied to each seeded file.>

## Resume parse summary

This section replaces "Questions and key answers" for Round 0. List each parsed asset with its slug + a one-line note (typically the first bullet, or "no bullets in source").

### Roles
1. **<slug-1>** -- <Role title>, <Company> (<dates>). <First-bullet preview or "no bullets in source">.
2. **<slug-2>** -- <Role title>, <Company> (<dates>). <First-bullet preview or "no bullets in source">.
...

### Projects (if present)
- **<project-name-1>** -- <one-line description from resume>
- ...

### Skills
<One-line note: "verbatim copy of resume's Skills section saved to _skills.md (N grouped categories)" or similar.>

### Other sections (if present)
- **<section-slug-1>** -- <verbatim section name from resume>
- ...

### Summary (if the resume had one)
<Quote the resume's summary block here verbatim. This is the candidate's overall framing and is the reference for round selection.>

## Decision question and candidate's branch

**Question asked:** "Is this resume up to date, or does it need more depth on specific roles? The current role typically holds the most engram-locked detail -- the things you remember vividly but didn't write down."

**Candidate's answer:** <"Up to date" | "Needs depth on: <comma-separated role slugs>" | "Re-run Round 0">

**Branch taken:**
- *Up to date:* No Q&A rounds scheduled. Proceeding directly to draft assembly using seeded bullets.
- *Needs depth on N roles:* Scheduled N targeted rounds (one per selected role, using the Current Role round for the current role and Specific past-role deep-dive for past roles). Skipping default Career Arc / Flagship Project / Skills+Behavioral / Personal Projects rounds.
- *Re-run Round 0:* Re-posted parse summary in chat; candidate then chose <final branch>.

## Decisions

<Concrete choices made during Round 0. Typically minimal -- "lock the seeded bullets as the resume left them" / "schedule round on <role-slug> next" -- but if any unusual decisions were made during the parse (e.g., merging two role entries that the resume had as separate blocks, treating a sub-section as a custom section), record them here.>

- <Decision 1, or "None this round">
- ...

## What got cut

<Things the resume contained that were not seeded -- e.g., a deprecated section the candidate said to drop, a paragraph the assistant determined was the candidate's draft notes rather than resume content. Skip this section ("None this round") if nothing was cut.>

## Outstanding work

<Things the candidate or assistant need to follow up on. Examples: a TODO in the resume that needs resolving, a date range that came through as "unknown", a custom section that needs a clearer slug.>

- [ ] <Follow-up 1, or "None this round">

## Side notes for future sessions

<Things observed during the parse that might matter later. The candidate's resume style (terse vs. dense, quantification-heavy vs. narrative), patterns in how they framed roles, anything the assistant noticed that might inform interview rounds.>

<Free-form prose paragraph, or "None this round.">
```

### Tone for the variant

Same rules as the standard schema apply: assistant's voice in the framing sections, the candidate's framing verbatim in the parse summary. The variant log typically runs 200-500 words depending on resume length. A two-role early-career resume produces a shorter log; a ten-role senior resume produces a longer one.
