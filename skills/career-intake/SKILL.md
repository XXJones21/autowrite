---
name: career-intake
description: "Interview-style intake skill that helps a candidate itemize their current role, past experience, projects, and skills through ~5 focused Q&A rounds, then synthesizes the responses into structured supplementary-context files (bullets/, interview-notes/, narratives/) that autowrite consumes downstream. When the candidate provides an existing resume, a preflight Round 0 parses it into seeded bullet files first, then asks the candidate whether the resume is up to date or needs more depth on specific roles -- the Q&A rounds only fire on the roles the candidate flags as under-documented. Use when: build my supplementary context, interview me about my work, help me itemize my career, prepare context for autowrite, career intake. Pairs with autowrite -- this skill produces the inputs autowrite's mutation engine pulls factual phrasings from."
---

# Career Intake

Resumes get rewritten under deadline pressure with no time to remember what the candidate actually did. The bullets that end up shipping are the ones the candidate could recall in the moment -- not the ones that would have most helped them.

This skill fixes that by running a structured Q&A interview before the rewrite. The candidate answers stream-of-consciousness; the assistant captures, reflects, drafts bullets, and accumulates the result into the supplementary-context files autowrite's mutation engine can pull from when it needs specifics the resume doesn't surface.

This is a **human-in-the-loop** skill -- the opposite mode from autowrite. The assistant does not run autonomously here. Every round is a conversation with the candidate.

---

## the core job

Conduct 5 rounds of focused Q&A about the candidate's career. Each round covers one topic (current role, career arc, flagship project, skills + behavioral signals, personal projects -- adjust to the candidate). At the end of each round, draft bullets and confirm them. Save every round's output to disk before moving to the next so the work is resumable across sessions. After 5 rounds, present an updated resume draft and let the candidate decide whether to loop back for more rounds or hand off to autowrite.

**Output:** Per-round session logs (`interview-notes/<date>-<topic>.md`), itemized bullet libraries (`bullets/<topic>.md`), and an updated resume draft (`revisions/<date>-draft.md`) the candidate can hand to autowrite.

---

## before starting: gather context

Resolve these fields. If the user invocation provides them, use the provided values. Otherwise ask one at a time -- this is a conversational skill, not an autonomous one.

1. **Candidate name** -- For the session header. Required.
2. **Output directory** -- Where `interview-notes/`, `bullets/`, `narratives/`, and `revisions/` will live. Recommend the same directory the candidate's resume markdown lives in (so autowrite's co-location convention picks it up automatically). Required.
3. **Existing resume** -- Optional path to current resume markdown OR PDF. If provided, the skill runs **Round 0 (resume ingestion)** before the interactive plan -- parsing the resume into seeded `bullets/` files, then asking the candidate whether the resume is up to date or needs more depth on specific roles. The answer narrows or skips the planned Q&A rounds entirely. If omitted, the skill runs the default 5-round Q&A flow from scratch.
4. **Target field / industry** -- Optional. Calibrates round selection (e.g., construction PM interview rounds differ from AI-engineering interview rounds). If omitted, the skill infers from the existing resume or asks neutrally about the candidate's career stage.
5. **Number of rounds** -- Default 5. The candidate can extend (round 6+) on subsequent invocations. Round 0 (resume ingestion) does NOT count toward this number.
6. **Re-ingest flag** -- Default `false`. When `true`, forces Round 0 to re-parse the resume even if seeded bullets already exist in `<output-dir>/bullets/`. The re-parse overwrites ONLY the lines above the first `## From interview <date>` heading in each per-role file; interview bullets locked in earlier sessions are preserved. Use this when the resume has been edited and you want fresh seeded bullets to reflect the new content.

Read [references/session-template.md](references/session-template.md) before the first question. Read [references/interview-rounds.md](references/interview-rounds.md) to see the round catalog and pick the 5 most relevant for this candidate. **If field 3 is set, also read [references/resume-ingest-template.md](references/resume-ingest-template.md) -- it defines the Round 0 parse contract and decision-question shape.**

---

## step 1: introduce yourself and confirm the plan

