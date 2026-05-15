# Company Profile Template

Every cached profile under `<resume-parent-dir>/profiles/<slug>.md` must follow this schema. A research subagent produces a file matching this template; a recruiter subagent reads it to know how to score. Profiles cache co-located with the resume markdown they're scored against -- not in the plugin tree.

The skeleton below is the canonical structure. Do not add sections that aren't here; do not remove sections that are. Empty a section only if no information was found -- and flag that explicitly with "Not found during research; revisit on profile refresh."

---

## skeleton

```markdown
---
name: <slug>
company: <Full Company Name>
role_qualifier: <optional, e.g., "AI Engineer / Applied Research" or "any">
researched_at: <ISO 8601 date, e.g., 2026-05-12>
sources:
  - <URL or short citation>
  - <URL or short citation>
---

# <Full Company Name>

## Hiring values

Bullet list of 3-6 explicit hiring values, drawn from public sources (engineering blog, "what it's like to work here" pages, hiring manager interviews, careers page). Each bullet should be one sentence and cite the source inline if non-obvious.

## Technical bar

What this company screens for at the role level. 4-8 bullets. Be specific -- "ships systems end-to-end" beats "strong engineering"; "delivers commercial projects under $5M without surprises" beats "good PM." Reference any named archetypes the company is hiring for if you can find them in their materials.

## Recent strategic priorities

What is this company investing in *right now* (within the last ~6 months)? Look at product launches, hiring posts, research focus areas, leadership statements. 3-6 bullets. This is the section most likely to go stale -- it's why profiles cache but support refresh.

## Anti-patterns / red flags

What this company explicitly does NOT hire for, or what gets resumes rejected. 3-6 bullets. Draw from interview reports, engineering blog "what we don't do" posts, hiring manager statements.

## Binary eval criteria

6-12 evals, each in the format defined in [eval-guide.md](eval-guide.md). Numbered. Each must be:
- Binary yes/no
- Specific enough that two recruiter subagents would agree
- Tied to this company's actual signals
- Not gameable by trivial keyword stuffing

```

EVAL 1: <Short name>
Question: <Yes/no>
Pass: <Specific>
Fail: <Specific>
Source: <Where this came from>

EVAL 2: ...

```

## Scoring notes

Any additional context for the recruiter subagent about *how* to score this company specifically. Examples:
- "This company weights research artifacts heavily; if the resume cites a paper or draft, lean toward passing the related eval."
- "This company is highly skeptical of cross-functional/managerial language for IC roles; treat such language as failing the IC-fit eval."

This section is optional. Use it only when scoring nuance can't be captured cleanly in the eval pass/fail definitions.

```

---

## validation checklist

Before saving a profile, the autowrite loop validates:

- [ ] All sections present and non-empty (or explicitly flagged as "not found")
- [ ] 6 to 12 evals (no fewer, no more)
- [ ] Every eval is binary yes/no
- [ ] At least 3-4 evals are clearly company-specific (would not appear unchanged in another company's profile)
- [ ] Each eval has a `Source:` line citing a real, current public signal
- [ ] `researched_at` date is set
- [ ] `sources` frontmatter lists at least 3 URLs or citations

If any of these fail, the loop re-spawns the research subagent with the validation feedback.

---

## example profiles (sketches only -- not real research)

Two examples in two different industries to show the same schema applies broadly.

### Example A: research-driven tech company (AI engineering hire)

```markdown
---
name: <slug>
company: <Tech Company>
role_qualifier: AI Engineer
researched_at: <YYYY-MM-DD>
sources:
  - <careers page URL>
  - <engineering blog URL>
  - <hiring manager interview citation>
---

# <Tech Company>

## Hiring values
- Treats AI safety as a first-class engineering concern, not a separate function.
- Selects for thoughtfulness about LLM limitations over raw output speed.
- Hires generalists who can pivot across infra, eval, and product work.

## Technical bar
- Ships systems end-to-end, including the messy operational parts.
- Demonstrates eval fluency -- can describe specific eval methodologies they've used.
- Familiar with research literature on the company's active areas.

## Binary eval criteria

EVAL 1: Multi-agent shipping evidence
Question: Does the resume describe a multi-agent system the candidate built and shipped in the last 18 months?
Pass: A specific system named, with deployment surface and adoption signal.
Fail: Only generic "agentic AI" framing.
Source: <citation>

(...further evals follow the same pattern)
```

### Example B: large general contractor (construction PM hire)

```markdown
---
name: <slug>
company: <Construction Firm>
role_qualifier: Senior Project Manager
researched_at: <YYYY-MM-DD>
sources:
  - <careers page URL>
  - <industry publication / project case study URL>
  - <hiring manager LinkedIn post citation>
---

# <Construction Firm>

## Hiring values
- Selects PMs who run jobs to schedule and budget without escalation drama.
- Prefers candidates with experience in the specific subtrade and jurisdiction (commercial vs. residential, union vs. open shop, target market segment).
- Hires for client-facing maturity as much as technical PM skills.

## Technical bar
- Has delivered projects at or above the firm's typical scale ($X-$Y range; team size N+).
- Holds current OSHA-30 and any state-specific certifications.
- Familiar with the schedule and cost-control tools the firm uses (Procore, Primavera, MS Project, etc.).

## Binary eval criteria

EVAL 1: Project-scale evidence
Question: Does the resume describe at least one delivered project of comparable scale (budget, duration, crew size) to the firm's typical engagement?
Pass: A specific project named with two or more quantified scale dimensions and a delivered outcome.
Fail: Only project counts or general scope descriptions without scale dimensions.
Source: <citation: firm's project portfolio page or job posting>

(...further evals follow the same pattern)
```

Both examples use the same schema. The differences are in the *signals* (what the company actually cares about) and the *examples in each eval's Pass/Fail clauses* (specific to the role's measurable artifacts). The shape -- frontmatter, sections, binary evals with sources -- is identical.

---

## maintenance

A cached profile is good for ~3 months. After that, refresh it -- companies' strategic priorities shift, especially in AI. The autowrite loop accepts a `profile_refresh: true` flag in step 1 to force re-research even when a cached file exists.
