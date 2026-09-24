# Hidden-market scout subagent prompt

Spawn one scout subagent per full run.

- `subagent_type`: `general-purpose` (it needs WebSearch and WebFetch, and writes one file)
- `model`: the `judge_model` value from `search/config.yaml`
- `description`: `Scout hidden-market companies`

`prompt`:

```
You are finding companies where this candidate could create value, whether or not they have posted a matching job. Output feeds a founder-outreach flow the candidate reviews; nothing you write is sent.

Candidate edge (their words):
[EDGE STATEMENT FROM outreach/positioning-brief.md, OR THE RESUME SUMMARY IF THAT FILE IS ABSENT]

Candidate evidence (factual library excerpts):
[THE LIBRARY FILES MOST RELEVANT TO THE EDGE, EACH PREFIXED WITH "--- <relative path> ---"]

Already on the company list (skip these): [COMMA-SEPARATED NAMES FROM search/companies.yaml]
Location constraint: [LOCATIONS FROM config.yaml]

Search recent funding announcements, product launches, open-source releases, and hiring posts from the last 6 months for companies whose product sits where the candidate's edge applies. Prefer companies of 10 to 500 people, where a founder or team lead is reachable. Verify each company with at least one source you fetched.

Write JSON to [ABSOLUTE PATH TO search/<date>/scout.json]:
{"companies": [{"name": "...", "board_url": "<careers or job-board URL, or empty>", "signal": "<one line: the funding, launch, or hiring signal>", "source_url": "<URL you fetched that shows the signal>"}],
 "cases": [{"company": "...", "paragraph": "<one paragraph: what they are building, the specific thing they appear to be missing, where that has worked elsewhere, roughly what it would change for them, and the candidate's matching evidence with its result, quoted from the library>", "sources": ["<URL>", "..."]}]}

List 10 to 20 companies. Write cases for the 5 strongest only. Every case cites at least one source you fetched. Drop any case you cannot source, and drop any claim about the candidate that is not in the library. Then reply with one line: the path and the counts.
```
