---
name: autowrite
description: "Autonomously improve a resume by spinning up company-specific recruiter subagents in parallel, scoring the resume against binary hiring evals derived from researched company profiles, mutating one line at a time, and keeping improvements until the resume converges across multiple target companies. Use when: evaluate my resume, optimize my resume for X, run recruiter evals, autowrite, improve resume for [company]. Outputs: per-profile recruiter reports, a working resume revision, a results log, a changelog of every mutation, and a live HTML dashboard."
---

# Autowrite for Resumes

Most resumes work about 70% of the time. The other 30% of the time a recruiter glances at it for four seconds, finds nothing that maps to what they're hiring for, and moves on. The fix isn't to rewrite the resume from scratch. It's to let a team of agents -- each assisting a recruiter at a specific company -- score it against binary hiring criteria, mutate one line at a time, and tighten the resume until that 30% disappears.

This skill adapts Andrej Karpathy's autoresearch methodology (autonomous experimentation loops) to resume content. Instead of optimizing a skill prompt, we optimize a resume. Instead of one fixed eval set, we run multiple recruiter subagents in parallel, each with their own company profile and their own binary evals, and we converge against the aggregate.

---

## the core job

Take an existing resume, gather company-specific hiring profiles (researching them on first run, caching them on disk for reuse), then run an autonomous loop that:

1. Spawns one recruiter subagent per target company in parallel
2. Each subagent scores the resume against that company's binary evals
3. Aggregates results across all profiles -- per-profile pass rates and cross-profile gaps
4. Mutates one line of the resume to address the most-shared gap
5. Re-scores: every recruiter subagent runs again on the mutated resume
6. Keeps mutations that improve aggregate score, discards the rest
7. Repeats until convergence or budget cap

**Output:** A working revised-resume.md + `results.tsv` log + `changelog.md` of every mutation attempted + per-profile recruiter reports + a live HTML dashboard you can watch in your browser. The original resume is NEVER modified.

---

## before starting: gather context

Resolve the following fields. If the user invocation provides them, use the provided values. If any are missing, **first try `AskUserQuestion`**; if that tool is unavailable (e.g., the harness is in `dontAsk` / autonomous mode), fall back to the defaults below and **announce them in a single message before starting the loop**, so the user can correct in their next turn.

1. **Target resume** -- Path to a resume file. Accepted formats: `.md` (markdown -- the canonical input that the loop operates on), `.pdf` (auto-converted to markdown at Step 1.0; the original PDF is never modified). REQUIRED. If the invocation did not include a path, halt and ask for one even if `AskUserQuestion` is unavailable -- there is no sensible default.
2. **Target companies** -- One or more company names, optionally qualified by role. Examples across industries: "Anthropic / AI Engineer", "Turner Construction / Senior Project Manager", "Riot Games / Gameplay Engineer", "Kaiser Permanente / Clinical Operations Manager". REQUIRED. At least one; recommend 2-4. (more profiles = more reliable aggregate, but slower and more expensive)
3. **Runs per experiment** -- Default: 1 run per profile per experiment. (recruiter subagents are deterministic enough that 1 run usually suffices; bump to 3 if you see high variance across runs)
4. **Budget cap** -- Number of mutation experiments before stopping. Default: no cap (runs until convergence or user stops). When the user says "budget N" in plain language, interpret as N mutation experiments (so total experiments = 1 baseline + N mutations).
5. **Profile refresh** -- Force re-research even for cached profiles. Default: use cache if available. (set this when company priorities have visibly shifted, e.g., a major reorg or product pivot)
6. **Clean run** -- Discard prior run state and start fresh on scoring/mutation. Default: `false`. Triggers when the user says any of: "clean run", "fresh run", "re-score from scratch", "reuse discovery only", "anti-bias rerun", or passes `clean_run: true`. In clean-run mode:
   - The skill reuses **cached company profiles** (`<resume-parent-dir>/profiles/<slug>.md`) and **cached discovery output** (`<resume-parent-dir>/applications/<company>/openings-*.json` and its companion `.md` file).
   - The skill **does NOT** read or resume from prior recruiter reports, prior hiring-manager profiles, prior per-role working files, prior locked variants, or the prior `autowrite-<slug>/` working directory.
   - Before starting, the skill **archives** any existing prior-run artifacts to `<resume-parent-dir>/archive/<YYYY-MM-DD>-<HHMM>/` so they are preserved but invisible to the loop. The archive includes the `applications/<company>/` per-role subdirectories, locked variants, the prior `autowrite-<slug>/` working dir, and per-company `index.html` / `results-openings.tsv`. The openings JSON and openings MD files for each company are **NOT** archived -- they stay in `applications/<company>/` so Step 6a's discovery can be skipped on the rerun.
   - Step 6a uses the cached discovery output directly (no new discovery subagent call). The companion openings markdown is updated only if new processing decisions need to be logged.
   - Primary loop (Steps 4-5) re-baselines against the current resume markdown -- no carryover from prior baseline scores.
   - Secondary loop (Step 6) rebuilds hiring-manager profiles fresh for every role in the cached openings JSON.
   - The purpose is anti-bias: when the user has edited the resume or refined supplementary context, clean-run guarantees the new scoring is not contaminated by prior verdicts or by parent-skill heuristics that learned the old shape of the resume.

**Announcement format (when proceeding with defaults in autonomous mode).** Before the first tool call, post a single message like:

> Starting autowrite with: resume=`<path>`, targets=`[<company list>]`, runs_per_experiment=1, budget=<N or "uncapped">, profile_refresh=false. Working dir: `<resume-dir>/autowrite-<resume-slug>/`. Working revision filename: `<resume-slug>-<target-slug>.md`. Correct me in your next message if any of this is wrong before the loop spends meaningful time.

Then proceed without further confirmation. The user can interrupt or correct on the next turn.

**File-creation fallback (when Write tool is denied).** In some harness configurations (`dontAsk` mode + restricted Write rules), the `Write` tool is denied even though file creation in the target paths is legitimate. When the parent skill encounters a `Write` denial:

1. First try the `Edit` tool (some configurations allow Edit but not Write).
2. If both Write and Edit are denied, fall back to PowerShell on Windows or Bash on Unix:
   - **PowerShell:** `Set-Content -Path "<full path>" -Value "<content>" -Encoding UTF8` for new files; `Add-Content` for appending.
   - **Bash:** `cat > "<path>" <<'EOF' ... EOF` for new files; `cat >> "<path>"` for appending.
3. This is not a malicious bypass -- it is a sanctioned fallback for the specific case where the user has explicitly approved alternative tools but the `Write` tool's permission entry is matched differently. Announce the fallback in chat ("Write tool denied; falling back to PowerShell Set-Content") so the trace is auditable.
4. If all of Write, Edit, and shell-based file writes are denied, stop and report -- the harness configuration does not support autowrite's required outputs.

