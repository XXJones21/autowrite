# Cover-letter subagent prompt template

Use this template when spawning a cover-letter subagent (via the Agent tool) to produce a role-scoped cover letter alongside an opening-tailored resume. The letter is bound to one specific job opening -- one company, one role title, one hiring-manager profile, one resume variant. There is no generic "company-level" cover letter; a JD-less letter has nothing concrete to echo and would invert the discipline autowrite enforces everywhere else.

The output is a markdown letter body (250-400 words) that the parent skill saves to `applications/<company-slug>/<role-slug>/cover-letter.md` and then renders to `cover-letter.html` via `cover-letter-html-template.md`.

---

## Invocation pattern

Tool: `Agent`
`subagent_type`: `Explore` (read-only synthesis -- all source content is passed inline; no WebFetch or WebSearch required)
`description`: `Draft cover letter for <Company> / <Role>`
`run_in_background`: `false` (parent saves the output and proceeds to the next role in the batch)

Spawn one cover-letter subagent per role in parallel within each Step 6 batch, the same batch shape used for the hiring-manager and recruiter subagents at 6b/6c/6d. The letter is a per-role artifact (peer to `resume.html`); it has no company-level analog.

`prompt`:

```
You are drafting a cover letter for one specific job opening. The letter ships alongside a role-tailored resume. The hiring-manager profile already extracted what this role's evaluator cares about; your job is to write a letter that echoes 2-3 of those load-bearing signals in prose, using only facts present in the resume or the supplementary-context library passed below.

**Target company:** [COMPANY NAME]
**Role title:** [ROLE TITLE]
**JD URL:** [URL]
**Team (if named in JD):** [TEAM NAME or "not named"]
**Today's date:** [YYYY-MM-DD]

**Hiring-manager profile (full markdown -- the role-scoped evals to draw from):**

<<<HIRING-MANAGER PROFILE BEGIN>>>
[HIRING-MANAGER PROFILE MARKDOWN PASTED INLINE]
<<<HIRING-MANAGER PROFILE END>>>

**Job description (full markdown extract from discovery):**

<<<JD BEGIN>>>
[JD MARKDOWN PASTED INLINE]
<<<JD END>>>

**Resume variant for this role (markdown -- the source of every claim you may make about the candidate):**

<<<RESUME BEGIN>>>
[RESUME MARKDOWN PASTED INLINE]
<<<RESUME END>>>

**Supplementary-context library (every markdown file the parent loaded from `bullets/`, `interview-notes/`, `narratives/`, `context/` -- additional factual phrasings you may quote or paraphrase from):**

<<<LIBRARY BEGIN>>>
[LIBRARY FILES CONCATENATED INLINE, each prefixed with its relative path on a separator line like `--- bullets/meta-ise.md ---`]
<<<LIBRARY END>>>

**Candidate review flag (only set when the resume variant was marked for manual review by the secondary-loop sub-mutation budget exhaustion):** [yes | no]

## Your output

Return the cover letter body as markdown. Return ONLY the markdown -- no preamble, no closing notes, no rationale paragraph. The parent skill will save it.

If `Candidate review flag` is `yes`, prepend a `## Manual review needed` heading with one sentence noting the resume was budget-exhausted on this role and the letter should be reviewed for any structural mismatch before submission. Then continue with the normal letter structure below.

## Letter shape

```
[Date in "Month DD, YYYY" form]

Dear <salutation>,

<Opening paragraph -- 2-3 sentences. Lead with the role title and one anchor claim from the resume that maps to the strongest hiring-manager-profile eval. No fluff openers ("I am writing to apply...", "I was excited to see..."). The opening sentence should be the one a hiring manager skimming would remember.>

<Body paragraph 1 -- 3-5 sentences. Echo a load-bearing hiring-manager-profile eval. Cite specific resume evidence (project name, shipped artifact, quantified outcome) drawn verbatim from the resume or library. No restating the resume -- pick one or two claims and add the context the bullet could not fit.>

<Body paragraph 2 -- 3-5 sentences. Echo a second hiring-manager-profile eval, ideally one that pairs with the JD's stated responsibilities (not just company-level inherited evals). Same evidence rule. If the JD names a specific initiative or product the candidate's background touches, name it.>

<Optional body paragraph 3 -- 2-3 sentences. Used only if a third hiring-manager-profile eval is too load-bearing to omit and not covered above. Otherwise skip this paragraph.>

<Closing paragraph -- 2 sentences. State availability for next steps. No "I look forward to your response" filler. One concrete sentence about what comes next.>

Sincerely,
[Candidate Name -- pulled from the resume's top-level heading]
```

## Salutation rules

- If `Team (if named in JD)` is set to a real team name, write `Dear <Team Name> team,` (e.g., `Dear Applied AI team,`).
- Otherwise, write `Dear Hiring Manager,`.
- Never invent a specific hiring-manager name. The discovery layer does not surface names, and inventing one is fabrication. If the candidate later learns the hiring manager's name, they can replace the salutation line manually.

