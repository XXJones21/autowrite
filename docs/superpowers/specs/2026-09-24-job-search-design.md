# Job search skill: design

Date: 2026-09-24. Status: approved in conversation, pending implementation plan.

## Purpose

Referrals and recommendations stopped producing interviews, and cold applications to hand-picked postings rarely get a reply. The job-search skill widens where the candidate looks and ranks what it finds against the candidate's own factual library, so the packet builder (autowrite) and the outreach flow get pointed at the best targets instead of whatever surfaced that week.

It covers three kinds of targets:

1. **Wide net:** every open posting on the public job boards of a maintained company list.
2. **Adjacent roles:** role families the candidate's record supports but has not been applying to (solutions, partner, and forward-deployed engineering, AI enablement, developer relations), tagged and ranked alongside core roles.
3. **Hidden market:** companies with recent funding, launches, or hiring signals that match the candidate's edge, with or without a posting, each with a sourced one-paragraph case for founder outreach.

Out of scope for v1: warm-path matching from a connections export, contract roles, and anything that sends a message or submits an application.

## Placement

A new generic skill in the autowrite plugin: `skills/job-search/`, beside `autowrite` and `career-intake`. The plugin holds only the method. All candidate data, configuration, and outputs live next to the candidate's resume, following autowrite's co-location rule:

```
<resume-parent-dir>/
  bullets/                 # factual library (read)
  profiles/                # cached company profiles (read, for seeding)
  applications/            # packets and trackers (read, for seeding and de-duplication)
  search/
    config.yaml            # filters and weights (candidate-editable)
    companies.yaml         # company list with board type and ID
    seen.json              # every posting ever judged, with verdict and dates
    <YYYY-MM-DD>/
      postings.json        # normalized, filtered postings from this run
      verdicts.json        # fit-judge output for this run
      ranked.md            # human report
      ranked.json          # machine report for hand-off
```

## Configuration

`search/config.yaml`, written on first run from the answers below and editable afterward:

```yaml
locations:
  keep: ["bay-area", "us-remote"]   # Bay Area onsite or hybrid (Santa Clara, San Jose, Peninsula, San Francisco), fully remote open to US residents
pay:
  base_floor_usd: 180000            # drop when the posted maximum base is below this; postings with no pay are kept and flagged
role_families:
  core: []                          # filled from the candidate's history on first run, confirmed by the candidate
  adjacent: []
  downweight: ["technical writing"] # ranked below adjacent; shown only in their own section unless the candidate asks
contract_roles: false
daily:
  max_judge_batches: 5              # about 50 postings
judge_model: opus                   # fixed for every judge call so scores compare across days
```

## Components

### 1. Board fetcher: `scripts/fetch_boards.py` (code)

- Reads `companies.yaml`: one entry per company with `name`, `board` (`ashby`, `greenhouse`, `lever`, `workday`), board identifiers, and optional `hidden: true` and `failures: N`.
- Pulls postings through public endpoints, no credentials:
  - Ashby: `GET https://api.ashbyhq.com/posting-api/job-board/<org>?includeCompensation=true`
  - Greenhouse: `GET https://boards-api.greenhouse.io/v1/boards/<token>/jobs?content=true`
  - Lever: `GET https://api.lever.co/v0/postings/<company>?mode=json`
  - Workday: `POST https://<tenant>.<wdN>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs` (paged list), then `GET .../job/<externalPath>` for the description and pay text.
  - Apple is not in v1: its search endpoint is unverified. Individual Apple postings can still be fetched by ID through `jobs.apple.com/api/v1/jobDetails/PIPE-<id>` at hand-off.
- Normalizes each posting to: `id` (board + native ID), `company`, `title`, `team`, `locations[]`, `remote` flag, `pay_min`, `pay_max`, `pay_text`, `posted_date`, `url`, `description_text`.
- Applies hard filters from `config.yaml`. Location matching is by a fixed table of Bay Area cities plus explicit US-remote markers. Pay is parsed only from posted text; the maximum base is compared to the floor, and a posting with no parseable pay is kept with `pay_listed: false`.
- Writes `search/<date>/postings.json`. With `--daily`, passes forward only IDs not in `seen.json` and marks IDs missing from their board as `closed` with the date.
- A board that errors or times out is recorded under `boards_not_checked` with the error and the run continues. Its `failures` count increments; at 3 it is flagged for the candidate.
- Python standard library only (`urllib`, `json`, `re`, `datetime`), plus a minimal YAML reader limited to the flat structures above, so the script has no dependencies.