**Avoid compound shell commands.** A Bash invocation like `cd "..." && for slug in "a" "b" "c"; do mkdir "$slug" && cp src "$slug/dst"; done` will fail under `dontAsk` even when individual `Bash(mkdir:*)`, `Bash(cp:*)`, and `Bash(cd:*)` rules are all in the allowlist -- the matcher matches against the FULL command string, not the underlying ops, and compound chains rarely match a single allowed pattern. When you need to apply the same operation to multiple files (e.g., copying `_company-locked.md` into N per-role `resume.md` files):

- **Preferred:** use the `Write` tool once per destination file. Slow but predictable. Each call is its own permission check against its own destination path.
- **Acceptable:** invoke `PowerShell` with a single-statement command (e.g., `Copy-Item -Path "src" -Destination "dst"`). The `PowerShell(Copy-Item:*)` rule typically matches. Repeat N times rather than scripting a loop.
- **Avoid:** Bash compounds with `&&`, `;`, `for`, `while`, or pipelines unless the entire compound was pre-approved as a single allowlist entry. They are the most common cause of mid-run permission failures.

---

## step 1: read the resume and the references

Before changing anything, read and understand the target resume completely.

### Step 1.0 -- PDF intake (skip if input is already `.md`)

If the target resume path ends in `.pdf`, autowrite must convert it to markdown before any downstream step touches it. The PDF is the **source artifact**; the markdown is the **working artifact**. The original PDF is never modified.

Procedure:

1. Read the PDF using the `Read` tool (the tool natively handles PDFs and returns the textual content, with image-bearing pages preserved as best-effort text extraction).
2. Convert the extracted content into a markdown file that mirrors the PDF's visible structure. Follow the **structure-discovery approach** described in [references/resume-html-template.md](references/resume-html-template.md), but in reverse -- inspect the PDF's headings, section breaks, role blocks, bullet patterns, contact line, and date conventions; emit the canonical markdown form for each. Specifically:
   - The candidate's name (typically the largest text on page 1) becomes the top-level `# Heading`.
   - The contact line directly under the name becomes the paragraph(s) immediately below the `# Heading`.
   - Each section header (typography signals: caps, bold, underlined, or visually larger than body text) becomes `## Heading` using the candidate's exact wording.
   - Each role entry inside a section becomes a `### Heading` followed by an italic date line if the PDF used a date row beneath the title.
   - Bullets remain bullets. Paragraphs remain paragraphs. Bold and italic spans inside body text are preserved.
3. Save the converted markdown alongside the PDF as `<pdf-stem>.md` in the same directory. Example: `~/career/resume-2026.pdf` -> `~/career/resume-2026.md`. If a `.md` of the same stem already exists in that directory, save as `<pdf-stem>-converted-<YYYY-MM-DD>.md` instead so the existing file is never overwritten.
4. Announce the conversion in chat: "Converted `<pdf-path>` to `<md-path>` (PDF intake). The original PDF is unchanged. Downstream steps operate on the markdown."
5. From this point forward, treat `<md-path>` as the canonical `<target-resume>` for every later step. The PDF is not referenced again unless the user explicitly asks for a re-conversion.

If the PDF is more than ~10 pages, pass a `pages` range to the Read tool (e.g., `pages: "1-3"` for a 2-page resume with one trailing page of references). Resumes longer than 3 pages are rare; if the user provides a long PDF, announce in chat and ask before converting all pages.

If text extraction is poor (scanned image, heavy formatting, missing words), announce in chat with the suspect output and ask whether to (a) proceed with the imperfect conversion, (b) wait for the user to provide a higher-fidelity markdown copy, or (c) re-read with `pages` narrowed to the most-relevant range.

### Step 1.1 -- Read references and check run state

1. Read the full resume markdown file (the converted one from Step 1.0 if the input was a PDF, otherwise the original `.md`).
2. **Load supplementary context (if present).** Look in the resume's parent directory for any of these subdirectories: `bullets/`, `context/`, `interview-notes/`, `narratives/`. If any exist, read every `.md` file within them. Treat their contents as the candidate's **factual library** -- itemized work, draft bullets, talking points, interview Q&A. The mutation loop may quote or paraphrase from this library when proposing changes that need specifics the resume doesn't currently surface. Hard constraint: only material in the resume + supplementary library is considered "stated." Anything not in either source must be flagged as a question to the candidate before being added to the resume. Announce the supplementary load in chat: "Loaded N supplementary context files from `bullets/`, `interview-notes/` (M total .md files). These will be available to the mutation engine for quoting factual phrasings without fabricating."
3. Read [references/eval-guide.md](references/eval-guide.md) so you can later evaluate whether researched evals are well-formed.
4. Read [references/profile-template.md](references/profile-template.md) so you know the profile schema.
5. Read [references/recruiter-subagent-prompt.md](references/recruiter-subagent-prompt.md), [references/research-subagent-prompt.md](references/research-subagent-prompt.md), [references/job-openings-subagent-prompt.md](references/job-openings-subagent-prompt.md), and [references/hiring-manager-subagent-prompt.md](references/hiring-manager-subagent-prompt.md) so you know exactly how each subagent role will be invoked.
6. Read [references/resume-html-template.md](references/resume-html-template.md) so you know the print-ready HTML conventions used when rendering locked variants and per-opening resumes.
7. **Check for existing run state.** Look ONLY at `<resume-parent-dir>/autowrite-<resume-slug>/`. If that directory exists with a `results.tsv` row at experiment 0 or higher:

   - **If `clean_run: true`** (per the context-gathering step 6): archive the existing `autowrite-<resume-slug>/`, `applications/<company>/_company-locked.{md,html}`, `applications/<company>/index.html`, `applications/<company>/results-openings.tsv`, and every per-role subdirectory under `applications/<company>/` (i.e., everything in `applications/<company>/` EXCEPT the `openings-*.json` and `openings-*.md` files) to `<resume-parent-dir>/archive/<YYYY-MM-DD>-<HHMM>/`. The openings JSON / MD remain in place so Step 6a can skip discovery. Announce: "Clean-run mode: archived prior run artifacts to `<archive-path>/`. Discovery output retained at `<openings-paths>`. Starting fresh primary baseline."
   - **If `clean_run: false`** (default): this is a **resume scenario**, not a fresh start. Read the existing `results.json` and `changelog.md`. Announce in chat: "Resuming from experiment N (status: <status>). Profiles already in cache: [...]. Locked variants already produced: [...]." Then continue the loop from where it stopped rather than re-baselining.

   **Locality rule.** Do not search other directories for prior autowrite runs. If the user wants to resume a prior run that lives in a different tree, they should explicitly pass the resume path that points into that tree. Cross-tree run-state imports are forbidden for the same reasons as cross-tree profile imports (see Step 2).

Do NOT skip this. You need to understand the resume's structure, identify its load-bearing claims, know the eval and profile contracts, and recognize prior run state before you can score or mutate anything. Hour-long human-on-the-loop runs depend on being resumable.

---

## step 2: resolve company profiles

Profiles cache **strictly co-located with the resume**, never in the plugin directory and never imported from any other location. The cache location is `<resume-parent-dir>/profiles/<slug>.md` -- where `<resume-parent-dir>` is the directory containing the resume markdown file currently being processed.

