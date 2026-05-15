# Research subagent prompt template

Use this template when spawning a research subagent (via the Agent tool) to build a new company profile. Fill in the bracketed values before invoking. The subagent's job: gather hiring signals for one target and produce a profile markdown file that matches the schema in `profile-template.md`.

---

## Invocation pattern

Tool: `Agent`
`subagent_type`: `Explore` (read-only web access via WebSearch/WebFetch is sufficient; no file edits needed since the parent skill writes the profile file)
`description`: `Research <Company> hiring profile`
`run_in_background`: `false` (parent skill needs the result to proceed)

`prompt`:

```
You are researching a company hiring profile for a resume-evaluation tool called autowrite. Your job is to gather public hiring signals for one specific company and produce a structured profile that will later be used by a recruiter subagent to score resumes.

**Target company:** [COMPANY NAME]
**Role qualifier:** [ROLE QUALIFIER -- or "any" if no specific role]

**Your output:** A profile markdown body matching the schema below. Return ONLY the markdown body (no preamble, no postamble). The parent skill will save it to disk and validate it.

## Where to look

Search for the following, in approximate order of signal value:

1. **The company's own careers / engineering / culture pages.** Especially: job postings for the target role, "what it's like to work here" content, hiring philosophy statements, "how we hire" posts.
2. **Engineering blog posts** from the last ~12 months. Look for posts that describe what the team builds, what tools they use, what kinds of problems are interesting to them.
3. **Public statements from hiring managers, founders, or senior ICs.** Twitter/X threads, LinkedIn posts, podcast interviews, conference talks. These often reveal what they actually screen for in ways the official careers page doesn't.
4. **Recent product launches or research releases.** These tell you what the company is *currently* investing in, which is more predictive than their general "we hire smart people" framing.
5. **Reputable interview reports.** Sites like levels.fyi, Glassdoor, or candidates posting interview experiences. Treat with skepticism (small sample, self-selection) but useful for spotting anti-patterns.

Use WebSearch first to identify URLs, then WebFetch to read the most signal-dense ones. Do not over-index on a single source.

## What to produce

A profile markdown body in this exact schema (no other top-level sections):

---
name: <slugified company name, e.g., "anthropic" or "openai-applied-research">
company: <Full Company Name>
role_qualifier: <ROLE QUALIFIER value, or "any">
researched_at: <today's date in YYYY-MM-DD format>
sources:
  - <full URL>
  - <full URL>
  - <full URL or short citation>
---

# <Full Company Name>

## Hiring values
- (3-6 bullets, drawn from public statements)

## Technical bar
- (4-8 bullets)

## Recent strategic priorities
- (3-6 bullets, biased toward the last ~6 months)

## Anti-patterns / red flags
- (3-6 bullets)

## Binary eval criteria

EVAL 1: <Short name>
Question: <Yes/no question about whether a resume passes this criterion>
Pass: <Specific positive condition>
Fail: <Specific negative condition>
Source: <which of the sources above this comes from>

EVAL 2: ...

(...continue to between 6 and 12 evals, inclusive)

## Scoring notes
(Optional. Use only if scoring requires nuance that can't be captured in pass/fail definitions. Otherwise omit this section entirely.)

## Constraints

- **Between 6 and 12 evals.** Fewer than 6 is too thin; more than 12 invites gaming.
- **Every eval must be binary yes/no.** No scales, no "rate 1-5," no compound conditions. If an eval is compound, split it into two.
- **At least 3-4 evals must be clearly company-specific.** A reader should be able to tell which company this profile is for from the evals alone. Generic SWE evals don't count toward this minimum.
- **Each eval needs a `Source:` line** citing a specific URL or interview/post that justifies it. If you can't cite a source, the eval shouldn't exist.
- **No invention.** Don't write evals based on what *should* be true of this company. Write evals based on what their public signals actually show.
- **No hype mirroring.** Don't reproduce the company's own marketing back at the profile (e.g., "Values curiosity and excellence" -- that's table stakes everywhere and adds no signal). Translate values into observable resume signals.
- **No emojis.** No markdown beyond what's shown in the schema.

## When you have low confidence

If you can't find enough public signals to write 6 strong evals, return a partial profile with a `## Research limitations` section at the bottom explaining what wasn't findable. The parent skill will surface this to the user and decide whether to use the partial profile or skip the target.

## Output

Return the markdown body only. The parent skill will save it. Do not include explanation text outside the markdown.
```

---

## Tuning notes (source prioritization heuristics by company shape)

Infer the company shape from the user's invocation and the resume. The same five source types weigh differently depending on shape:

- **Large established organizations** (multi-thousand-employee enterprises, public companies, government agencies, large institutions): Source #1 (specific job postings) carries the most weight -- the official posting is the literal job spec and the company has the process maturity for postings to be accurate.
- **Specialist or research-driven organizations** (research labs, R&D-heavy companies, specialist consultancies): prioritize Sources #1, #2, and #3. Public statements from senior practitioners are unusually high-signal because they explicitly describe what they look for, and the careers page often understates the bar.
- **Early-stage or rapidly-changing organizations** (startups, scale-ups, organizations in active reorg): Source #4 (recent product / project launches / press releases) carries more weight than careers pages -- job descriptions are often stale relative to what the team is actually building.
- **Distributed or hands-on organizations** (construction firms, agencies, trades, field-services companies): Source #1 (job postings) and Source #5 (interview reports / community forums in the industry) carry the most weight. Engineering-blog equivalents may not exist; substitute industry publications, trade journals, or relevant professional associations.

Examples of inferring shape from the invocation:

- "Anthropic" + AI-engineer-shaped resume → specialist research-driven; prioritize Sources #1-3.
- "Turner Construction" + construction-PM-shaped resume → large established; prioritize Source #1 plus industry-association references.
- "<10-person startup>" + generalist-engineer resume → early-stage; prioritize Source #4 plus founder statements.
- "<Game studio>" + game-dev resume → varies by studio size; for AAA studios use large-established heuristic, for indies use early-stage.

If the company has multiple distinct hiring tracks (research vs applied vs product; commercial vs residential; healthcare specialty vs generalist), and the user did not specify a role qualifier, default to whichever track is most prominent in current hiring posts and note that choice in the `## Scoring notes` section.