### 2. Fit judge (subagent prompt: `references/fit-judge-prompt.md`)

- Input: a batch of about 10 filtered postings and the candidate's full factual library (`bullets/*.md`, `interview-notes/`, `narratives/`, `context/`, as autowrite loads it).
- Output per posting (JSON): `role_family` (`core` / `adjacent` / `downweight`), 3 to 5 `checks` drawn from the posting's stated hard requirements, each with `passed` and a verbatim `quote` from the library, `gates` (degree, years, clearance, location, or other stated knockout) each `passed` / `failed` / `unverified`, and `candidate_questions` for requirements that would pass only with a fact not in the library.
- Rules: a pass without a quote is a fail; a gate the library cannot confirm is `unverified`, never passed; a degree requirement reports that no degree is on file when the library says so; the judge never adds skills or facts.
- Runs on the fixed `judge_model` from config.

### 3. Hidden-market scout (subagent prompt: `references/scout-prompt.md`)

- Searches recent funding rounds, product launches, and hiring signals matching the candidate's edge (the edge statement comes from `outreach/positioning-brief.md` when present, otherwise from the resume summary).
- Adds new companies to `companies.yaml` with `hidden: true` and the board identifiers when a board exists.
- For the top 5, drafts the one-paragraph case (building X, missing Y, working for A/B/C, what it does to revenue, the candidate's Z with results). Every case cites a source URL for the funding or launch it rests on; an unsourced case is dropped. Drafts are for the candidate only.
- Runs in full runs only.

### 4. Ranker and report: `scripts/rank.py` (code)

- Merges `postings.json` and `verdicts.json`, updates `seen.json`.
- Sort order: no failed gates first, then checks passed (count, then ratio), then role family (core, adjacent, downweight), then posting freshness.
- Writes `ranked.md`: a numbered table (rank, company, title, location, pay or "not listed", family, checks passed, gates, posted date, URL), then "New since yesterday" on daily runs, then the hidden-market cases, then "Boards not checked" and candidate questions. `ranked.json` carries the same rows with full verdicts.

## Run modes

**Full run** (`/job-search`): scout, fetch, judge all unjudged postings, rank, then a short chat summary with counts, the top 10, and the report path.

**Daily delta** (`/job-search daily`): fetch with `--daily`, judge only new postings up to `max_judge_batches`, rank, append under "New since yesterday." No scout. Postings over the cap are listed as deferred and judged the next day. Scheduled by the operating system, for example Windows Task Scheduler running `claude -p "/job-search daily"` in the candidate's folder each morning, using the candidate's existing Claude Code login.

**First run** (no `search/` yet): write `config.yaml` from the filters above and a proposed `role_families` list for the candidate to confirm, and seed `companies.yaml` from `profiles/`, the companies in `applications/` and its trackers, and any board identifiers found in saved postings.

## Hand-off

The candidate picks rows by number ("build 2, 5, 9"). For each pick the skill re-fetches the posting; if it is gone the candidate is told and nothing is built. Live picks go to autowrite's secondary loop with the posting URL and the fetched description, so autowrite skips discovery. A hidden-market pick goes to the outreach flow (high-leverage-job-hunt's Move 3 kit) with its case paragraph. Nothing is built without a pick.

## Honesty rules

- Every ranked row has a live URL and fetch date.
- Pay is only what the posting states.
- Every judge pass quotes the library; unconfirmable gates are `unverified`.
- Hidden-market cases cite sources.
- Nothing is sent, submitted, or posted.

## Testing

- `scripts/test_fetch_boards.py` (`unittest`): parsing fixtures for each board type (saved real responses, starting with this week's Ashby and Workday fetches), location and pay filters (Bay Area kept, Tel Aviv-only dropped, US remote kept, $170K cap dropped, no-pay kept and flagged), daily diff (new IDs pass, vanished IDs close), and a failing board recorded without stopping the run.
- `scripts/test_rank.py`: fixed verdicts produce the specified sort order.
- Prompt checks by hand before shipping: the judge on two known postings (NVIDIA JR2021035, Salesforce JR360438) quotes real bullets, tags Salesforce as downweighted, and reports the degree gate as unverified with no degree on file; the scout's cases each cite a URL that loads.
- Acceptance: one real full run over the seeded company list produces a `ranked.md` the candidate judges useful.