**Strict locality rule (do not violate even when being helpful):**

- The ONLY directory autowrite consults for cached profiles is `<resume-parent-dir>/profiles/`.
- Do NOT search the filesystem for prior runs in other directories.
- Do NOT "port" profiles from a sibling resume tree, a previous test, a different candidate, or any cached `autowrite-*` working directory that is not under the current `<resume-parent-dir>`.
- Do NOT use Glob, Grep, or any other tool to look for prior profiles outside `<resume-parent-dir>/`. If they exist elsewhere, they are a different run, for a different resume, and importing them invalidates the test.
- The cost of re-researching a profile (~30 seconds + a WebSearch budget hit) is far lower than the cost of contaminating a run with a stale or cross-context profile.

If the user wants to reuse profiles from a previous run, the correct path is for them to manually copy the profile files into the current `<resume-parent-dir>/profiles/` directory before invoking autowrite. The skill itself never performs cross-tree imports.

For each target company:

1. Slugify the target. Examples: "Anthropic" -> `anthropic`, "OpenAI / Applied Research" -> `openai-applied-research`.
2. Check `<resume-parent-dir>/profiles/<slug>.md`. If it exists AND the user did not request a profile refresh, load it and move on. **Do not check anywhere else.**
3. Otherwise, spawn a **research subagent** using the prompt template in [references/research-subagent-prompt.md](references/research-subagent-prompt.md). Pass it the company name and optional role qualifier. The subagent uses WebSearch and WebFetch to gather hiring signals and produces a profile markdown file following the schema in [references/profile-template.md](references/profile-template.md).
4. Critically, the profile must contain **6 to 12 binary yes/no eval criteria** that are specific to that company's bar -- not generic "demonstrates leadership" filler. See [references/eval-guide.md](references/eval-guide.md) for what good evals look like.
5. Save the profile to `<resume-parent-dir>/profiles/<slug>.md`. Create the `profiles/` directory if it does not exist.
6. Load it.

When you can spawn multiple research subagents in parallel, do so -- they don't depend on each other. Single message, multiple Agent tool calls.

**Validation gate:** before moving past step 2, read each new profile and confirm:
- All template sections are populated
- Each eval is binary (yes/no, not a scale, not subjective)
- No eval references a different company by name
- No eval is so narrow that the resume could trivially game it

If any profile fails validation, re-spawn the research subagent for that target with explicit feedback about what was wrong.

**Profile-overalignment safeguard.** A single research subagent can produce evals that align too closely with the resume's existing language, giving a false 100% baseline. Defensive rule:

- If the user passed exactly **1 target company**, automatically queue a **triangulation profile** before declaring a confident baseline. Pick a sibling company in the same role family. Infer the role family from the resume and the original target -- for any field, pick a peer company that the candidate could plausibly also apply to. Announce the addition in chat: "Adding <sibling> as triangulation profile -- single-target baselines are unreliable. To skip, re-invoke with `triangulate: false`."
- If the user explicitly passed `triangulate: false`, honor it but warn in chat that single-profile baselines can be deceptive.
- If 2+ target companies were passed, no triangulation needed -- the user already configured for cross-profile signal.

---

## step 3: generate the live dashboard

Before running any experiments, create a live HTML dashboard at `<resume-dir>/autowrite-<resume-slug>/dashboard.html` and open it in the browser.

