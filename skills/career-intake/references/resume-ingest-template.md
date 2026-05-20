# Round 0: Resume ingestion template

Use this template when the candidate provides an existing resume to `/career-intake`. Round 0 runs **before** the interactive Q&A plan: it parses the resume into seeded `bullets/` files (per role + skills + projects), writes a single session log, and asks the candidate one structured question to decide whether deeper Q&A is warranted.

The point of Round 0 is to avoid throwing away what the candidate already wrote down. The default flow used to be "ask everything from scratch even if a resume exists" -- that wastes the candidate's time when the resume is already in decent shape, and it disrespects the bullets the candidate has been iterating on. With Round 0, the resume becomes the lightweight knowledge-base seed; the Q&A rounds only fire on roles the candidate explicitly flags as under-documented.

This template is read by career-intake's SKILL.md Step 1.5. It is not a subagent prompt; the parent skill performs the ingestion directly using `Read`, `Write`, and the AskUserQuestion tool.

---

## When Round 0 fires

- The user invoked `/career-intake` AND provided an existing resume path (gather-context field 3).
- The resume is markdown OR PDF. PDF goes through the same PDF intake autowrite uses at its Step 1.0 (see `../../autowrite/SKILL.md` Step 1.0 -- read the PDF, convert to markdown, save alongside the PDF as `<stem>.md`). The candidate's `output-dir` is the destination for downstream artifacts regardless of where the PDF lives.
- The output directory does NOT already contain seeded bullets from a prior Round 0 (the marker line below is absent or the user passed `re_ingest: true`).

If the user did not provide a resume, skip Round 0 entirely and proceed with the existing 5-round Q&A flow as defined in the rest of SKILL.md.

## When Round 0 is skipped on re-invocation

If `<output-dir>/bullets/` already contains files written by a prior Round 0 (detected by the marker line `<!-- career-intake:round-0-seed -->` at the top of any seeded bullets file), skip the parse step and proceed directly to the round selection question. Announce in chat:

> Seeded bullets from a prior Round 0 detected at `<paths>`. Skipping re-ingestion. If the resume changed and you want to re-seed, re-invoke with `re_ingest: true` (existing seeded files will be overwritten; appended interview bullets under `## From interview <date>` headings will be preserved).

When `re_ingest: true` is set, overwrite ONLY the lines above the first `## From interview` heading in each per-role bullets file. Lines from `## From interview <date>` onward come from later Q&A rounds and must never be discarded by a re-ingest.

## Parse contract -- what to extract from the resume

The resume is the source of truth for both content AND structure. Mirror it; do not invent.

Read the entire resume markdown and identify the following:

### 1. Roles

A "role" is any block under the resume's Experience / Work Experience / Professional Experience / Career History section (use the candidate's actual section name). Each role has:

- **Title** (the role heading, e.g., "Information Security Engineer", "Senior Project Manager")
- **Company** (the employer, e.g., "Meta", "Turner Construction")
- **Dates** (start - end or start - "Present")
- **Slug** (derived: lowercase, hyphenated, drop punctuation; format `<role-or-team>-<company>` shortened to a recognizable form -- examples: `meta-ise`, `apple-tech-writer`, `snap-ar-lead`, `turner-spm`). The slug must be filename-safe and unique within the resume.

Build an in-memory list `roles[]` with one entry per role. Order is the resume's order (most recent first by convention, but mirror whatever the resume uses).

A role is the **current role** if its end date is "Present" or empty AND it is the most-recent entry in the resume's experience section. Note this in the role's metadata -- it is the only role whose seed file gets the `current_role: true` field.

### 2. Projects

A "project" is any entry under the resume's Personal Projects / Selected Work / Portfolio / Projects section. Each project has:

