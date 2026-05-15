---
name: career-intake
description: "Interview-style intake skill that helps a candidate itemize their current role, past experience, projects, and skills through ~5 focused Q&A rounds, then synthesizes the responses into structured supplementary-context files (bullets/, interview-notes/, narratives/) that autowrite consumes downstream. Use when: build my supplementary context, interview me about my work, help me itemize my career, prepare context for autowrite, career intake. Pairs with autowrite -- this skill produces the inputs autowrite's mutation engine pulls factual phrasings from."
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
3. **Existing resume** -- Optional path to current resume markdown. If provided, the skill reads it before starting so questions skip over what's already well-documented and focus on what's missing.
4. **Target field / industry** -- Optional. Calibrates round selection (e.g., construction PM interview rounds differ from AI-engineering interview rounds). If omitted, the skill infers from the existing resume or asks neutrally about the candidate's career stage.
5. **Number of rounds** -- Default 5. The candidate can extend (round 6+) on subsequent invocations.

Read [references/session-template.md](references/session-template.md) before the first question. Read [references/interview-rounds.md](references/interview-rounds.md) to see the round catalog and pick the 5 most relevant for this candidate.

---

## step 1: introduce yourself and confirm the plan

Before the first question, post a single message:

> Career intake starting. I'll ask one question at a time across ~5 rounds; you answer in whatever depth feels natural. After each round I'll draft bullets and confirm them with you before we move on. Everything saves to disk as we go, so we can pause and resume across sessions.
>
> Rounds I'm planning for this run: [list of 5 round names selected from references/interview-rounds.md]. Let me know if you'd like to swap any of these out before we start.
>
> Round 1 topic: [topic]. Question 1: [first question].

Wait for the candidate's response. Do NOT batch questions. Do NOT ask 3 questions at once. The stream-of-consciousness approach requires the candidate's full attention on one prompt at a time.

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

**Input to career-intake:** the candidate, optionally an existing resume.
**Output of career-intake:** `interview-notes/`, `bullets/`, `narratives/`, and a `revisions/<date>-draft.md` markdown resume.
**These outputs are exactly what autowrite reads in Step 1.1** as the supplementary-context library. Running career-intake first, then autowrite, gives autowrite a much richer factual library to mutate against than a bare resume markdown could.

Recommended flow for a candidate updating their resume from scratch:

1. `/career-intake` -- 5 rounds, ~30-60 minutes of conversation, produces the bullet library and the draft.
2. Review the draft. Iterate inside career-intake if needed.
3. `/autowrite` against the draft + target companies. Autowrite uses the bullet library autonomously to optimize per-company variants without fabricating.