The dashboard must:
- Auto-refresh every 10 seconds (the page reloads itself via `setTimeout(() => location.reload(), 10000);`). Do NOT use `fetch('results.json')` -- it is silently blocked by Chrome and Edge under the `file://` protocol due to CORS-on-local-files defaults. Full-page reload is the only pattern that works reliably across browsers without requiring the user to launch with special flags or run a local server.
- Open with a **Table of Contents** at the top: anchor links to (a) Primary loop progression, (b) Per-profile eval breakdown, (c) Per-company secondary-loop panels (one anchor per locked company linking to that company's section AND to its standalone `applications/<company>/index.html`), (d) Locked variants list with direct links to `_company-locked.html` files. The TOC is the loop-time navigation surface -- the user lands here, scans active state, and jumps to whichever artifact they need.
- Show a score progression chart with **one line per profile** plus a bold aggregate line (X axis: experiment number, Y axis: pass rate %)
- Show a colored bar for each experiment: green = keep, red = discard, blue = baseline
- Show a table of all experiments with: experiment #, mutation summary, per-profile pass rates, aggregate, status (keep/discard/baseline)
- Show per-profile eval breakdown: which evals pass most/least for each company
- Show current status: "Running experiment [N] against [profile-count] profiles..." or "Idle" or "Converged"
- Clean styling: white background, pastel accents, monospace for numbers, sans-serif for prose

Generate the dashboard as a single self-contained HTML file with inline CSS and inline JavaScript and **inline data**. After every experiment, re-write the entire `dashboard.html` file with the latest results data baked directly into a `<script>const results = { ... };</script>` block at the top of the body. Then the page's auto-reload picks up the fresh data on the next refresh tick. Do not rely on a separate JSON fetch -- the data is in the HTML.

You can still keep `results.json` as a sibling file (for machine-readable consumption -- the user can grep it, parse it, archive it, etc.). But the dashboard's source of truth is the inline data block, not the JSON file. Update both after every experiment.

Use Chart.js loaded from CDN for the chart. The TOC links and the locked-variant / company-index links are static HTML (no JS dependency) so they continue to work even if Chart.js fails to load. **Print the absolute path to the dashboard in chat** so the user can open it themselves; optionally attempt to open it automatically (`Start-Process` on Windows PowerShell, `open` on macOS, `xdg-open` on Linux) but treat auto-open failure as non-fatal -- the loop must continue even if the browser can't be launched from the harness.

**Update `results.json`** after every experiment so the dashboard stays current. Format:

```json
{
  "resume_slug": "candidate-2026-05-12",
  "status": "running",
  "current_experiment": 3,
  "baseline_aggregate": 64.0,
  "best_aggregate": 78.0,
  "profiles": ["anthropic", "openai", "google-deepmind"],
  "experiments": [
    {
      "id": 0,
      "status": "baseline",
      "mutation": "original resume -- no changes",
      "per_profile": {"anthropic": 65.0, "openai": 60.0, "google-deepmind": 67.0},
      "aggregate": 64.0
    }
  ],
  "eval_breakdown": {
    "anthropic": [{"eval": "Cites a shipped multi-agent system", "passed": true}, ...],
    "openai": [...]
  }
}
```

When the loop finishes, set `status` to `"converged"`, `"budget-hit"`, or `"stopped"` so the dashboard renders a final-state summary.

---

## step 4: establish baseline

Run the recruiter eval AS-IS on the original resume before changing anything. This is experiment #0.

1. **Ask the user what to name the working revision.** Example: "What should I call the optimized resume? (e.g., resume-2026-frontier-labs, resume-v2)". The user picks the name.
2. Create the working directory: `<resume-dir>/autowrite-<resume-slug>/`
3. **Copy the original resume into the working directory as `<chosen-name>.md`** -- this is the copy you will mutate. NEVER edit the original resume. All mutations happen on this copy.
4. Also save `<chosen-name>.md.baseline` (identical to the original at start-of-run; this is the revert target).
5. Create `results.tsv` with the header row.
6. Create `results.json` and `dashboard.html`, then open the dashboard.
7. **Spawn all recruiter subagents in parallel** -- one per profile -- using the prompt template in [references/recruiter-subagent-prompt.md](references/recruiter-subagent-prompt.md). Pass each subagent the full resume markdown and the full profile markdown. Single message, multiple Agent tool calls.
8. Collect their structured reports. Score each profile (passed evals / total evals).
9. Compute the aggregate (mean across profiles -- weighted if the user provided weights).
10. Write the baseline row to `results.tsv` and update `results.json`.

**results.tsv format (tab-separated):**

```
experiment	status	mutation	anthropic	openai	google-deepmind	aggregate
0	baseline	original resume -- no changes	65.0	60.0	67.0	64.0
```

**IMPORTANT:** After establishing baseline, confirm the score with the user before proceeding. If aggregate is already 90%+, the resume may not need optimization. Surface the per-profile breakdown so the user can spot whether one company is dragging the average.

---

## step 5: primary mutation loop with lock-and-branch

This is the primary autowrite loop. Once started, run autonomously. **Each profile can independently LOCK** -- when a profile reaches ≥90% pass rate for 3 consecutive experiments, that profile's variant of the resume is saved as the company-canonical artifact and removed from the active mutation pool. The loop continues against the remaining un-locked profiles until all profiles lock, the budget is exhausted, or you stop.

The lock-and-branch design recognizes that different companies have divergent hiring bars: a single converged resume that "satisfies all profiles at once" is rarely the best output. Per-company resume variants score better against their own profile AND give the user concrete artifacts to submit to each company. Once a profile locks, the variant for that company is fixed -- subsequent mutations targeting OTHER profiles do not modify the locked variant.

**LOOP (per experiment, all un-locked profiles in parallel):**

1. **Identify the working pool.** Active profiles are those that haven't yet locked. If all profiles are locked, exit the primary loop and proceed to step 6 (secondary loop) for each locked variant.

2. **Analyze failures across un-locked profiles.** For each active profile, look at which evals are failing. Read the actual "gaps" returned by each recruiter subagent. Rank gaps by how many active profiles flag them -- a gap appearing in 2 of 2 un-locked profiles is more valuable to fix than a gap appearing in 1 of 2.

3. **Form a hypothesis.** Pick ONE thing to change about the working resume copy of the **lowest-scoring un-locked profile** (the one furthest from lock). Don't change 5 things at once.

   Good mutations:
   - Add a specific quantified outcome to a bullet that's currently vague ("led a team" -> "led a team of 4 engineers across 3 quarters")
   - Reword a sentence so it leads with a verb that maps to the dominant target profile
   - Move a buried bullet higher within a role section (priority = position on the page)
   - Add a new bullet that documents a capability the active profile flags as missing
   - Trim a bullet that's burning resume real estate on a low-signal item
   - Add a specific keyword the active profile screens for (only if true)

   Bad mutations:
   - Rewriting an entire section from scratch
   - Adding 5 new bullets at once
   - Padding to fill space
   - Generic resume cliches ("results-driven," "passionate about")
   - Adding a claim that isn't true -- recruiter subagents may pass on it but a real interviewer will catch you

   **Using the supplementary context library.** If Step 1.1 loaded `bullets/`, `context/`, `interview-notes/`, or `narratives/` from the resume's parent directory, those files are your factual library for this mutation step. When an eval flags a gap that the resume doesn't address but the supplementary library does, pull the relevant phrasing from the library into the resume mutation. Cite which library file the phrasing came from in the changelog entry (e.g., `Source: bullets/meta-ise.md`). Anything not present in the resume OR the library is not yet "stated" -- flag it as a question to the candidate in the changelog (e.g., `Candidate question: did you ship a fine-tuning workflow? Not in resume or library.`) rather than fabricating.

4. **Branch the working file per active profile.** If multiple profiles are active, maintain one mutation track per profile so mutations don't bleed across companies whose bars genuinely differ. The working files live at:

   ```
   <working-dir>/<resume-slug>-<company-slug>.md
   ```

   Apply the mutation to the file matching the lowest-scoring un-locked profile. Other profiles' working files only re-score if the mutation is also potentially useful for them (judgment call based on the gap analysis).

5. **Re-score in parallel.** Spawn all un-locked recruiter subagents on their respective working files in parallel. Single message, multiple Agent tool calls.

6. **Per-profile keep/discard decision.** For each active profile, against its working file:
   - Pass rate improved -> **KEEP.** Working file advances.
   - Pass rate stayed the same -> **DISCARD.** Revert that file.
   - Pass rate got worse -> **DISCARD.** Revert that file.

7. **Check for lock.** For each active profile, after applying keep/discard, check the last 3 experiments' pass rates *for that profile*. If all 3 are ≥90%, the profile **LOCKS**:
   - Save the working file as the company-locked variant at `<resume-parent-dir>/applications/<company-slug>/_company-locked.md`.
   - **Render the locked variant to HTML** at `<resume-parent-dir>/applications/<company-slug>/_company-locked.html` using [references/resume-html-template.md](references/resume-html-template.md). This is the print-ready artifact -- the user prints to PDF from the browser.
   - Append a `## LOCKED` entry to `changelog.md`.
   - Update `results.json` to mark the profile as locked.
   - Announce in chat: "Anthropic profile locked at experiment N (pass rates: 92%, 91%, 95% over last 3). Saved markdown to applications/anthropic/_company-locked.md and HTML to _company-locked.html (open in browser -> Ctrl+P -> Save as PDF). Continuing primary loop against [<remaining-profiles>]."
   - Remove the profile from the active pool.

8. **Log the experiment** in `results.tsv` and append to `changelog.md`. Include per-profile pass rates and lock status.

9. **Repeat.** Go back to step 1 of the loop.

**STOPPING CONDITIONS** for the primary loop:
- All profiles have locked (transition to step 6 -- secondary loop)
- Budget cap hit (default: 10 mutations; surface remaining un-locked profiles as candidates for manual review)
- User manually stops
- 5 consecutive experiments produce zero kept mutations across all active profiles (the resume has stabilized; no further automated lift available)

**NEVER STOP** mid-experiment. Once a mutation is applied, complete the re-score and decision before checking stop conditions.

**If you run out of mutation ideas:** Re-read each active recruiter subagent's structured suggestions. Try the highest-priority revision the lowest-scoring profile suggested. Try a structural mutation (re-ordering experience entries, moving Personal Projects above Experience for a research-heavy target). Try removing instead of adding -- a tighter resume often scores higher than a padded one.

---

## step 6: secondary loop -- per-opening tailoring

The primary loop produces per-company locked variants. The secondary loop takes each locked variant, discovers actual open job postings at that company, builds a role-scoped hiring-manager profile for each, and runs a sub-mutation loop against that profile to produce a per-opening resume variant. Output: a directory of submission-ready resumes, one per open role you could plausibly apply for.

Run this loop **for each company that locked** during the primary loop. If multiple companies locked, run them sequentially (not in parallel) -- this keeps the user's dashboard and chat trace coherent across a multi-hour session.

**For each locked company:**

### 6a. Discover open roles

**Clean-run discovery reuse.** If `clean_run: true`, look in `<resume-parent-dir>/applications/<company-slug>/` for prior discovery artifacts. Two cases:

- **Preferred -- openings-*.json exists.** Load the JSON directly. It has full `roles[]` records with `title`, `url`, `responsibilities_extract`, `requirements_extract`, `active_status`, etc. Hand each role to the hiring-manager subagent at Step 6b with the verbatim JD extracts inline. Announce: "Clean-run mode: reusing cached discovery JSON (`<N>` total roles, `<M>` active). Skipping fresh discovery subagent."

- **Fallback -- only openings-*.md exists** (e.g., the prior run bailed before writing JSON). Parse the markdown's role tables to extract title + URL (when present) per role. **Discard any "Selected for processing" annotations, "Not selected because..." commentary, and rationale paragraphs** -- those represent the prior run's parent-skill editorial bias and must not contaminate the rerun. The role list itself (what discovery found) is bias-free and reusable; the selection layer on top of it is not. Hand each role to the hiring-manager subagent at Step 6b with just title + URL; the subagent uses WebFetch to pull the JD verbatim. Announce: "Clean-run mode: no openings JSON found, falling back to openings markdown for role extraction. Discarding prior selection rationale (anti-bias). Processing all `<N>` extracted roles via fresh hiring-manager subagents that re-fetch JD content."

- **Neither exists** (clean run on a directory with no prior discovery output): treat the same as fresh-run mode. Spawn the discovery subagent.

In all reuse paths, the rule from "No fit predictions at the selection step" applies: process every active role from the cached discovery, no editorial subset. Cached discovery's `active_status` and `excluded_reason` tags are honored (mechanical filter), but the parent skill does not apply additional judgment on top.

Otherwise (fresh discovery, not clean-run): Spawn the **job-openings discovery subagent** using [references/job-openings-subagent-prompt.md](references/job-openings-subagent-prompt.md). Pass it the company name, today's date, and the locked resume variant (used only to calibrate role-family filtering, not for scoring).

**Hand-off contract.** The subagent's JSON response can be large (50+ roles for a major company). Save the raw JSON to disk immediately upon receiving it -- do NOT hold the full payload in active context. The parent's working memory only needs a digest (count by status, count by source, the list of role titles + URLs + slugs). The full record per role is re-read from disk in batches during 6b-6e.

Save the raw discovery output to `<resume-parent-dir>/applications/<company-slug>/openings-<YYYY-MM-DD>.json`. This is the discovery cache (7-day lifetime per the subagent's own spec). The subagent does **not** self-filter -- every role it considered, including those tagged closed or excluded, appears in the JSON.

**Generate `openings-<YYYY-MM-DD>.md` companion file.** Markdown is the audit surface; JSON is the machine surface. The markdown file must be scannable in under 30 seconds. Format:

```markdown
# <Company> openings -- discovered <YYYY-MM-DD>

Sources consulted:
- <source 1>: <N roles found>
- <source 2>: <N roles found>

## Active roles (N)
| # | Title | Team | Location | Posted | URL | Also seen on |
|---|-------|------|----------|--------|-----|--------------|
| 1 | <title> | <team> | <loc> | <date or "no date"> | <url> | <comma-separated other sources, or "-"> |
...

## Excluded by tag (N)
| Title | URL | Excluded reason |
|-------|-----|-----------------|
| <title> | <url> | <reason> |
...

## Closed / unverified (N)
| Title | URL | Status | Evidence |
|-------|-----|--------|----------|
| <title> | <url> | <closed/unverified> | <one-line evidence> |
...

## Notes
<discovery_notes verbatim from the subagent, or "none">
```

This is the artifact the user will scan when they want to know "what did the search consider." Save it next to the JSON.

**Surface every role title in chat.** After generating both files, post a single message with the full active-role list (titles + URLs), the count of excluded/closed/unverified roles with a one-line reason summary, and the path to `openings-<YYYY-MM-DD>.md` for full detail. Example:

> Discovered 14 roles for Anthropic. 9 active, 2 closed (Greenhouse no-longer-accepting), 3 excluded (1 requires PhD, 2 are Account Executive roles outside engineering arc). Full list: [paths]. Processing all 9 active roles into hiring-manager profiles unless you say otherwise in your next message.

**Decision on what to process.** In normal mode use `AskUserQuestion` to let the user select a subset. In dontAsk / autonomous mode, process **every active role** from the discovery output -- no count cap, no freshness cap, no editorial subset selection. If the discovery agent surfaced N active roles, all N get scored. The architectural premise is simple: if a role is viable (active status, no hard structural disqualifier), it is evaluated. The recruiter subagent at Step 6c determines per-role fit through binary evals -- that is the layer where "is this candidate competitive for this role" gets answered. The parent skill does not pre-empt that determination here.

**No self-narrowing.** When discovery returns a large set (50+ or even 150+ roles), DO NOT pick a "high-signal" subset to keep the run manageable. That is exactly the bias the discovery prompt was rewritten to avoid -- and re-introducing it at this layer defeats the purpose. The correct response to a large discovery is **batching**: process roles in groups of 5-10, completing each batch's hiring-manager + recruiter pass before starting the next. Save each batch's artifacts to disk so the parent's active context stays bounded. The batch count and order should be `posted_date`-freshness sorted (freshest first, so the user gets the most-relevant verdicts earliest in a long run) but the **SET being processed is every active role**. Narrowing to a "high-signal" subset of 6 or 25 instead of batching all N is a contract violation -- it pre-filters in exactly the way Goodhart discipline forbids, and it can hide the specific role the candidate had in mind behind a freshness-rank or editorial-judgment cut.

**Budget framing for long runs.** A 90-role discovery with 5-role batches is 18 batches; each batch runs hiring-manager + recruiter subagents in parallel within the batch, so wall-clock time scales with batch count, not total role count. Surface this to the user explicitly in chat at the start of Step 6: "Discovery surfaced N active roles for `<company>`. Processing all N in batches of B (≈ N/B batches). Estimated wall-clock: X minutes. Each batch's artifacts save to disk before the next starts; you can review intermediate results in `applications/<company>/` as the run progresses." This lets the user interrupt if they want a narrower scope -- but the default is full coverage.

**No fit predictions at the selection step.** The selection step is the same layer where latest-identity bias previously snuck into discovery, and it can re-enter here if the parent makes its own judgments about which roles "fit" the candidate. The selection step MAY filter on:

- `active_status` from discovery (drop `closed` roles unless the user asks otherwise; treat `unverified` as active)
- `excluded_reason` from discovery (already-tagged hard structural disqualifiers like PhD-required, security clearance, licensed profession)
- Maximum count cap (top 25 by `posted_date` freshness when the active set exceeds 25)

The selection step MUST NOT filter on:

- "Resume probably won't score well against this profile" -- that prediction is the recruiter subagent's job, downstream. Pre-empting it collapses the breadth discovery just produced.
- "Less SE-heavy" / "less framework-specific" / "more customer-facing" / "more research-heavy" -- these are role-family characterizations that belong in the hiring-manager profile's evals, not in selection.
- "Outside the X-engineering arc" / "outside the candidate's stated identity" -- same latest-identity bias the discovery prompt was rewritten to avoid. If discovery surfaced it, the candidate's surface area allows it.
- "Candidate has no formal experience in this role family" -- the resume's full surface area (including adjacent families and personal projects) determines competition zone, not paid-title exact match. The hiring-manager subagent reads the JD and the resume and decides; the parent does not pre-empt.
- "This role overlaps with another role we already selected" -- duplicate teams or duplicate titles are still distinct openings with distinct hiring managers and slightly different evals. The user picks which to submit; the parent does not deduplicate.

The selection step is mechanical, not editorial. The editorial layer is the recruiter / hiring-manager subagents that score per-role. If you find yourself writing a rationale paragraph for why each role was or wasn't selected, you are doing editorial work at the wrong layer. The correct selection-step output is a simple ordered list of the top-25-freshest active roles, no commentary.

**Auditable narrowing.** If you DO narrow (because >25 active or because some are `excluded_reason`-tagged), the openings markdown's "Excluded by tag" / "Closed / unverified" tables already capture the audit trail. Do not add a second editorial narrative on top -- that's where bias smuggles in.

If the subagent returns 0 roles total, announce in chat with the `discovery_notes` content and skip to the next locked company.

### 6b. For each role, build a hiring-manager profile

**This step is REQUIRED for every role being processed. It may not be skipped.** Copying the locked company variant directly into a per-role `resume.md` without first generating a role-scoped hiring-manager profile defeats the entire secondary loop. If the JD content needs to be fetched from the web to build the profile, **spawn the subagent** -- the `Explore` subagent type has `WebFetch` and `WebSearch` in its tool envelope even when the parent skill doesn't. Do not bypass on the assumption that "WebFetch isn't available" -- it is, inside the subagent.

In parallel **within each batch** (per the no-self-narrowing rule in 6a -- 5-10 roles per batch): spawn one **hiring-manager profile subagent** per role using [references/hiring-manager-subagent-prompt.md](references/hiring-manager-subagent-prompt.md). Pass it:
- Company name and role title
- JD URL
- The company profile markdown (full text, inline)
- The JD markdown extract from the discovery JSON (verbatim responsibilities and requirements sections; the subagent uses these as primary source if WebFetch on the JD URL fails)

Each subagent returns a hiring-manager profile body (same schema as a company profile, with `hiring_manager_view: true` in the frontmatter and 8-15 evals blending 4-6 inherited company evals + 4-9 JD-derived evals).

Save each profile to:

```
<resume-parent-dir>/applications/<company-slug>/<role-slug>/hiring-manager-profile.md
```

Slugify `<role-slug>` from the role title (lowercase, hyphenated, drop punctuation).

**If a subagent fails to fetch the JD AND the discovery JSON's `responsibilities_extract` / `requirements_extract` are also thin** (the discovery agent itself didn't get good JD content), the hiring-manager subagent should produce a profile with inherited company evals plus a `## Profile limitations` section noting the thin JD source -- not a bypass. The recruiter subagent downstream will treat this profile with lower confidence, which is the correct calibration, not a skip.

### 6c. Score the locked variant against each hiring-manager profile

In parallel across all roles: spawn one **recruiter subagent** per role using [references/recruiter-subagent-prompt.md](references/recruiter-subagent-prompt.md). Pass it the **locked company variant** (`_company-locked.md`) as the resume and the hiring-manager profile as the profile. The recruiter's prompt template detects the `hiring_manager_view: true` flag and shifts its scoping mode accordingly.

Save each recruiter report to:

```
<resume-parent-dir>/applications/<company-slug>/<role-slug>/recruiter-report-baseline.md
```

This is the **opening-level baseline** -- the locked company variant scored against this specific role's requirements. Some roles will pass at high rates (the locked variant happens to fit); others will surface real gaps.

### 6d. Sub-mutation loop per role

For each role where the baseline score is below the lock threshold (≥90% pass rate), run a sub-mutation loop:

1. Copy `_company-locked.md` to `<role-slug>/resume.md` -- this is the per-opening working file.
2. Apply the same mutation discipline as the primary loop, but mutate against the hiring-manager profile's gaps instead of the company profile's gaps.
3. Re-score with the recruiter subagent + hiring-manager profile.
4. Keep/discard per the primary loop's rules.
5. Lock the role when pass rate hits ≥90% for 3 consecutive experiments OR when a per-role budget (default: 5 mutations) exhausts.

For roles that already pass at baseline (≥90% on the first recruiter scoring), no sub-mutation loop needed. The locked company variant IS the opening-tailored resume. Copy `_company-locked.md` to `<role-slug>/resume.md` unchanged and mark the role as "ready-to-submit at baseline."

### 6e. Per-role artifacts

After each role's sub-loop completes (whether it locked, baselined above threshold, or hit budget), **render the per-role markdown to HTML** at `<role-slug>/resume.html` using [references/resume-html-template.md](references/resume-html-template.md). The HTML is the print-ready submission artifact.

After each role's sub-loop completes, the directory looks like:

```
<resume-parent-dir>/applications/<company-slug>/<role-slug>/
  resume.md                          # opening-tailored variant (markdown source)
  resume.html                        # print-ready variant (the final submission artifact -- print to PDF from browser)
  hiring-manager-profile.md          # role-scoped profile
  recruiter-report-baseline.md       # initial score before sub-mutation
  recruiter-report-final.md          # final score after sub-mutation (or same as baseline if no mutations needed)
  job-posting.md                     # markdown snapshot of the JD (from discovery)
  sub-changelog.md                   # mutation log for THIS role only
```

### 6f. Update the dashboard and announce

After each role completes, append a row to a secondary results file at `<resume-parent-dir>/applications/<company-slug>/results-openings.tsv`:

```
role_slug	baseline_pct	final_pct	mutations_kept	status	submission_ready
ai-engineer-applied	78.6	91.7	3	locked	yes
research-engineer-evals	66.7	66.7	0	budget_exhausted	flag_for_review
```

Update the dashboard HTML to show a secondary panel per locked company with the per-role results. Announce each role's completion in chat with a one-line summary so the user can follow along during the hour-long run.

### 6g. Generate the company-level index page

After all discovered roles for a company have been processed (locked, baselined-above-threshold, or budget-exhausted), generate a company-level HTML index at `<resume-parent-dir>/applications/<company-slug>/index.html`. This is the user-facing entry point for that company -- one page that shows every opening, its current status, and a link to the printable resume tailored for it.

The index must contain:

- A header with the company name, the locked variant link (`_company-locked.html`), and the discovery date(s).
- A summary line: `N roles discovered (X active, Y excluded, Z closed). M ready to submit. P flagged for manual review.`
- A table of every opening from `openings-<YYYY-MM-DD>.json` with columns: `#`, `Title`, `Team`, `Location`, `Posted`, `Active`, `Final score`, `Status` (locked / baseline / flagged / closed / excluded), `Resume` (link to `<role-slug>/resume.html` if rendered, otherwise "-"), `JD` (link to original posting).
- A footer noting that the markdown sources live alongside each HTML file for editing.

The page uses the same self-contained HTML conventions as the resume template (single file, inline CSS, no external dependencies, no images). Styling is similar to the dashboard but tuned for navigation rather than charts:

- Same Source Serif Pro / Source Sans Pro family with system fallbacks
- Section-rule borders on header dividers
- Plain anchor styling, monochrome
- Status pill colors only for `Status` column (locked = green pill, baseline = blue, flagged = amber, closed = gray, excluded = gray strikethrough)

Announce in chat with the index path. This is the page the user will share or revisit when they want to pick which role to submit next.

### Stopping conditions for the secondary loop

The secondary loop is bounded -- it processes a finite set of roles per company. It stops when:
- All discovered roles have produced an opening-tailored variant or hit per-role budget
- User manually interrupts
- The per-role sub-budgets exhaust without locks AND no further productive mutations are visible

---

## step 7: write the changelog

After each experiment (whether kept or discarded), append to `changelog.md`:

```markdown
## Experiment [N] -- [keep/discard]

**Aggregate:** [previous]% -> [new]% (delta [+/-X.X])
**Per-profile deltas:** anthropic [prev->new], openai [prev->new], google-deepmind [prev->new]
**Mutation:** [One sentence describing what was changed -- which section, which bullet, what swap]
**Reasoning:** [Why this change was expected to help -- which gap from which profile(s)]
**Result:** [Which evals flipped -- which were now passing, which now failing]
**Remaining gaps:** [Brief description of what still fails, top 1-2 items]
```

This changelog is the most valuable artifact. It's a research log that any future agent (or smarter future model) can pick up and continue from. It also documents *why* a resume reads the way it does after the loop -- useful when the user is asked about specific bullet choices in interviews.

---

## step 8: deliver results

When the user returns or the loop stops, present:

1. **Primary-loop summary:** Baseline aggregate -> final aggregate. Per-profile lock status. Which companies locked, which didn't.
2. **Secondary-loop summary (per locked company):** Roles discovered, roles tailored, roles submission-ready at baseline, roles flagged for manual review (budget-exhausted or unfixable structural gaps).
3. **Total experiments run** across both loops, kept vs discarded.
4. **Top 3 mutations that helped most** (from `changelog.md` and per-role `sub-changelog.md` files).
5. **Per-profile remaining failure patterns:** What each company's recruiter subagent still flags as a gap -- these become interview-prep talking points.
6. **Submission-ready artifact list:** Full paths to every per-opening `resume.md`. Each is ready to submit to a real job application.
7. **The original resume is untouched.** All artifacts live in `<resume-parent-dir>/autowrite-<resume-slug>/` (working dir for primary loop) and `<resume-parent-dir>/applications/` (locked variants + per-opening submission artifacts).
8. **Profile cache state:** Which company profiles were researched fresh, which used cache; same for hiring-manager profiles.
9. **Location of `results.tsv`, `changelog.md`, `dashboard.html`, and per-company `results-openings.tsv`** for reference.

---

## output format

The skill produces artifacts in three sibling trees, all under `<resume-parent-dir>/`:

### 1. Company profile cache (reusable, co-located with the resume)

```
<resume-parent-dir>/profiles/
  anthropic.md                 # cached company profile (reusable across runs)
  openai.md
  google-deepmind.md
  ...
```

Profiles travel with the resume. If you have separate resume markdown files for different career tracks, each can have its own profile cache. To share across multiple resumes, put them in a common parent and use `../profiles/`.

### 2. Primary-loop working tree (mutation experiments and per-company variants in progress)

```
<resume-parent-dir>/autowrite-<resume-slug>/
  dashboard.html               # live browser dashboard (auto-refreshes)
  results.json                 # data file powering the dashboard
  results.tsv                  # score log for every primary-loop experiment
  changelog.md                 # detailed mutation log (primary loop)
  <resume-slug>-<company-slug>.md           # per-profile working file (one per active profile)
  <resume-slug>-<company-slug>.md.baseline  # revert target per profile
  recruiter-reports/
    experiment-000/
      anthropic.md
      openai.md
      ...
    experiment-001/
      ...
```

Each active profile gets its own working file so per-profile mutations do not contaminate each other once profiles begin to diverge.

### 3. Applications tree (locked variants + per-opening submission artifacts)

```
<resume-parent-dir>/applications/
  anthropic/
    _company-locked.md                 # company-canonical resume variant markdown source
    _company-locked.html               # print-ready variant -- open in browser, Ctrl+P to PDF
    openings-<YYYY-MM-DD>.json         # discovery cache (7-day lifetime)
    openings-<YYYY-MM-DD>.md           # human-readable opening index (active + excluded + closed)
    results-openings.tsv               # per-role score log
    index.html                         # company entry point: opening list + links to per-role resumes
    ai-engineer-applied/
      resume.md                        # opening-tailored variant markdown source
      resume.html                      # print-ready opening-tailored variant (SUBMIT THIS)
      hiring-manager-profile.md
      recruiter-report-baseline.md
      recruiter-report-final.md
      job-posting.md
      sub-changelog.md
    research-engineer-evals/
      ...
  openai/
    _company-locked.md
    _company-locked.html
    index.html
    ...
```

The `applications/` tree is the **final output surface** the user submits from. Each `resume.html` under a role slug is the print-ready submission artifact -- open in a browser, Ctrl+P / Cmd+P, Save as PDF. The markdown source sits next to it for re-editing if needed.

**The original resume is NEVER modified.** Mutations happen on the working files in the primary-loop tree. Locked variants and opening-tailored variants live in the `applications/` tree. The user reviews, diffs, and manually applies changes if they choose. Do NOT offer to overwrite the original. Do NOT copy a working file over the original.

---

## example: full end-to-end run with lock-and-branch + secondary loop

*The example below walks through an AI-engineering job search to illustrate the flow. The same loop, lock behavior, and secondary-loop structure apply to any industry -- construction, IT operations, game development, skilled trades, creative production, etc. The only differences across industries are the source-prioritization heuristics the research subagent uses (covered in `references/research-subagent-prompt.md`) and the eval shapes that come out of the research (covered in `references/eval-guide.md`).*

**Context gathered:**
- Target resume: `<resume-parent-dir>/revisions/2026-05-12-draft.md`
- Targets: ["Anthropic", "OpenAI / Applied", "xAI"]
- Runs per experiment: 1
- Budget cap: 10 primary mutations, 5 sub-mutations per role
- Profile refresh: no (use cache if available)

### Primary loop

**Step 2 -- Profile resolution.** No cached profiles exist at `<resume-parent-dir>/profiles/`. Three research subagents spawn in parallel. Each returns a profile (Anthropic: 11 evals, OpenAI: 12 evals, xAI: 10 evals).

**Step 4 -- Baseline (experiment 0):**
- Anthropic 100.0% (11/11)
- OpenAI 75.0% (9/12)
- xAI 50.0% (5/10)
- Aggregate 75.0%

**Experiment 0.5 -- Anthropic over-alignment check (auto-triggered).** Anthropic baseline = 100%; the safeguard would normally auto-add a triangulation profile, but OpenAI and xAI are already in the active pool, so no extra profile is added. Anthropic LOCKS immediately (3 hypothetical consecutive runs at 100% is trivially satisfied for an already-perfect profile -- the skill treats baseline 100% as 1-of-3 consecutive and waits for 2 more confirmations across experiments 1-2 before locking). Conservative behavior: Anthropic doesn't lock until experiment 2 confirms.

**Experiment 1 -- KEEP for OpenAI (75% -> 83.3%), no change for Anthropic/xAI:**
Mutation: Added a guardrails/safety bullet to the Meta section covering per-stage tool allowlists, sandboxed shell execution, and human-on-the-loop approval gates.
Reasoning: OpenAI's recruiter flagged "no observability or safety language despite shipping agent infra." Mutation honestly names work that was actually done.
Result: OpenAI flipped 1 eval to pass. Anthropic and xAI unchanged.

**Experiment 2 -- KEEP for xAI (50% -> 60%):**
Mutation: Added "concurrent multi-agent job execution against a SQL-backed queue" framing to the Rust orchestration server bullet.
Reasoning: xAI's recruiter flagged concurrency/scale framing as missing. The work exists; the resume just didn't name it that way.
Result: xAI flipped 1 eval to pass. Anthropic and OpenAI unchanged. **Anthropic LOCKS** (now confirmed 3 consecutive at 100%). Saves `applications/anthropic/_company-locked.md`. Removes anthropic from active pool.

**Experiments 3-7:** Active pool is OpenAI + xAI. Mutations target each in turn.

**Experiment 5 -- OpenAI LOCKS** (3 consecutive ≥90% confirmed). Saves `applications/openai/_company-locked.md`.

**Experiment 8 -- xAI hits budget.** xAI plateaued at 70% (3 evals are structurally unfixable: Colossus experience, RL training at scale, 100k+ GPU). xAI does NOT lock. Surfaced in chat as "xAI variant flagged for manual review; structural gaps are not addressable via resume mutation."

### Secondary loop (per locked company)

**6a -- Anthropic openings discovery:** Job-openings subagent returns 4 plausible roles. User confirms via dashboard.

**6b/6c/6d -- Per-role processing (parallel across 4 roles):**
- `ai-engineer-applied`: baseline 91.7% against hiring-manager profile. Already above lock threshold. No sub-mutations. `resume.md` = `_company-locked.md` verbatim.
- `research-engineer-evals`: baseline 80.0%. 2 sub-mutations. Locks at 93.3%.
- `member-of-technical-staff`: baseline 86.7%. 1 sub-mutation. Locks at 93.3%.
- `infrastructure-engineer`: baseline 71.4%. 5 sub-mutations exhaust budget at 78.6%. Flagged for manual review.

**6a -- OpenAI openings discovery:** 6 roles returned. Repeat per-role processing.

### Final delivery
- 3 company profiles researched; 2 companies locked (Anthropic, OpenAI), 1 flagged (xAI)
- 8 primary-loop experiments, 5 kept, 3 discarded
- 10 opening-tailored variants across Anthropic and OpenAI; 8 submission-ready, 2 flagged for manual review
- 18 hours of recruiter-equivalent work compressed into a 1-hour autonomous run
- Top primary mutations: guardrails bullet, concurrency framing
- Remaining gaps captured per-role in `recruiter-report-final.md` files for interview prep

---

## the test

A good autowrite run:

1. **Started with a baseline across multiple profiles** -- never mutated anything before measuring. Single-target invocations were auto-triangulated unless explicitly opted out.
2. **Used binary evals only** -- every eval in every profile (company or hiring-manager) is yes/no. No scales. No vibes.
3. **Changed one thing at a time** -- so the changelog is causal, not correlative.
4. **Branched mutations per profile after divergence** -- once profiles' bars diverge, working files split so per-company mutations don't contaminate each other.
5. **Kept a complete log** -- every experiment recorded with per-profile deltas. Per-role sub-mutations also logged.
6. **Spawned subagents in parallel** -- baseline scoring across N profiles, per-experiment re-scoring across active profiles, openings discovery per locked company, hiring-manager profile generation per role, opening-level scoring per role. The parallel design is the whole architecture.
7. **Locked per-profile when consecutive ≥90% confirmed** -- did not chase incremental gains on profiles that had already converged. Locked variants saved as company-canonical artifacts and removed from the active pool.
8. **Ran the secondary loop on each locked variant** -- discovery, hiring-manager profile, per-opening scoring, sub-mutation loop. Outputs are submission-ready per role.
9. **Did not overfit** -- the resume got better at getting interviews at these specific companies and these specific roles, not just at passing test evals.
10. **Ran autonomously, human-on-the-loop** -- did not stop to ask permission between experiments; did not pause when the operator was away. Surfaced state in chat at key transitions (profile locks, role completions) so the operator could pick up the trace on return.

If a resume "passes" all evals but doesn't actually read better -- the evals are bad, not the resume. Go back to step 2 and re-research with explicit feedback to the research subagent.

---

## how this connects to other tools

**What feeds into autowrite:**
- A resume markdown file (the artifact under test)
- Company names (the primary-loop targets)
- Optional: cover letter drafts, LinkedIn summary, personal site copy -- can be passed through the same loop with profile evals tailored to that surface

**What autowrite feeds into:**
- **The applications tree:** submission-ready per-opening resumes. Each `<resume-parent-dir>/applications/<company>/<role>/resume.md` is ready to attach to a real job application.
- **Locked company variants:** the canonical per-company resume revisions. Use these as the starting point for any new role at that company that surfaces later.
- **The cached profiles:** reusable on next run. As long as the resume's surface doesn't change radically, re-running autowrite with the same target companies will hit the cache and skip re-research.
- **The changelog and sub-changelogs:** an explanation of why your resume reads the way it does at each level (company-canonical and per-opening). Valuable when prepping for interviews -- you know which mutations were applied for which role and why.
- **The per-profile and per-role remaining-gaps lists:** interview-prep talking points. You know in advance what each company will probe and what each specific hiring manager flagged.
- **The discovery cache:** `openings-<date>.json` files document which roles existed when. Useful for tracking how a company's hiring direction evolves over time.