Before the first question, post a single message. The message has two forks depending on whether the candidate provided an existing resume in the gather-context step:

**Fork A -- candidate provided a resume (Round 0 will fire):**

> Career intake starting. You provided an existing resume at `<path>`, so I'll begin with **Round 0 (resume ingestion)** -- I'll parse the resume into a seed knowledge base (one bullets file per role, plus skills and projects), then ask you whether the resume is up to date or whether specific roles need more depth. Round 0 doesn't ask Q&A questions; it just sets up the seed and asks one structured decision question.
>
> After Round 0, we'll branch:
> - If you say "up to date" -- I'll assemble the draft from the seeded bullets and hand off. No Q&A rounds.
> - If you say "needs depth on N roles" -- I'll narrow the planned rounds to those roles only (the current role typically holds the most engram-locked detail) and we'll do one Q&A round per selected role, one question at a time.
>
> Everything saves to disk as we go, so we can pause and resume across sessions. Starting Round 0 now.

Then proceed to Step 1.5. Do not list a planned 5-round set yet; Round 0's decision question drives the set.

**Fork B -- no resume provided (default 5-round flow):**

> Career intake starting. I'll ask one question at a time across ~5 rounds; you answer in whatever depth feels natural. After each round I'll draft bullets and confirm them with you before we move on. Everything saves to disk as we go, so we can pause and resume across sessions.
>
> Rounds I'm planning for this run: [list of 5 round names selected from references/interview-rounds.md]. Let me know if you'd like to swap any of these out before we start.
>
> Round 1 topic: [topic]. Question 1: [first question].

Wait for the candidate's response. Do NOT batch questions. Do NOT ask 3 questions at once. The stream-of-consciousness approach requires the candidate's full attention on one prompt at a time.

---

## step 1.5: Round 0 -- resume ingestion (only if the candidate provided a resume)

Skip this step if no resume was provided in the gather-context step. Otherwise:

The full Round 0 parse contract, output file shapes, marker-line convention, decision-question phrasing, and branching logic live in [references/resume-ingest-template.md](references/resume-ingest-template.md). Read it before running this step.

The step at a glance:

### 1.5a. Detect prior Round 0 state

Check `<output-dir>/bullets/` for files containing the marker line `<!-- career-intake:round-0-seed -->`. If any are found AND `re_ingest: false` (the default):

- **Skip the parse.** Announce: "Seeded bullets from a prior Round 0 detected at `<paths>`. Skipping re-ingestion. If the resume changed and you want to re-seed, re-invoke with `re_ingest: true`."
- Jump to step 1.5d (decision question) -- the candidate still gets to decide whether the existing seeded bullets need any depth rounds, or if the prior session already covered everything.

If no prior seed exists OR `re_ingest: true`:

- Proceed to step 1.5b.

### 1.5b. Convert the resume if needed and parse it

If the resume path ends in `.pdf`, run the PDF intake described in the autowrite skill's Step 1.0 (read the PDF, convert to markdown, save the converted markdown alongside the PDF -- never modify the PDF). Use the converted markdown for the rest of Round 0.

Then parse the resume markdown per the contract in [references/resume-ingest-template.md](references/resume-ingest-template.md):

- Roles list (one entry per role from the experience section, each with title + company + dates + slug + `current_role` flag).
- Projects list (entries from the Projects / Personal Projects section, if present).
- Skills section (verbatim).
- Education section (verbatim, if present).
- Custom sections (Patents, Press, Talks, Certifications, etc.) -- one entry per non-standard section.
- Summary block (if the resume has one) -- captured into the session log, NOT written as a `bullets/` file.

### 1.5c. Write the seeded files

Create (or overwrite per the `re_ingest` rules) the following:

```
<output-dir>/
  bullets/
    <role-slug-1>.md            # one per role
    <role-slug-2>.md
    ...
    _skills.md
    _projects.md                # absent if no Projects section
    _education.md               # absent if no Education section
    _<custom-section-slug>.md   # one per non-standard section
  interview-notes/
    <YYYY-MM-DD>-resume-ingest.md
```

