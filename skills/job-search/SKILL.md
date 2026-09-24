---
name: job-search
description: "Find and rank job openings and unposted targets for a candidate. Fetches postings from public job boards (Ashby, Greenhouse, Lever, Workday) for a maintained company list, filters by location and pay, judges fit against the candidate's factual library with quoted evidence, scouts hidden-market companies with sourced outreach cases, and writes a ranked list the candidate picks from. Use when: job search, find jobs, find me roles, what should I apply to, daily job check, search openings, hidden market. Hands picks to autowrite for packets."
---

# Job search

Finds openings the candidate has not seen, ranks them against what the candidate has actually done, and stops at a ranked list. The candidate picks; only picks get packets.

Scripts live in this skill's `scripts/` directory. Run them with `python <skill-dir>/scripts/<name>.py --root <resume-parent-dir>`, where `<resume-parent-dir>` is the directory holding the candidate's resume, `bullets/`, and `profiles/`. Every output lands in `<resume-parent-dir>/search/`.

## Modes

Read the invocation: `daily` means the daily run, a list of row numbers ("build 2, 5, 9") means hand-off, anything else is a full run. If `search/config.yaml` is missing, do the first run before anything else.

## First run

1. Ask the candidate, in one `AskUserQuestion` call: which locations to keep (`bay-area`, `us-remote`, or both), and the base-pay floor in USD. Postings with no listed pay are always kept and flagged.
2. Run `init_search.py --root <dir> --locations <...> --pay-floor <n>`. It writes `search/config.yaml` and seeds `search/companies.yaml` from job-board URLs in `applications/` and company names in `profiles/`.
3. Read the resume and library, then propose `role_families` (core, adjacent, downweight) and `titles.include` / `titles.exclude` keyword lists for `config.yaml`. Title keywords are lowercase substrings; include should cover every core and adjacent family, and exclude should drop obvious misses (intern, sales, recruiter, and similar). For broad titles such as product manager, add them to `titles.qualify.terms` with `titles.qualify.with` words (for example developer, platform, api, ai, agent, tools) so only the relevant ones pass. Show the proposal and the seeded company list, and apply the candidate's corrections. Set `disabled: true` on any company the candidate rules out.
4. Run `discover_boards.py --root <dir> --from-list`, which tries slug variants of each board-less company on Ashby, Greenhouse, and Lever. For companies it cannot find, look up their careers page. When it is on Ashby, Greenhouse, Lever, or Workday, fill in the board fields (Workday needs `host`, `tenant`, `site`, and `search_terms`). Otherwise leave `board: none`.
5. Continue with a full run.

## Full run

1. **Scout.** Spawn the scout per `references/scout-prompt.md`. Then run `merge_scout.py --root <dir>`, then `discover_boards.py --root <dir> --from-list` to find public boards for any new board-less companies. To widen the list on request, pass company names with `discover_boards.py --root <dir> --names "Name One" "Name Two"`.
2. **Fetch.** Run `fetch_boards.py --root <dir>`. Relay any boards not checked.
3. **Batch.** Run `make_batches.py --root <dir>`. Postings are ordered by the candidate's `titles.include` order, then newest first. When more than about 10 batches would result, pass `--max-batches 10` and tell the candidate how many postings wait for the daily runs; `daily.batch_size` sets postings per batch.
4. **Judge.** For every batch listed in `search/<date>/batches/index.json`, spawn a fit judge per `references/fit-judge-prompt.md`, all in one message. Pass each judge the list of library file paths (every `.md` in `bullets/`, `interview-notes/`, `narratives/`, `context/`); the judge reads them itself, which keeps the parent's context small. When a judge fails or its verdicts file is missing, re-spawn it once; if it fails again, leave that batch unjudged (its postings stay pending for the next run) and say so.
5. **Rank.** Run `rank.py --root <dir>`.
6. **Report.** In chat: counts (ranked, filtered out, boards not checked, closed), the top 10 rows (rank, company, role, pay, checks, gates), the hidden-market company names, and the path to `ranked.md`. Then stop and let the candidate pick.

## Daily run

Run `fetch_boards.py --root <dir> --daily`, then `make_batches.py --root <dir> --daily`, judge the listed batches as in the full run, then `rank.py --root <dir>`. No scout. The report's "New since yesterday" section lists the new rows. Keep the chat summary to counts and the new rows.

## Hand-off

1. Run `recheck.py --root <dir> --rows <n ...>` with the candidate's picks. It re-fetches each posting, writes `applications/<company>/<role>/job-posting.md` for live ones, and closes the rest. Tell the candidate which picks closed.
2. For each live pick, hand the posting to autowrite's secondary loop (Step 6b onward) with the saved `job-posting.md` as the JD source, so autowrite skips discovery.
3. For a hidden-market pick, hand its case paragraph and sources to the outreach flow (the high-leverage-job-hunt skill's Move 3 when installed). Draft only; nothing is sent.

## Scheduling the daily run

Offer this once, after the first successful full run, and let the candidate create it themselves; creating a scheduled task is a system change the candidate makes. On Windows:

```
schtasks /Create /SC DAILY /ST 07:30 /TN "job-search daily" /TR "cmd /c cd /d <resume-parent-dir> && claude -p \"/job-search daily\""
```

On macOS or Linux, a crontab line: `30 7 * * * cd <resume-parent-dir> && claude -p "/job-search daily"`.

## Rules

- Every ranked row came from a board fetch; never add a posting by hand or from memory.
- Pay is what the posting states. A row without pay says "not listed".
- The fit judge's passes quote the library. Unconfirmed gates stay unverified.
- Hidden-market cases cite sources; nothing is sent to anyone.
- Nothing is built until the candidate picks rows.
