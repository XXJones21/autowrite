# Hiring-manager profile subagent prompt template

Use this template when spawning a hiring-manager profile subagent (via the Agent tool) to produce a role-scoped profile for one specific job opening. Output is structurally identical to a company profile (same schema in `profile-template.md`) so the recruiter subagent can score against it without modification.

A hiring-manager profile differs from a company profile in scope: it blends company-bar signals (inherited from the company profile, with attribution) with JD-derived signals specific to this exact role. The eval set is 8-15 evals (vs. company-profile's 6-12), with 4-6 inherited company evals and the remaining 4-9 derived from this JD.

---

## Invocation pattern

Tool: `Agent`
`subagent_type`: `Explore` (read-only; needs WebFetch to pull the JD if not already cached as markdown)
`description`: `Build hiring-manager profile for <Company> / <Role>`
`run_in_background`: `false` (parent loop spawns recruiter immediately after to score the locked resume)

`prompt`:

```
You are building a hiring-manager profile for one specific job opening. The output is a profile markdown file structurally identical to the company profile, but scoped to this specific role. Downstream, a recruiter subagent will use this profile to score the candidate's locked resume against the role.

**Target company:** [COMPANY NAME]
**Role title:** [ROLE TITLE]
**JD URL:** [URL]
**Discovery date:** [YYYY-MM-DD]

**Company profile (full markdown -- for inheriting company-level evals):**

<<<COMPANY PROFILE BEGIN>>>
[COMPANY PROFILE MARKDOWN PASTED INLINE]
<<<COMPANY PROFILE END>>>

**Job description (full markdown extract):**

<<<JD BEGIN>>>
[JD MARKDOWN PASTED INLINE -- or fetch from URL above if not provided]
<<<JD END>>>

Your output: A profile markdown body matching the schema in profile-template.md, with the additions noted below. Return ONLY the markdown body. The parent skill will save it.

## Frontmatter

```
---
name: <company-slug>-<role-slug>
company: <Full Company Name>
role_qualifier: <Full role title>
jd_url: <URL>
hiring_manager_view: true
parent_company_profile: <company-slug>
researched_at: <YYYY-MM-DD>
sources:
  - <JD URL>
  - <any additional company-blog or hiring-post URLs referenced>
---
```

The `hiring_manager_view: true` flag signals to the recruiter subagent that it should assist *the hiring manager for this specific role*, not a generalist company recruiter. The recruiter prompt template handles the scope-switch on this flag.

## Body sections (same as company profile, role-scoped)

### Hiring values
- 3-6 bullets. Lead with values the JD itself emphasizes (read the "what we're looking for" or "you'll thrive here" sections of the JD). Then fall back to company-level values from the company profile. Each bullet should be one sentence with the source cited inline if non-obvious.

### Technical bar
- 4-8 bullets. The first 2-3 should be inherited from the company profile (the company-bar). The remaining bullets are role-specific, drawn from the JD's "responsibilities" and "requirements" sections.

### Recent strategic priorities
- 3-6 bullets. Mostly inherit from the company profile. Add 1-2 role-specific priorities if the JD explicitly references a current initiative ("we're building X to solve Y").

### Anti-patterns / red flags
- 3-6 bullets. Inherit company-level red flags. Add any JD-specific anti-patterns (e.g., if the JD says "this is not a research role" but the resume reads as research-heavy, that's an anti-pattern to flag).

### Binary eval criteria

**8 to 15 evals total**, in this composition:

- **4-6 inherited company evals.** Copy verbatim from the company profile's eval list (with the same numbering re-anchored). Each must include an `Inherited from: company profile` note appended to the Source line.
- **4-9 role-specific evals derived from the JD.** Each must cite a specific JD passage in the Source line (e.g., `Source: this JD URL, "responsibilities" section: "Build evaluation harnesses for production agentic systems"`).

Format each eval exactly as in profile-template.md:

```
EVAL [N]: <Short name>
Question: <Yes/no question about the resume>
Pass: <Specific positive condition>
Fail: <Specific negative condition>
Source: <citation; for inherited evals, also note "Inherited from: company profile">
```

JD-derived evals must NOT:
- Test for skills the JD does not name (do not invent requirements)
- Be vague ("seems experienced") -- if the JD lists a specific responsibility, the eval asks whether the resume demonstrates that specific responsibility
- Duplicate inherited evals -- if the JD restates a company-bar signal, the inherited eval covers it; don't double-count

### Scoring notes (optional)

Include a `## Scoring notes` section ONLY if there's role-specific nuance the recruiter needs. Examples:
- "This role is on the Applied team, not Research; weight production-engineering evidence over research artifacts."
- "JD emphasizes evaluation methodology twice; treat eval-related evals as load-bearing for this role."

## Constraints

- **8-15 evals.** Fewer than 8 means you under-extracted from the JD; more than 15 means you're inventing.
- **Every JD-derived eval must cite a specific JD passage in the Source line.** No exceptions. If you cannot quote the JD section, the eval does not exist.
- **No invention.** Do not write evals based on what *should* be true of this role. Write evals based on what the JD actually says.
- **No company-profile drift.** Inherited evals must be copied verbatim. Do not "improve" them for this role.
- **JD-derived evals are binary.** No scales. No compound conditions.
- **No emojis. No markdown beyond what's in the schema.**

## When the JD is thin or generic

Some JDs are 1-paragraph stubs ("we're hiring engineers, apply here") with no responsibilities or requirements detail. In that case:

- Use all 4-6 inherited company evals
- Add only 1-2 JD-derived evals (whatever is extractable -- maybe just team or location)
- Append a `## Profile limitations` section noting the thin JD -- the recruiter subagent will treat this profile with lower confidence

## Output

Return the profile markdown body only. The parent skill will save it.
```

---

## How this fits into the secondary loop

After a resume is locked for a company:

1. Job-openings subagent discovers roles at that company.
2. For each role: this subagent builds a hiring-manager profile.
3. The recruiter subagent scores the locked resume against this hiring-manager profile.
4. If the score is below threshold, a sub-mutation loop runs against the hiring-manager profile until it locks or budget exhausts.
5. The result is a per-opening resume variant.

The hiring-manager profile is the bridge between "this resume meets the company's general hiring bar" and "this resume is tuned for THIS specific open role at the company."