Each `bullets/` file starts with the marker line `<!-- career-intake:round-0-seed -->`, followed by YAML frontmatter, then the verbatim section content. The per-role file's frontmatter includes `role_title`, `company`, `dates`, `slug`, `current_role`, `seeded_from`, `seeded_at`. The full file shape and constraints are in `references/resume-ingest-template.md`.

The `interview-notes/<date>-resume-ingest.md` session log follows the **resume-ingest variant** in [references/session-template.md](references/session-template.md) -- the "Questions and key answers" section is replaced by "Resume parse summary" listing each parsed asset with its slug + first-bullet preview.

Announce in chat:

> Round 0 complete. Parsed N roles, P projects, S custom sections. Seeded files at `<output-dir>/bullets/` and `<output-dir>/interview-notes/<date>-resume-ingest.md`. Now -- one question before I plan the Q&A rounds.

### 1.5d. Ask the decision question

Use `AskUserQuestion` with the shape defined in `references/resume-ingest-template.md`:

- Question: "I've parsed your resume into a starting knowledge base (N roles, P projects, S custom sections). Is this resume up to date, or does it need more depth on specific roles? The current role typically holds the most engram-locked detail -- the things you remember vividly but didn't write down."
- Header: "Resume depth"
- Options: 1) "Up to date -- finalize draft from seeded bullets" 2) "Needs depth on these roles" 3) "Re-run Round 0 -- I'd like to see what was parsed first"

Wait for the candidate's answer. Do not proceed until they have chosen.

### 1.5e. Branch on the candidate's answer

- **"Up to date":** Announce "Marking the resume as up-to-date. Skipping Q&A rounds. Assembling the draft now." Jump directly to **Step 3** (generate a draft), but assemble the draft from the seeded `bullets/` files instead of from interview-driven rounds. The resulting `revisions/<YYYY-MM-DD>-draft.md` is effectively a verbatim copy of the original resume, but uniformly placed under `revisions/` so the hand-off path to autowrite is identical to the Q&A path. Then go to **Step 4**, but present only the revise-current-draft and hand-off-to-autowrite options (the loop-back option is omitted since no Q&A rounds ran -- the candidate can still re-enter the skill later to add rounds).

- **"Needs depth on N roles":** Present a multi-select follow-up listing the parsed role titles (with "Other (specify)" available for roles that didn't appear in the resume's experience section, e.g., a side-project lead). Wait for selections. Then schedule the targeted rounds:
  - Current role selected -> include the "Current role" round from `references/interview-rounds.md`.
  - Past role selected -> include the "Specific past-role deep-dive" round, one per selected past role.
  - Multiple selections -> N rounds, one per role.
  - Skip the default Career Arc / Flagship Project / Skills+Behavioral / Personal Projects rounds; the candidate can add them later via Step 4's loop-back option after the targeted rounds complete.

  Announce: "Scheduled N rounds based on your depth selections: <list>. Starting round 1 now." Then proceed to **Step 2** with the narrowed round set.

- **"Re-run Round 0":** Post a chat message with a parse summary (role list + slugs + first-bullet previews, project list, custom-section list). Then re-ask the decision question with options 1 and 2 only (option 3 is dropped to prevent loops). Branch on the new answer.

### 1.5f. Per-role bullet append rule for later Q&A rounds

When a Q&A round (e.g., "Current role") locks bullets for a role whose seeded bullets file already exists, **append** the new bullets to the existing file under a dated subheading rather than overwriting:

```markdown
<!-- career-intake:round-0-seed -->
---
... (frontmatter unchanged)
---

# <Role title> -- <Company> (<dates>)

<Seeded bullets from the resume -- preserved verbatim>

## From interview <YYYY-MM-DD>

<New bullets locked at the end of this Q&A round>
```

The seeded bullets remain as a fallback layer; interview bullets are the higher-fidelity layer above them. If multiple Q&A rounds run against the same role on different dates, append additional `## From interview <date>` blocks chronologically -- never overwrite an earlier interview block.

