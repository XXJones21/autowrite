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