- **Name** (the project heading)
- **One-line description** (whatever framing the candidate used)
- **Bullets** (the project's bulleted body)

A single combined `bullets/_projects.md` holds all projects in resume order. Do not split projects into one-file-per-project; the resume's Projects section is itself a section, not a per-item collection.

### 3. Skills

Any content under the resume's Skills / Technical Skills / Tools & Stack / Competencies section. The shape varies:

- Grouped bullets ("**Languages:** Python, Rust, ..." / "**Frameworks:** ...")
- Flat list
- Tag cloud
- Categorized blocks with sub-headings

Preserve the candidate's structure exactly. A single `bullets/_skills.md` holds the skills section verbatim.

### 4. Summary (if present)

The opening summary / objective / professional-summary block above the experience section. If present, include it as a `## Summary (from resume)` block at the top of the resume-ingest session log. Do not create a `bullets/_summary.md` -- the summary is the candidate's overall framing, not a per-section asset, and it lives in the session log so the candidate can revisit it during round selection.

### 5. Education

Any content under the resume's Education section. Capture as a single `bullets/_education.md` block, verbatim from the resume. The Q&A rounds may or may not touch education depending on round selection.

### Anything else

Custom sections (Patents, Press, Talks, Certifications, etc.) get one `bullets/_<section-slug>.md` file per section, verbatim. The resume's section names drive the slug.

## Output -- the seeded knowledge base

After parsing, write the following files (creating parent directories as needed):

```
<output-dir>/
  bullets/
    <role-slug-1>.md            # one per role from experience section
    <role-slug-2>.md
    ...
    _skills.md                  # verbatim skills section
    _projects.md                # verbatim projects section (or absent if no Projects section)
    _education.md               # verbatim education section (or absent if no Education section)
    _<custom-section-slug>.md   # one per non-standard section (Patents, Press, etc.)
  interview-notes/
    <YYYY-MM-DD>-resume-ingest.md   # session log following the resume-ingest variant in session-template.md
```

### Per-role bullets file shape

Each `bullets/<role-slug>.md` looks like:

```markdown
<!-- career-intake:round-0-seed -->
---
role_title: <Full title from resume>
company: <Company name from resume>
dates: <Start> - <End or "Present">
slug: <role-slug>
current_role: <true | false>
seeded_from: <relative path to the resume markdown>
seeded_at: <YYYY-MM-DD>
---

# <Role title> -- <Company> (<dates>)

<Verbatim copy of the role's bullets from the resume, in the resume's order. Each bullet kept as a single line under a `-` marker. Bold / italic / inline code preserved.>

<If the role had a leading paragraph (some resumes use a sentence before the bullets), include it above the bullet list as a paragraph block.>
```

The marker line `<!-- career-intake:round-0-seed -->` is the re-ingest detection signal. Do NOT omit it.

The frontmatter is read by downstream tools (currently informational; autowrite Step 1.1 may consume it later for source attribution). Format must be valid YAML.

If a role had no bullets in the resume (just a title + dates), still create the file with the frontmatter and a body of `<!-- no bullets in source resume; pending Round X Q&A -->`. The file presence is what matters; the candidate may later flag this role for depth.

### _skills.md, _projects.md, _education.md shape

Each is a single markdown block with the marker line and one-line frontmatter, then the section verbatim from the resume:

```markdown
<!-- career-intake:round-0-seed -->
---
section: <Resume's exact section name, e.g., "Technical Skills">
seeded_from: <relative path to the resume markdown>
seeded_at: <YYYY-MM-DD>
---

<Verbatim section content from the resume, preserving headings, lists, paragraph structure.>
```

No interpretation. No reorganization. The resume's chosen shape is the shape.

### Session log shape

Write `<output-dir>/interview-notes/<YYYY-MM-DD>-resume-ingest.md` following the **resume-ingest variant** in `session-template.md`. Key sections to populate:

- A summary of what was parsed (count of roles, projects, sections; the role list with slugs).
- The "Resume parse summary" block (variant replaces the normal Q&A block; see session-template.md).
- The candidate's chosen branch from the AskUserQuestion below (up-to-date / needs-depth / other).
- If the candidate chose `needs-depth`, the role(s) they flagged.

## The decision question -- AskUserQuestion

After writing the seeded files but before any Q&A round runs, post a single `AskUserQuestion` with the following shape:

```
Question: "I've parsed your resume into a starting knowledge base (<N> roles, <P> projects, <S> custom sections). Is this resume up to date, or does it need more depth on specific roles? The current role typically holds the most engram-locked detail -- the things you remember vividly but didn't write down."

Header: "Resume depth"
multiSelect: false
Options:
  1. "Up to date -- finalize draft from seeded bullets" (Recommended when the resume was recently updated with detail.)
     Description: "Skip the Q&A rounds. I'll assemble a `revisions/<date>-draft.md` from the seeded bullets (effectively a verbatim copy of the resume) and hand off to autowrite."
  2. "Needs depth on these roles" (multi-select within this option via a follow-up if necessary)
     Description: "Pick one or more roles whose bullets feel thin. I'll narrow the planned rounds to focus on those roles only. The other roles' seeded bullets stay as the resume left them."
  3. "Re-run Round 0 -- I'd like to see what was parsed first"
     Description: "Show me the seeded bullets in chat so I can check what was captured before deciding."
```

Wait for the candidate's answer. Do not proceed to round selection until they have chosen.

### Up-to-date branch

If the candidate chose option 1:

1. Announce in chat: "Marking the resume as up-to-date. Skipping the interactive Q&A rounds. Assembling the draft now."
2. Jump to SKILL.md's existing **Step 3** (after 5 rounds, generate a draft), but with this modification: pull bullets directly from the seeded `bullets/*.md` files instead of from interview-driven rounds. The resulting `revisions/<YYYY-MM-DD>-draft.md` will be effectively a verbatim copy of the original resume, but it lives under the `revisions/` directory so the hand-off path to autowrite is uniform across both branches.
3. Skip Step 4's "loop or hand off" prompt's loop-back option (no rounds happened, so there's nothing to loop back to) and present only the revise-current-draft and hand-off-to-autowrite options.

### Needs-depth branch

If the candidate chose option 2:

1. Present a multi-select follow-up listing the parsed role titles (and "Other (specify)" for roles that didn't get an entry, e.g., a side-project lead that wasn't in the resume's experience section). The role list comes from the in-memory `roles[]` parsed at the top of Round 0.
2. Wait for the candidate to pick one or more roles.
3. **Narrow the planned 5-round set** to focus on the selected roles:
   - If the candidate's current role is selected: include the "Current role" round from `interview-rounds.md`.
   - If a past role is selected: include the "Specific past-role deep-dive" round (from `interview-rounds.md`) for that role; the opening question is the templated "Tell me about your work at [previous company]. Same shape as the Current Role round, but for a role you've already left."
   - If multiple roles are selected: run one round per selected role (so 2 selections = 2 rounds, 3 selections = 3 rounds). The Q&A pacing remains one question at a time, one round at a time.
4. **Drop overlapping rounds from the default 5-round set**: if the candidate selected the current role, the Career Arc / Flagship Project / Skills+Behavioral / Personal Projects rounds are downgraded to optional -- the candidate decides which (if any) to add in Step 4's loop prompt. The default for a needs-depth flow is to run ONLY the selected-role rounds, not the full default 5. If the candidate later wants more breadth, they can add rounds via Step 4's loop-back option.
5. Proceed to SKILL.md's existing **Step 2** (conduct each round), running only the narrowed set.

### Re-run-Round-0 branch

If the candidate chose option 3:

1. Post a chat message summarizing what was parsed: the role list with slugs, the project list, the custom sections list. Include a one-line note per role (the first bullet, or "no bullets" if empty).
2. Re-present the AskUserQuestion from above with only options 1 and 2 (drop option 3 since they already chose to review). Wait for their new answer and branch as above.

## How Round 0 output interacts with later Q&A rounds

When a Q&A round (e.g., "Current role") runs against a role whose seeded bullets file already exists, the round's locked bullets are **appended** to the same file under a dated subheading:

```markdown
<!-- career-intake:round-0-seed -->
---
role_title: ...
...
---

# <Role title> -- <Company> (<dates>)

<Original seeded bullets from the resume.>

## From interview <YYYY-MM-DD>

<New bullets locked at the end of this Q&A round.>

<If multiple Q&A rounds happen on the same role on different dates, append additional `## From interview <date>` blocks chronologically. Never overwrite an earlier interview block.>
```

The seeded bullets stay intact as a fallback layer. Downstream consumers (autowrite Step 1.1) see one file per role with full provenance: what the resume said + what the candidate added across each interview. The `## From interview` heading is also the discriminator for `re_ingest: true` -- everything below the first such heading is preserved across re-ingests.

If a Q&A round runs against a role that does NOT have a seeded bullets file (i.e., the candidate flagged a role via "Other (specify)" that wasn't in the resume's experience section), create the file fresh with the marker line, the frontmatter (using `seeded_from: <none -- added via Round X Q&A on YYYY-MM-DD>` and `seeded_at: <YYYY-MM-DD>`), no body bullets above the interview heading, and the `## From interview <YYYY-MM-DD>` block holding the locked bullets.

## Hard constraints

- **Never modify the original resume markdown.** Round 0 only reads it; the seeded files are independent artifacts.
- **Never delete or overwrite content below a `## From interview` heading**, even when `re_ingest: true` is set. The interview blocks are higher-fidelity than the seed.
- **Preserve the candidate's framing verbatim.** Round 0 is not the place to rewrite bullets, smooth out phrasing, or "fix" the resume. The Q&A rounds are where that work happens, on the candidate's terms.
- **No quantification you didn't see in the resume.** If a bullet says "contributed to a 3x improvement," the seed file says "contributed to a 3x improvement" -- not "drove" and not "led."
- **No fabricated metadata.** If the resume doesn't list a date range for a role, the seed's frontmatter has `dates: <unknown>` and a note in the body. Do not infer from context.
- **One file per role from the experience section.** Even if a role is short or undated, give it its own file -- the slug is its identifier across the system.

## Tone in announcements

The chat messages around Round 0 should feel like a research assistant briefing the candidate on what was extracted. Not theatrical, not apologetic. State what was parsed, surface the question, wait. Examples:

> Round 0 starting. Parsing `~/career/resume-2026-05-12.md`.

> Round 0 complete. Parsed 5 roles, 3 personal projects, and 1 Education section. Seeded files at `~/career/bullets/` and `~/career/interview-notes/<date>-resume-ingest.md`.

> Now -- one question before I plan the Q&A rounds.
