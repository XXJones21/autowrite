# Interview rounds catalog

A library of round templates the career-intake skill can pick from. The default 5-round run picks the most load-bearing rounds for the candidate's situation; this file is the menu.

Each round entry has: a topic name, a short purpose statement, an opening question (the one that invites the longest, most useful response), 2-3 follow-up question shapes, and notes on when to use the round vs. skip it.

---

## Preflight rounds (run before the default 5-round set when applicable)

### Round 0: Resume ingestion

**Purpose:** When the candidate provides an existing resume, parse it into seeded `bullets/<role-slug>.md` files (plus `_skills.md`, `_projects.md`, custom-section files) and a `interview-notes/<date>-resume-ingest.md` session log. Then ask the candidate whether the resume is up to date or needs more depth on specific roles. The answer narrows -- or skips -- the planned Q&A rounds.

**Parse contract and decision-question shape:** see [resume-ingest-template.md](resume-ingest-template.md). The full ingestion + branching logic lives there; this entry is a pointer.

**When to use:** Any time the user invokes `/career-intake` AND provides an existing resume (gather-context field 3). Round 0 fires automatically before the round-selection step.

**When to skip:** No resume provided. Skip Round 0 entirely and proceed with the existing 5-round Q&A flow.

**How it interacts with the default 5-round set:**

- **If the candidate answers "up to date":** the default 5-round set is dropped entirely. The skill jumps to draft assembly using only the seeded bullets, then offers the Step 4 hand-off options (minus the loop-back, since no rounds ran).
- **If the candidate answers "needs depth" on N roles:** the default 5-round set is **replaced** by N targeted rounds, one per selected role. Use the "Current role" round for the current role and the "Specific past-role deep-dive" round for past roles. The Career Arc / Flagship Project / Skills+Behavioral / Personal Projects rounds become optional add-ons that the candidate can request via Step 4's loop-back option after the targeted rounds complete.
- **If the candidate answers "re-run Round 0":** the parse summary is reposted in chat for review, then the decision question is re-asked with options 1 and 2 only.

**Re-invocation behavior:** if `<output-dir>/bullets/` already contains seeded files from a prior Round 0 (detected via the `<!-- career-intake:round-0-seed -->` marker line), Round 0 is skipped on re-invocation and the skill picks up at round selection. The user can force a re-parse with `re_ingest: true`; this overwrites only the lines above the first `## From interview` heading in each per-role file, preserving any interview bullets locked in earlier sessions.

**Output:** seeded `bullets/` files, a single `interview-notes/<date>-resume-ingest.md` session log following the resume-ingest variant in [session-template.md](session-template.md), and an in-memory `roles[]` list that drives the depth-needed multi-select.