If a Q&A round runs against a role that does NOT have a seeded file (the candidate flagged it via "Other (specify)" because it wasn't in the resume), create the file fresh with the marker line, frontmatter set to `seeded_from: <none -- added via Round X Q&A on YYYY-MM-DD>`, no body bullets above the interview heading, and the `## From interview` block holding the locked bullets.

---

## step 2: conduct each round

Each round is structured as:

### 2a. Open with one targeted question

Pick the most load-bearing question for the round's topic. Examples by round:

- **Current role:** "Walk me through your single biggest project in your current role. Treat me like a peer who knows the industry but doesn't know your team -- start anywhere."
- **Career arc:** "Tell me how you got from your earliest professional work to today, hitting only the turning points. I'll fill in details with follow-up questions."
- **Flagship project:** "Pick one project from your career you'd most want a hiring manager to know about. Tell me what it was, what you did on it, and what changed because of it."
- **Skills + behavioral signals:** "What's something about how you work that recruiters would never figure out from a resume bullet but matters?"
- **Personal projects:** "Walk me through anything you've built outside of paid work -- side projects, public repos, hobby tools. Include the ones that aren't done."

The question shape matters: it should invite a long, unstructured response, not a yes/no or a single-fact answer.

### 2b. Follow up two or three times

After each candidate response, ask one specific follow-up. The follow-up should:

- Probe a specific concrete claim the candidate just made
- Surface quantification ("how many people", "over what timeframe", "what before vs. after")
- Surface unusual decisions or tradeoffs ("why did you go with X instead of Y?")
- Surface the non-obvious throughline ("what's the skill you used here that you also used in your last role?")

Stop following up when:
- The candidate's answers start repeating
- They explicitly say "I think that's everything on this"
- Three follow-ups have been asked

### 2c. Reflect back and draft bullets

After the round's questions close, post:

> Let me reflect what I heard. [2-3 sentence synthesis in the candidate's own framing.] Here are draft bullets:
>
> - [bullet 1, using candidate's exact wording where possible, with quantification where the candidate gave it]
> - [bullet 2]
> - [bullet 3-5 typical]
>
> Tell me what's wrong, what's missing, or what's overclaimed. I'll revise before saving.

The drafting rules are strict:

- **Use the candidate's exact phrasing for verbs and noun phrases.** "Drove partner teams from human-in-the-loop to human-on-the-loop" is the candidate's framing -- preserve it. Don't paraphrase to "Improved AI workflow adoption."
- **Include quantification only where the candidate gave it.** "14 products in 5 months mostly solo" is quantification the candidate provided. "Many products shipped" is filler -- skip it.
- **Skip generic resume verbs** ("leveraged", "spearheaded", "drove cross-functional alignment") unless the candidate used them.
- **Flag underclaims and overclaims.** If the candidate seemed to downplay a 50k-user product, flag it ("you mentioned 50k MAU almost in passing -- this is significant; should we surface it?"). If they overstated something, flag it ("you said 'replaced' but earlier you said the old system still runs in parallel -- want to soften to 'parallel implementation'?").

### 2d. Iterate on bullets until the candidate signals lock

The candidate corrects, you revise, repeat. When the candidate says some variant of "yes, that's right" or "looks good", lock the round.

### 2e. Save the round's artifacts

Before moving to the next round, save:

1. **Session log** at `<output-dir>/interview-notes/<YYYY-MM-DD>-<round-topic-slug>.md` following the schema in [references/session-template.md](references/session-template.md). Include the questions asked, key answers, decisions, anything the candidate said that's worth keeping for future interview prep ("side notes" section).
2. **Bullet library** at `<output-dir>/bullets/<round-topic-slug>.md` -- just the locked bullets in clean markdown, no Q&A scaffolding.

Announce in chat: "Round [N] locked. Saved session log to `<path>` and bullets to `<path>`. Moving to round [N+1]: [topic]."

---

## step 3: after 5 rounds, generate a draft

When the planned rounds are all locked, post:

> Five rounds done. Here's a quick stitch of what we have:
>
> - [bullet 1 from round 1 with file source]
> - [bullet 2 from round 2 with file source]
> - ...
>
> I'll now assemble these into an updated resume draft. This may take a moment.

Then assemble a draft markdown resume at `<output-dir>/revisions/<YYYY-MM-DD>-draft.md`. Pull from:

- `bullets/<round-topic-slug>.md` for each locked round
- The existing resume markdown (if provided in the context-gathering step) for sections the rounds did not touch (education, older roles, contact info)
- The candidate's own framing for the Summary -- written from the throughline that surfaced across rounds, not from a generic template

Announce in chat with the draft path and a one-paragraph "what changed" note: which rounds contributed which new bullets, which old sections were preserved as-is, and any TODOs flagged for the candidate to resolve before publishing.

---

## step 4: loop or hand off

After the draft is presented, ask the candidate:

> Three options for next steps:
>
> 1. **Loop back for more rounds.** I have additional round templates -- leadership, education, behavioral signals, specific past role deep-dives -- in `references/interview-rounds.md`. Pick a topic and we'll do another round.
> 2. **Revise the current draft.** Tell me what's off and I'll iterate on specific bullets or sections.
> 3. **Hand off to autowrite.** Invoke autowrite against `<output-dir>/revisions/<YYYY-MM-DD>-draft.md`. It'll auto-load the `bullets/` and `interview-notes/` we just built and use them as the factual library when proposing per-company mutations.

Honor whichever path the candidate picks. There is no autonomous default here -- this is a human-in-the-loop skill.

---

## the test

A good career-intake run:

1. **Asked one question at a time.** No batched questions. Stream-of-consciousness pacing throughout.
2. **Used the candidate's framing.** Drafted bullets in the candidate's verbs and noun phrases. Did not paraphrase to generic resume-speak.
3. **Saved incrementally.** Every round saved its session log + bullets before moving on. The candidate could close the session at any point and resume.
4. **Flagged under- and over-claims.** Surfaced things the candidate downplayed; softened things the candidate may have overstated.
5. **Produced a draft, not a final.** The output is a candidate-reviewable draft. The handoff to autowrite is where the per-company optimization happens.
6. **Loopable.** The candidate could come back tomorrow, run again, and add a round 6 on a topic they remembered later.

If the bullets at the end read more like the assistant than the candidate -- the framing got lost. Re-read the session logs and revise.

---

## how this connects to autowrite

**Input to career-intake:** the candidate, optionally an existing resume (markdown or PDF).
**Output of career-intake:** `interview-notes/`, `bullets/`, `narratives/`, and a `revisions/<date>-draft.md` markdown resume.
**These outputs are exactly what autowrite reads in Step 1.1** as the supplementary-context library. Running career-intake first, then autowrite, gives autowrite a much richer factual library to mutate against than a bare resume markdown could.

The output shape is **identical** whether the candidate ran Round 0 + Q&A, Round 0 only (up-to-date branch), or the default 5-round flow with no resume. The same `bullets/` files exist in the same locations with the same shapes -- the only difference is whether the bullets came from the resume seed, from interview rounds, or both (with interview bullets appended under `## From interview <date>` subheadings). Autowrite Step 1.1 needs no changes to consume any of these flows; it globs `bullets/*.md` and reads each file's content regardless of provenance.

Recommended flows:

**Candidate has an existing resume in decent shape (most common):**
1. `/career-intake` with the resume path -- Round 0 parses it; the candidate answers "up to date" -- draft assembled in seconds. No Q&A.
2. `/autowrite` against the draft + target companies.

**Candidate has an existing resume but the current role is under-documented:**
1. `/career-intake` with the resume path -- Round 0 parses it; the candidate answers "needs depth on current role" -- one targeted Q&A round runs, appending fresh bullets under `## From interview <date>` in the current-role file.
2. Review the draft. Add more rounds via Step 4's loop-back if needed.
3. `/autowrite` against the draft + target companies.

**Candidate has no existing resume:**
1. `/career-intake` with no resume -- the default 5-round Q&A flow runs (Career Arc / Current Role / Flagship Project / Skills+Behavioral / Personal Projects), ~30-60 minutes of conversation, produces the bullet library and the draft from scratch.
2. Review the draft. Iterate inside career-intake if needed.
3. `/autowrite` against the draft + target companies.

In all three flows, autowrite uses the bullet library autonomously to optimize per-company variants without fabricating.
