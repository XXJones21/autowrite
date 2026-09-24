# Fit judge subagent prompt

Spawn one fit-judge subagent per batch file listed in `search/<date>/batches/index.json`, in parallel, one message with several Agent calls.

- `subagent_type`: `general-purpose` (it writes one file)
- `model`: the `judge_model` value from `search/config.yaml`, the same for every batch in a run, so verdicts stay comparable across days
- `description`: `Judge job batch <batch name>`

`prompt`:

```
You are screening job postings for one candidate. For each posting in the batch, decide which role family it belongs to and check the posting's stated hard requirements against the candidate's factual library. You are not writing a resume or giving advice.

Batch file: [ABSOLUTE PATH TO batches/<name>.json]
Write your result to: [ABSOLUTE PATH TO batches/<name>.verdicts.json]

Candidate's role families (from search/config.yaml):
- core: [CORE LIST]
- adjacent: [ADJACENT LIST]
- downweight: [DOWNWEIGHT LIST]

Candidate's factual library (every file below is a fact the candidate has confirmed; nothing else is a fact):
<<<LIBRARY BEGIN>>>
[EVERY .md FILE FROM bullets/, interview-notes/, narratives/, context/, EACH PREFIXED WITH "--- <relative path> ---"]
<<<LIBRARY END>>>

For each posting:
1. role_family: core, adjacent, or downweight, by what the job does day to day, not by title words alone.
2. checks: 3 to 5 of the posting's stated hard requirements (skills, experience, domain), each with passed true or false and a quote copied verbatim from the library that supports a pass. A pass needs a quote. When no quote supports it, it fails.
3. gates: every stated knockout (degree, minimum years, clearance, work authorization, location or onsite days, certification). status is passed, failed, or unverified. Use unverified whenever the library does not settle it. When the library says the candidate has no degree and the posting requires one without an equivalent-experience clause, the degree gate is failed; with an equivalent-experience clause it is unverified and the note says no degree is on file.
4. candidate_questions: requirements that would pass only with a fact not in the library, phrased as a question to the candidate.

Never add a skill, number, or experience the library does not state. Do not soften a failed check.

Write this JSON to the output path and nothing else:
{"verdicts": [{"id": "<posting id>", "role_family": "core|adjacent|downweight", "checks": [{"requirement": "...", "passed": true, "quote": "..."}], "gates": [{"gate": "...", "status": "passed|failed|unverified", "note": "..."}], "candidate_questions": ["..."]}]}

Every posting in the batch gets exactly one verdict. Then reply with one line: the output path and the count of verdicts written.
```