**When the resume itself is a PDF:** convert via the PDF-intake step (mirrors autowrite's Step 1.0 -- see `../../autowrite/SKILL.md` Step 1.0). The original PDF is never modified; the converted markdown is saved alongside it. Downstream Round 0 logic operates on the markdown.

---

## Core rounds (run at least 4 of these in the default 5-round set)

### Round: Current role

**Purpose:** Surface what the candidate is doing right now in enough detail that bullets can be drafted from it. Almost always the most load-bearing round.

**Opening question:** "Walk me through your single biggest project in your current role. Treat me like a peer who knows the industry but doesn't know your team -- start anywhere."

**Follow-ups:**
- "Who else was involved, and what was your specific role on it vs. theirs?"
- "What does success look like for this work, and how do you know when you've hit it?"
- "What's the part of this work you'd be most disappointed if it didn't show up on the resume?"

**When to skip:** Almost never. Skip only if the candidate just started a role (under ~2 months) and has nothing shipped yet -- in that case substitute the "Most recent shipped work" round.

---

### Round: Career arc

**Purpose:** Map the throughline from earliest professional work to today. Identify the throughline skill that recruiters and hiring managers will care about more than any individual title.

**Opening question:** "Tell me how you got from your earliest professional work to today, hitting only the turning points. I'll fill in details with follow-up questions."

**Follow-ups:**
- "What's a skill you used in role [X earlier in the arc] that you still use today, just applied to a different audience or domain?"
- "If you had to summarize your career in one sentence -- the throughline a recruiter should walk away with -- what would it be?"
- "Was there a role you took that didn't fit the throughline at the time? How do you think about it now?"

**When to use:** Always include if the candidate has 5+ years of experience OR if their current role title doesn't obviously map to where their experience came from (career-switchers, technical-to-management pivots, T-shaped backgrounds).

**When to skip:** Very early-career candidates with one or two roles -- the arc is too short to land insights.

---

### Round: Flagship project

**Purpose:** Pick the single project the candidate would most want a hiring manager to know about, and itemize it to a depth that supports both resume bullets and interview answers.

**Opening question:** "Pick one project from your career you'd most want a hiring manager to know about. Tell me what it was, what you did on it, and what changed because of it."

**Follow-ups:**
- "What did you decide to NOT do on this project that someone else might have done? Why?"
- "What was the outcome -- not just the deliverable, but what changed for the people who used it?"
- "What's the part of this you wish more people knew about?"

**When to use:** Always. Even if the candidate already covered a flagship in the Current Role round, this round forces them to pick across their whole career, which often surfaces a different one.

---

### Round: Skills and behavioral signals

**Purpose:** Capture how the candidate works, not just what they've done. The things that don't fit bullet form but matter to interview prep and culture-fit screening.

**Opening question:** "What's something about how you work that recruiters would never figure out from a resume bullet but matters?"

**Follow-ups:**
- "What kind of work do you actively avoid, and why?"
- "What's a feedback loop you've gotten from teammates more than once -- positive or critical?"
- "What's a tool or technique you'd recommend to anyone in your role, even if it's not on most lists?"

**When to use:** Always for senior candidates (signals are load-bearing for hiring managers). Optional for early-career (they may not have enough patterns yet).

---

### Round: Personal projects and outside-work signals

**Purpose:** Cover side projects, public repos, hobby tools, writing, talks, open-source contributions, or other artifacts the candidate produced outside of paid work. These are often the strongest evidence of self-directed capability.

**Opening question:** "Walk me through anything you've built outside of paid work -- side projects, public repos, hobby tools. Include the ones that aren't done."

**Follow-ups:**
- "Why did you start [project X]? What problem was it solving for you personally?"
- "Are any of these public? Do you want a hiring manager to find them?"
- "Is there a side project where the skill or insight ended up bleeding back into your day job?"

**When to use:** Almost always. Even candidates who think they have nothing here often surface a useful artifact (a repo, a Substack, a recurring presentation).

**When to skip:** Only when the candidate explicitly has no outside-work artifacts and isn't comfortable manufacturing them for the resume. Honor that.

---

## Supplementary rounds (use as round 6+ or substitute for core rounds when relevant)

### Round: Leadership and people management

**Opening question:** "Tell me about a time you owned the outcome for work that you didn't personally do all of. Who did the work? What did 'ownership' mean in practice?"

**Follow-ups:** size of team, span of control, specific person they helped grow, specific decision they made about staffing or scope.

**When to use:** Candidates targeting Senior+ / Staff+ / management roles, or whose work is meaningfully cross-functional even at IC level.

---

### Round: Specific past-role deep-dive

**Opening question:** "Tell me about your work at [previous company]. Same shape as the Current Role round, but for a role you've already left."

**When to use:** When a specific past role keeps coming up in other rounds and needs its own focused treatment. Common when the past role is more prestigious or recognizable than the current one.

---

### Round: Education and credentials

**Opening question:** "Walk me through your formal education and any credentials -- degrees, certifications, programs. Skip the things that don't matter; lead with the ones that do."

**Follow-ups:** transcripts vs. degree completion, capstone projects, professors or programs the candidate would name-drop in interview, certifications that are load-bearing for the target field.

**When to use:** Candidates with non-standard education paths (incomplete degree, bootcamp, vocational program, transfer credits, abroad). Skip for candidates whose degree is conventional and recent.

---

### Round: Specific technical capability

**Opening question:** "Tell me about your [LLM evaluation / structural engineering / cinematic compositing / etc.] work specifically. I want depth on this one capability, not breadth."

**Follow-ups:** specific tools and versions, specific decisions about technique, specific things the candidate's approach does differently than the default.

**When to use:** When a target role's hiring bar centers on one specific technical capability the candidate has worked on. Often paired with the Flagship Project round.

---

### Round: Field-specific or industry-specific

**Opening question:** depends on the field. Examples:
- *Construction PM:* "Tell me about the most complex project you sequenced. How did you handle the trade dependencies and the timeline risks?"
- *Creative producer:* "Walk me through a delivery that almost didn't make it. What did you do?"
- *Sales engineering:* "Tell me about a deal where the technical question was the load-bearing question -- not pricing, not relationship, just whether the thing would actually work for them."

**When to use:** When standard rounds don't capture the rhythm of the candidate's field. Build a custom opening question that matches how their industry talks about work.

---

## Round selection guidance for the default 5-round set

Given a candidate who provided a resume AND just ran Round 0:

The candidate's answer to the Round 0 decision question drives selection. The default-5 heuristic below does NOT apply -- Round 0 has already narrowed (or eliminated) the set:

- **Answered "up to date":** no rounds run. Jump straight to draft assembly.
- **Answered "needs depth on N roles":** run N targeted rounds, one per selected role. Use the "Current role" round for the current role and "Specific past-role deep-dive" for past roles. Skip Career Arc / Flagship Project / Skills+Behavioral / Personal Projects unless the candidate explicitly adds them via Step 4's loop-back option after the targeted rounds complete.
- **Answered "re-run Round 0":** re-enter Round 0 with options 1 and 2 only.

The point of Round 0 is to avoid running rounds the seeded bullets already cover. Do not pad the round set "for completeness" -- if the candidate said one role needs depth, run that one round and hand off to draft assembly.

Given a candidate who provided a resume BUT skipped Round 0 (e.g., `re_ingest: false` and seeded bullets already exist from a prior session) OR with NO existing resume:

The Round 0 narrowing does not apply. Use the heuristics below.

**With existing resume (Round 0 skipped on re-invocation):**

1. Read the existing resume and the seeded bullets.
2. Identify which sections feel thinly-detailed or generically written -- those become priority rounds (often Current Role and Flagship Project).
3. Identify cross-cutting throughlines that aren't explicit -- those go in the Career Arc round.
4. Pick Skills/Behavioral and Personal Projects as the rounds that most resumes underdocument.
5. The 5th slot floats based on the candidate's situation: leadership for senior candidates, a specific past-role for career-switchers, education for non-standard paths, a field-specific round for specialists.

**With NO existing resume:**

1. Lead with Career Arc to build the spine.
2. Current Role for the most-recent reference point.
3. Flagship Project to anchor the strongest single story.
4. Skills/Behavioral to capture working style.
5. Personal Projects to surface outside-work signals.

The default 5-round set should always feel coherent -- if a round overlaps heavily with another already-planned round, swap it out for one of the supplementary rounds.
