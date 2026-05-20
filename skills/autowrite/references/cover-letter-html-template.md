# Cover-letter HTML rendering template

Use this template when converting a saved `cover-letter.md` to print-ready `cover-letter.html`. The letter is structurally simpler than the resume -- date, salutation, body paragraphs, signature -- and the CSS reuses the same variables and font stack as `resume-html-template.md` so the two documents read as a matched pair when the candidate prints them.

## When this template is invoked

- After Step 6.5 saves `applications/<company>/<role>/cover-letter.md`, immediately render the HTML sibling at `applications/<company>/<role>/cover-letter.html`.
- The markdown source is never replaced or deleted by the render.
- One letter, one HTML file. No bundled "company-level letter" output exists.

## How to convert

The letter markdown is the source of truth. Mirror its content verbatim into the HTML.

| Markdown element | HTML element | Notes |
|------------------|--------------|-------|
| Top line containing a date (e.g., `May 20, 2026`) | `<p class="date">` | If the letter begins with a `## Manual review needed` heading, that block precedes the date paragraph (see "Manual review banner" below). |
| Salutation line (`Dear ...,`) | `<p class="salutation">` | One paragraph. |
| Body paragraph(s) | `<p>` each | Preserve every paragraph break. Body paragraphs are the bulk of the letter. |
| Closing line (`Sincerely,`) | `<p class="closing">` | |
| Signature line (the candidate's name) | `<p class="signature">` | |
| `## Manual review needed` heading + its paragraph | banner block (see below) | Only present when the role was flagged. |
| `## Candidate questions flagged` heading + bullets | drop from HTML | These are operational notes for the parent skill; they belong in the markdown source and `sub-changelog.md` but not in the print-ready letter. Log them, do not render them. |
| Inline `**bold**` / `*italic*` / `[text](url)` | `<strong>` / `<em>` / `<a>` | Preserve inline formatting. |

**Preserve every word from the letter body.** This is rendering, not editing. No truncation, no smoothing, no "polishing." The markdown is locked at Step 6.5; the HTML mirrors it.

### Manual review banner

When the markdown starts with a `## Manual review needed` heading (set by the subagent when the role was budget-exhausted), render it as a small banner above the date:

```html
<div class="review-banner">
  <strong>Manual review needed.</strong> [verbatim paragraph from the markdown]
</div>
```

The banner is amber-tinted and intentionally visible so the candidate notices before submitting. When the letter is not flagged, the banner is omitted entirely (no empty container).

### Candidate questions flagged

If the markdown contains a `## Candidate questions flagged` section at the bottom, strip it from the HTML render. These are notes the subagent emitted about facts it considered but skipped due to no source. The markdown keeps them as a checkbox list for the user to resolve; the parent skill should also surface them in `sub-changelog.md`. They do not belong in the print-ready letter.

## HTML skeleton

Save this exact skeleton, substituting `[CANDIDATE NAME]` for the signature line at the bottom of the letter (used only in the `<title>` tag; the body content of `<p class="signature">` is the literal markdown signature line).

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>[CANDIDATE NAME] -- Cover Letter</title>
<style>
  :root {
    --ink: #1a1a1a;
    --muted: #5a5a5a;
    --rule: #cccccc;
    --review: #b07a1f;
    --review-bg: #fdf6e3;
    --page-max: 8.0in;
  }

  * { box-sizing: border-box; }

  html, body {
    margin: 0;
    padding: 0;
    background: #ffffff;
    color: var(--ink);
    font-family: "Source Serif Pro", "Georgia", "Times New Roman", serif;
    font-size: 11pt;
    line-height: 1.5;
  }

  main {
    max-width: var(--page-max);
    margin: 0 auto;
    padding: 0.75in 0.75in;
  }

  .review-banner {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-size: 9.5pt;
    color: var(--review);
    background: var(--review-bg);
    border-left: 3px solid var(--review);
    padding: 8px 12px;
    margin: 0 0 18px 0;
    line-height: 1.4;
  }
  .review-banner strong { color: var(--review); font-weight: 700; }

  p.date {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-size: 10pt;
    color: var(--muted);
    margin: 0 0 22px 0;
  }

  p.salutation {
    margin: 0 0 14px 0;
  }

  p {
    margin: 0 0 12px 0;
    text-align: left;
  }

  p.closing {
    margin: 18px 0 4px 0;
  }

  p.signature {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-weight: 600;
    margin: 0;
  }

  strong { font-weight: 700; }
  em { font-style: italic; }

  a { color: var(--ink); text-decoration: underline; }
  a:hover { text-decoration: none; }

  /* Print rules: trim browser chrome, set page margins, keep paragraphs intact */
  @page {
    size: letter;
    margin: 0.75in 0.75in;
  }
  @media print {
    main { padding: 0; max-width: none; }
    p { page-break-inside: avoid; }
    .review-banner { page-break-inside: avoid; }
    a { color: var(--ink); text-decoration: none; }
  }
</style>
</head>
<body>
<main>
[INLINE CONVERTED BODY]
</main>
</body>
</html>
```

## After writing the HTML file

Announce in chat with:

1. The HTML path.
2. One-line print instructions: "Open in browser -> Ctrl+P (Cmd+P on macOS) -> Destination: Save as PDF -> Layout: Portrait -> Margins: Default -> Save."
3. On Windows, optionally attempt `Start-Process <path>` to open the file in the default browser. Treat failure as non-fatal.

Do not attempt headless PDF conversion. The same manual print-to-PDF pattern as the resume applies.

## Constraints

- **One file, no external dependencies.** All CSS inline. No CDN fonts, no scripts, no images. The HTML must render identically offline.
- **Letter size, three-quarter-inch margins.** The wider margin (vs. the resume's half-inch) gives the letter the white space the genre expects. Adjust to A4 only if the candidate's contact info indicates a non-U.S. location AND the resume's existing styling implies A4 expectations.
- **Serif body, sans-serif date + signature.** Source Serif Pro for the body (the letter genre is serif by convention). Source Sans Pro for date metadata and signature for visual contrast with the body. Same fallback cascade as the resume template.
- **Monochrome with a single amber accent.** The amber is reserved for the manual-review banner and appears nowhere else. The rest of the document is ink + muted gray + thin rule (which the letter template doesn't actually use, but the variable is kept for consistency with the resume).
- **No icons. No emojis.** Even if a candidate question accidentally rendered with an emoji upstream, strip it from the HTML.
- **No content invention.** If the markdown letter has only two body paragraphs, the HTML has two body paragraphs. Do not pad. Do not insert a "looking forward to hearing from you" sentence that isn't in the source.
- **Preserve every word.** This is rendering, not editing. Quote markdown content into HTML elements verbatim.

## Edge cases worth handling

- **Letter without an explicit date line.** Insert today's date (the date the parent skill saved the markdown) as the first `<p class="date">`. The subagent prompt requires the date, so this should be rare -- but if it's missing, the render does not silently drop it.
- **Markdown with hard line breaks inside a paragraph.** Preserve as `<br>` only when the line break is clearly intentional (e.g., a multi-line address block). For body paragraph wrapping, drop hard line breaks -- the HTML re-wraps naturally.
- **Salutation with a long team name.** `Dear Applied AI Engineering team,` should still fit on one line at the chosen font size; if the candidate-name signature is unusually long, that is also fine -- no special handling needed.
- **Signature line missing.** If the markdown ends with `Sincerely,` but no signature line follows, render only the closing paragraph and add a `<p class="signature">[Your Name]</p>` placeholder. Announce in chat that the signature was missing from the markdown source so the user can decide whether to amend the markdown or the rendered HTML.
- **A second `## Manual review needed` heading later in the letter.** Only the first one renders as a banner; any subsequent occurrences are dropped (they would only appear if the subagent malformed its output, and a single banner is sufficient).
