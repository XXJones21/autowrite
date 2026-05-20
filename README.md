# Autowrite

A Claude Code plugin that autonomously improves a resume by spinning up company-specific recruiter subagents, scoring the resume against binary hiring evals, mutating one line at a time, and converging across multiple target companies in parallel.

Modeled on Andrej Karpathy's autoresearch methodology, adapted from skill-prompt optimization to resume content.

---

## What it does

You give autowrite a resume markdown file and a list of target companies. It runs a two-stage autonomous loop -- expect an hour or more for a full multi-company end-to-end run.

### Stage 1: Primary loop (per-company convergence)

1. For each company, it **researches** the hiring profile on first run (using WebSearch and WebFetch against careers pages, engineering blogs, public statements from leadership, recent product launches). Profiles cache to disk and reuse.
2. Each profile contains 6-12 **binary yes/no eval criteria** specific to that company's bar.
3. autowrite spawns one **recruiter subagent per company in parallel**, each scoring the resume against its profile's evals.
4. **Profile-overalignment safeguard:** if you target only one company, autowrite automatically adds a triangulation profile to detect false 100% baselines (a real failure mode from production -- a single research subagent can produce evals that align too closely with the resume's own language).
5. The mutation loop mutates **one line of the resume at a time** to address cross-profile gaps. Improvements are kept; non-improvements are reverted.
6. **Per-profile lock:** when a company's profile holds at ≥90% pass rate for 3 consecutive experiments, that variant **LOCKS**. autowrite saves it as `applications/<company>/_company-locked.md` and removes that profile from the active mutation pool. The loop continues against un-locked profiles.
7. Different companies have divergent bars -- so the output is per-company resume variants, not a single one-size-fits-all resume.

### Stage 2: Secondary loop (per-opening tailoring)

For each locked company:

1. A **job-openings investigator** subagent discovers currently-open roles at that company (discovery only -- no scoring, to avoid bias).
2. For each role: a **hiring-manager profile** subagent builds a role-scoped profile that blends company-bar evals with JD-specific evals.
3. A recruiter subagent scores the locked company variant against the hiring-manager profile.
4. If the score is below the lock threshold, a per-role sub-mutation loop runs against the hiring-manager profile until it locks or the per-role budget exhausts.
5. A **cover-letter subagent** drafts a 250-400 word role-scoped letter that echoes 2-3 of the hiring-manager-profile evals in prose, anchoring every claim to the resume or supplementary-context library (no fabrication; any missing facts surface as candidate questions in the role's `sub-changelog.md`).
6. Output per role: a `resume.md` AND a `cover-letter.md` (plus print-ready `.html` siblings), ready to submit as a job application.

### Outputs

- Working primary-loop tree with mutation history (`autowrite-<resume-slug>/`)
- Profile cache (`profiles/`)
- Applications tree (`applications/<company>/<role>/`) containing the submission set per opening: `resume.md` + `resume.html` (print-ready resume) and `cover-letter.md` + `cover-letter.html` (print-ready role-scoped cover letter) -- open each HTML file in a browser, Ctrl+P -> Save as PDF
- Company-level navigation pages (`applications/<company>/index.html`) listing every discovered opening with active-status tags, final scores, and direct links to the print-ready resume + cover letter pair
- Live HTML dashboard with a top-of-page TOC linking to per-company index pages and each locked variant's HTML; per-profile score lanes and per-company role breakdowns underneath
- Full discovery audit trail: `openings-<YYYY-MM-DD>.json` (machine-readable) and `openings-<YYYY-MM-DD>.md` (scannable) showing every role the discovery subagent considered, including roles tagged closed, excluded, or unverified -- nothing is dropped silently
- changelog.md (primary loop) and sub-changelog.md (per role, including a `## Cover letter generated` block recording which evals each letter echoed) -- causal logs of every mutation for interview prep

**The original resume is never modified.** Mutations happen on working copies. The user reviews, diffs, and manually decides whether to apply changes.

---

## What it does NOT do

- Send your resume to anyone. Everything runs locally on your machine.
- Pretend a resume passes evals it doesn't. The point is to find the gaps, not paper over them.
- Add fabricated content. If a recruiter subagent suggests a capability the resume should claim, you decide whether that's true and add it yourself -- autowrite proposes mutations, you approve them in the loop's keep/discard logic, but you remain accountable for accuracy.
- Replace human judgment. The mutation loop optimizes for what the recruiter subagents detect. Your hiring manager will see things subagents can't. Treat autowrite as a sparring partner, not an oracle.

---

## Installation

This is a Claude Code plugin. It lives at `~/.claude/plugins/autowrite/` (or `%USERPROFILE%\.claude\plugins\autowrite\` on Windows). After placing or cloning the directory there, Claude Code picks it up on next launch.

Quickest path -- clone directly into the plugin directory:

```
# macOS / Linux
git clone https://github.com/<your-username>/autowrite ~/.claude/plugins/autowrite

# Windows (PowerShell)
git clone https://github.com/<your-username>/autowrite "$env:USERPROFILE\.claude\plugins\autowrite"
```

Or install manually (if you downloaded a zip):

```
# macOS / Linux
mkdir -p ~/.claude/plugins
# place the autowrite directory inside ~/.claude/plugins/

# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude\plugins"
# place the autowrite directory inside %USERPROFILE%\.claude\plugins\
```

The plugin should resolve to:

```
~/.claude/plugins/autowrite/
  .claude-plugin/
    plugin.json
  README.md
  skills/
    autowrite/
      SKILL.md
      references/
        eval-guide.md
        profile-template.md
        recruiter-subagent-prompt.md
        research-subagent-prompt.md
        job-openings-subagent-prompt.md          # v0.3+
        hiring-manager-subagent-prompt.md        # v0.3+
        resume-html-template.md                  # v0.4+
        cover-letter-subagent-prompt.md          # v0.6+
        cover-letter-html-template.md            # v0.6+
    career-intake/                               # v0.5+
      SKILL.md
      references/
        session-template.md
        interview-rounds.md
        resume-ingest-template.md                # v0.6+
```

The plugin ships two skills. `autowrite` is the autonomous evaluator + mutator (and, as of v0.6, the cover-letter generator). `career-intake` is a human-in-the-loop interview skill that builds the supplementary-context library `autowrite` reads from; v0.6 added a preflight **Round 0** that parses an existing resume into seeded bullet files first, then asks whether specific roles need deeper Q&A -- so candidates whose resume is already in decent shape skip the full 5-round interview entirely. Recommended flow for a fresh resume update: run `/career-intake` first with your existing resume, decide whether Round 0's seed is enough or whether the current role needs depth, then `/autowrite` against the resulting draft.

After installing, **restart Claude Code** so the plugin registry picks up the new skill.

---

## Usage

Once installed and Claude Code has been restarted, invoke the skill in any Claude Code session:

> /autowrite

or in natural language:

> Run autowrite on `~/path/to/resume.md` for <Company A>, <Company B>, and <Company C>.

(Examples: "for Anthropic, OpenAI, and Google DeepMind" for an AI-engineering search; "for Turner Construction, Skanska, and Mortenson" for a construction-management search; "for Riot, Insomniac, and Bungie" for a game-development search. The pattern is the same; only the targets change.)

The skill enters its STOP-and-confirm gate before running anything (mirrored from autoresearch). It will ask:

1. **Target resume.** Path to a `.md` or `.pdf` file. If you pass a PDF, autowrite converts it to markdown as Step 1.0 (the original PDF is never modified) and saves the converted file alongside it. Markdown is the canonical working format -- the loop operates on it from that point forward.
2. **Target companies.** One or more, optionally qualified by role (examples: `"Anthropic / AI Engineer"`, `"Turner Construction / Senior Project Manager"`, `"Riot Games / Gameplay Engineer"`). Recommend 2-4 targets for a meaningful aggregate.
3. **Runs per experiment.** Default 1. Bump to 3 if you see eval results flip between runs without resume changes.
4. **Budget cap.** Optional. Default: no cap (runs until convergence).
5. **Profile refresh.** Default: use cache if available. Set to `true` to force re-research even when a cached profile exists.

Once you confirm, the loop runs autonomously. The dashboard opens in your browser; you can walk away.

---

## How company research works

When autowrite encounters a target company with no cached profile (or with `profile_refresh: true`), it spawns a research subagent that:

1. Uses **WebSearch** to find the company's careers / engineering / culture pages.
2. Uses **WebFetch** to read the most signal-dense URLs: job postings, "how we hire" content, engineering blog posts from the last ~12 months, public statements from leadership.
3. Synthesizes the findings into a profile markdown file containing:
   - Hiring values
   - Technical bar
   - Recent strategic priorities (last ~6 months)
   - Anti-patterns / red flags
   - **6-12 binary eval criteria** tied to specific public signals (each with a `Source:` line citing where the criterion came from)
4. Saves the profile to `<resume-parent-dir>/profiles/<slug>.md` -- co-located with the resume, not in the plugin tree. This sidesteps harness write-restrictions on `~/.claude/` and keeps profile caches travelling with the resume they were researched against.

The skill validates each profile before using it -- all sections populated, 6-12 evals, every eval binary and clearly company-specific (no generic checks that could appear in any company's profile), every eval cited. If validation fails, the research subagent runs again with explicit feedback.

**Profiles cache for ~3 months.** After that, refresh them -- companies' strategic priorities shift, especially in fast-moving fields. You can also delete a profile file at any time to force a re-research.

You can also **hand-author profiles** if you want. Follow the schema in `skills/autowrite/references/profile-template.md` and drop the file into `<resume-parent-dir>/profiles/`. The skill will load it the same way as a researched one.

---

## How the recruiter eval works

For each profile (cached or freshly researched), autowrite spawns a **recruiter subagent in parallel** (single message, multiple Agent tool calls -- they run concurrently, not serially). Each subagent receives:

- The full resume markdown content
- The full profile markdown content

It assists a senior recruiter at the target company, scoring the resume against the profile's binary evals only -- it does not invent new criteria. It returns a structured JSON-shaped report with:

- Per-eval pass/fail and evidence
- Pass count and pass rate
- Top 3 strengths
- Top 3 gaps (prioritized by impact at this company)
- Single highest-priority revision suggestion (specific section, specific bullet, specific swap)
- Optional evaluator notes (eval ambiguity, scoring confidence, etc.)

The skill aggregates these reports, identifies the most-shared gap across profiles, and proposes the next mutation.

---

## Outputs

After a run, you'll find these artifacts in `<resume-directory>/autowrite-<resume-slug>/`:

```
autowrite-<resume-slug>/
  dashboard.html                   # live dashboard, auto-refreshes every 10s
  results.json                     # data file powering the dashboard
  results.tsv                      # tab-separated score log
  changelog.md                     # detailed mutation log with reasoning
  <chosen-name>.md                 # working revised resume (the artifact)
  <chosen-name>.md.baseline        # original resume at start-of-run
  recruiter-reports/
    experiment-000/
      <profile-slug>.md            # structured report per profile per experiment
      ...
    experiment-001/
      ...
```

And the profile cache at `<resume-parent-dir>/profiles/` grows as you target new companies. Profiles are co-located with the resume they were researched against -- not in the plugin tree.

---

## Outputs you should care about

1. **`applications/<company>/<role>/resume.html` + `cover-letter.html`** -- the per-opening submission pair. Print each to PDF and submit. The markdown sources live alongside for re-editing.
2. **`<chosen-name>.md`** -- the working revised resume that fed the locked variants. Diff against your original, decide what to keep, apply manually to your canonical resume. autowrite never overwrites your original.
3. **`changelog.md` + per-role `sub-changelog.md`** -- the research logs. Each kept mutation has a reason; each generated cover letter records which hiring-manager-profile evals it echoed and any candidate questions the subagent flagged rather than invent. When an interviewer asks "why is your resume structured this way?" you have receipts.
4. **`recruiter-reports/<final>/<profile>.md`** -- per-profile remaining gaps. These are your **interview prep talking points**. You know in advance what each target company will probe, because their recruiter subagent flagged it.
5. **`<resume-parent-dir>/profiles/<slug>.md`** -- the cached company profile. Reusable on every future run against this resume. Treat it as a living document.

---

## Customization

### Adjust convergence threshold

Edit `skills/autowrite/SKILL.md` step 5. Default is 90% aggregate for 3 consecutive experiments. Bump to 85% if you want shorter runs; bump to 92% if you want stricter convergence.

### Weight some profiles more heavily

When invoking, pass weights: `"anthropic: 2x, openai: 1x, google-deepmind: 1x"`. The aggregate becomes weighted. Useful when you have a primary target and secondary comparison points.

### Add a custom profile

Author a markdown file at `<resume-parent-dir>/profiles/<your-slug>.md` matching the schema in `skills/autowrite/references/profile-template.md`. The skill will use it without re-researching.

### Force a profile refresh

Pass `profile_refresh: true` at invocation, or delete the cached profile file. The research subagent re-runs.

---

## Limitations

- **Subagent variance.** Recruiter subagents are deterministic enough for single runs in most cases, but agentic eval scoring carries some noise. If you see implausible result flips without resume changes, bump `runs per experiment` to 3.
- **Research recency.** Profiles capture what was public at `researched_at`. Fast-moving fields (tech, AI, gaming, fashion, biotech) shift priorities quickly; slower fields (utilities, government, established trades) stay stable longer. Refresh quarterly for the former, semi-annually for the latter, or after major company news.
- **Single-document scope for scoring.** autowrite scores one resume against profiles. As of v0.6 it also generates a role-scoped cover letter per opening at the end of the secondary loop, but cover letters are an output artifact -- they are not scored or mutated against their own profile set. LinkedIn summaries and portfolio sites still aren't supported as scored targets, though the architecture would extend cleanly.
- **No verification.** A recruiter subagent scores a claim as it appears in the resume. If your resume says "shipped X" and you didn't, the subagent has no way to know. autowrite optimizes the document's pass rate; you remain accountable for accuracy.
- **English-only profiles right now.** The research subagent prompts in English and looks for English-language sources. Multilingual research is a future extension.

---

## Pattern lineage

autowrite is a direct adaptation of the autoresearch skill structure (binary evals, STOP-and-confirm gate, baseline-before-mutation, one-mutation-at-a-time, keep/discard logic, autonomous loop, never-stop posture, dashboard pattern, changelog format). The novel piece is the multi-subagent orchestration -- spawning one recruiter per profile in parallel, aggregating across profiles, mutating against the cross-profile gap.

If autoresearch optimizes a skill prompt against fixed evals, autowrite optimizes a resume against *researched, company-specific* evals across multiple targets simultaneously. Same loop, different artifact, broader eval surface.

---

## License

MIT. Use it, fork it, send improvements.