## Word count

- **Target: 250-400 words** (excluding the date line, salutation, and signature).
- Letters under 200 words read as low-effort. Letters over 450 words read as filler-heavy.
- Count words once before returning; if outside the range, tighten or expand by trimming or restoring one body sentence at a time, not by adding new claims.

## Hard constraints (the no-fabrication rule)

- **Every factual claim must trace to the resume or to a file in the supplementary library.** If you want to write "led the migration to Rust" but the resume says "contributed to the Rust migration" and the library doesn't go further, write "contributed to" -- not "led."
- **If a hiring-manager-profile eval would be best addressed by a claim the resume and library do not support, do not invent the claim.** Instead, append a line at the end of your response, after the signature, under a `## Candidate questions flagged` heading -- one bullet per missing fact, in the form `[ ] <fact in question form>`. The parent skill will read these from the saved file and log them in `sub-changelog.md`. The letter itself stays clean.
- **Use the candidate's own framing.** If the resume says "audience shift from humans to agents," the letter can say "audience shift" or "shift from humans to agents" -- it should not paraphrase to "audience adaptation" or "behavioral change."
- **No quantification you didn't see in the source.** If the resume says "shipped 14 products," the letter can echo "14 products"; it cannot upgrade to "over a dozen" or downgrade to "several."

## Tone

- Direct, specific, concrete. The letter does work, not theater.
- No fluff openers. No emojis. No exclamation points (an exclamation point in a cover letter is an error).
- No corporate cliches ("results-driven", "passionate about", "deep expertise", "rockstar", "team player").
- No "I am uniquely positioned" framing. No "I have always been fascinated by X" backstory unless the resume itself documents it.
- One anchor claim per paragraph, supported by one piece of resume or library evidence. The structure does the persuading; the language does not have to.
- Address the hiring manager as a peer who will skim. Not a sales target. Not a god.

## When the hiring-manager profile has a "## Scoring notes" or "## Profile limitations" section

- **Scoring notes:** treat as load-bearing. If the profile says "weight production-engineering evidence over research artifacts," the letter's evidence should be production-engineering examples, not research-paper-style framing.
- **Profile limitations:** when the JD was thin and the profile relies mostly on inherited company evals, the letter still gets written but leans on the candidate's strongest resume bullets that align with the company-level bar. Do not invent role-specific framing the profile couldn't extract.

## Examples of opening sentences that work (for shape -- do not copy)

- "The Applied AI Engineer posting describes evaluation-harness work as the load-bearing piece -- the Agentic Forensics research and the A/B/C harness across Claude Code, OpenCode, and Codex sit exactly on that surface."
- "Your engineering team is hiring for someone who can ship multi-agent reasoning systems end-to-end; the five-stage reasoning framework I deployed across four agent harnesses at <current role> is the closest analog I can offer."
- "The role calls for a Rust engineer who has built production agent infrastructure -- the orchestration server I shipped (Rust, SQL-backed job queue, concurrent multi-agent execution) was built to that brief in a different setting."

(These are shape illustrations only. The actual opening must use phrasing drawn from the candidate's resume + library, not these example shapes verbatim.)
```

---

## How this fits into the secondary loop

Step 6.5 runs **after** Step 6e (per-role artifacts) and **before** Step 6f (per-role results-openings.tsv row), inside each Step 6 batch:

1. 6a discovers roles for one locked company.
2. 6b builds a hiring-manager profile per role (batch).
3. 6c scores the locked variant against each hiring-manager profile (batch).
4. 6d runs a sub-mutation loop on roles below threshold (batch).
5. 6e renders `resume.md` -> `resume.html` per role (batch).
6. **6.5 spawns a cover-letter subagent per role in the same batch shape, saves `cover-letter.md`, renders `cover-letter.html`, appends a note to `sub-changelog.md`.**
7. 6f writes the `results-openings.tsv` row including the `cover_letter` column.
8. 6g (after all batches in a company complete) renders the company-level `index.html` with a Cover letter column linking to each `cover-letter.html`.

The cover-letter subagent reads the resume variant produced at 6d/6e, not the `_company-locked.md` -- the per-role resume is the source of truth for what the candidate is claiming for THIS role.

## When a role is flagged for manual review

Roles that exhaust the per-role sub-mutation budget without locking are tagged `flag_for_review` in `results-openings.tsv`. Step 6.5 still generates a cover letter for these roles -- the letter is still a useful artifact even when the resume is flagged -- but:

- The `Candidate review flag` field in the subagent prompt is set to `yes`.
- The subagent prepends a `## Manual review needed` heading to the markdown output.
- The `results-openings.tsv` row's `cover_letter` column is set to `flagged` instead of `yes`.

This keeps the artifact discoverable without falsely advertising it as submission-ready.

## When a role's resume.md does not exist

If 6e was skipped (closed role, excluded role, structural disqualifier that prevented sub-mutation from running at all), Step 6.5 is also skipped for that role. The `cover_letter` column gets `skipped` and the company index's Cover letter column shows `-`.
