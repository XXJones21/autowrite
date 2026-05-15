# Resume HTML rendering template

Use this template when converting a locked markdown resume to print-ready HTML. The goal is **structural faithfulness**: produce HTML that mirrors whatever shape the input markdown actually has, rather than forcing every resume into a fixed schema.

The CSS skeleton at the bottom is intentionally general-purpose -- it styles whatever HTML elements appear, in a clean single-column print-ready layout, without assuming any specific section order or naming convention.

## When this template is invoked

- After a company profile LOCKS in the primary loop: render `applications/<company>/_company-locked.md` -> `_company-locked.html`
- After a per-role sub-loop completes (or baselines above threshold) in the secondary loop: render `applications/<company>/<role>/resume.md` -> `resume.html`

Both produce a sibling HTML file alongside the markdown source. Do NOT replace or delete the markdown.

## How to convert -- structure-discovery approach

The input markdown is the source of truth for both content AND structure. Do not impose a section order, do not rename sections, do not insert sections that aren't there, do not skip sections that are there (with one optional exception noted below). The HTML mirrors whatever the markdown contains.

The process is two passes:

### Pass 1 -- Inspect the resume's actual structure

Read the entire markdown file before writing any HTML. As you read, note:

- **Heading depth distribution.** Which heading levels does this resume use? Some resumes use only `#` and `##`. Some use `#` / `##` / `###`. Some use a flat list of `##` sections with no nesting. Whatever you find is correct -- treat it as the candidate's chosen hierarchy.
- **The first block.** The opening block is almost always identity + contact info. It might be: an `# H1` with the name and a paragraph underneath, or a name line followed by separator-delimited contact info, or a name with multiple paragraph lines. Capture what's actually there without assuming a specific shape.
- **Section labels.** Read the actual section names. "Experience" / "Work Experience" / "Professional Experience" / "Career History" are all valid. Same for "Skills" / "Technical Skills" / "Tools & Stack" / "Competencies", and "Projects" / "Personal Projects" / "Selected Work" / "Portfolio". Use the candidate's words verbatim.
- **Per-role / per-item shape.** Inside an Experience section, what does each role look like? Is the role title a sub-heading? Is it bold inline text? Are dates italicized? On the same line as the title? Below it? Capture the pattern and apply it consistently to all entries in that section.
- **Bullet vs. paragraph density.** Some sections are bulleted; some are paragraphs; some are a mix. Preserve whichever the candidate used.
- **Inline formatting.** Bold spans, italic spans, inline code, links -- preserve them.
- **Working-draft scaffolding.** Look for a section named "Open TODOs", "Notes", "Scratch", "TODO", or similar at the end of the file. This is sometimes used as a working-draft surface and is the only block you may skip from the rendered HTML -- if you skip it, announce the skip in chat ("Working-draft section '<name>' omitted from HTML render -- resolve before publishing"). When in doubt, include the section.

If the resume uses an unusual structure -- a sidebar-style layout encoded with two-column markdown tables, ASCII separators, callout blocks, or anything else not on the standard heading/list/paragraph palette -- preserve it. Use HTML tables for markdown tables. Use `<blockquote>` for blockquotes. Use `<hr>` for horizontal rules when they carry visual meaning beyond section separation. The CSS handles styling.

### Pass 2 -- Map markdown to HTML one element at a time

These are the safe defaults. Adjust if the candidate's resume uses something the table doesn't cover.

| Markdown element | HTML element | Notes |
|------------------|--------------|-------|
| Top-level `# Heading` | `<h1>` | Usually the candidate's name. Always emitted, never demoted. |
| Paragraph(s) immediately under `# Heading` before the first `##` | `<p class="contact">` (one or more) | This is the contact/identity block. If there are multiple lines, emit each as its own `<p class="contact">`. Pipe / bullet / middot separators between fields stay inline. |
| `## Heading` | `<h2>` | Section header (whatever the candidate named it). |
| `### Heading` | `<h3>` | Role / item / sub-section header. |
| `#### Heading` | `<h4>` | Sub-item. Rare but supported. |
| Italic-only line immediately under a `###` (typically a date range or location) | `<p class="dates">` | Common pattern; treat as metadata for the heading above. |
| Bullet list `- item` | `<ul><li>` | |
| Numbered list `1. item` | `<ol><li>` | |
| `**bold**` | `<strong>` | |
| `*italic*` or `_italic_` | `<em>` | |
| `` `inline code` `` | `<code>` | |
| `[text](url)` | `<a href="url">text</a>` | |
| `> blockquote` | `<blockquote>` | |
| Horizontal rule `---` between sections | drop | CSS handles section spacing. |
| Horizontal rule `---` within a section (deliberate visual break) | `<hr>` | Keep when the rule isn't just acting as a section separator. |
| Markdown table | `<table>` | Preserve verbatim. |
| Code fence (triple backtick) | `<pre><code>` | Rare in resumes but if present, preserve. |

**Preserve every word.** This is rendering, not editing. No truncation, no rewriting, no "polishing." The markdown is locked; the HTML mirrors it.

If you encounter a structural element you're unsure how to map, the safe default is: emit it as the closest semantic HTML element, and the CSS skeleton will give it sensible defaults.

## HTML skeleton

Save this exact skeleton, substituting `[CANDIDATE NAME]` for whatever the resume's top-level heading says (the title-tag value is the only place where the candidate's name is templated -- everywhere else, the name is just the body content of the first `<h1>`). The body is wrapped in `<main>` and styled by the inline CSS block below.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>[CANDIDATE NAME] -- Resume</title>
<style>
  :root {
    --ink: #1a1a1a;
    --muted: #5a5a5a;
    --rule: #cccccc;
    --page-max: 8.0in;
  }

  * { box-sizing: border-box; }

  html, body {
    margin: 0;
    padding: 0;
    background: #ffffff;
    color: var(--ink);
    font-family: "Source Serif Pro", "Georgia", "Times New Roman", serif;
    font-size: 10.5pt;
    line-height: 1.35;
  }

  main {
    max-width: var(--page-max);
    margin: 0 auto;
    padding: 0.5in 0.6in;
  }

  h1 {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-size: 22pt;
    font-weight: 700;
    margin: 0 0 4px 0;
    letter-spacing: 0.01em;
  }

  p.contact {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-size: 10pt;
    color: var(--muted);
    margin: 0 0 4px 0;
    line-height: 1.4;
  }
  p.contact:last-of-type { margin-bottom: 14px; }

  p.contact a { color: var(--muted); text-decoration: none; }
  p.contact a:hover { text-decoration: underline; }

  h2 {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-size: 12pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 16px 0 6px 0;
    padding-bottom: 3px;
    border-bottom: 1px solid var(--rule);
  }

  h3 {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-size: 11pt;
    font-weight: 600;
    margin: 10px 0 1px 0;
  }

  h4 {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-size: 10.5pt;
    font-weight: 600;
    font-style: italic;
    margin: 6px 0 1px 0;
  }

  p.dates {
    font-family: "Source Sans Pro", "Helvetica Neue", "Arial", sans-serif;
    font-size: 9.5pt;
    font-style: italic;
    color: var(--muted);
    margin: 0 0 4px 0;
  }

  p { margin: 6px 0; }

  ul, ol {
    margin: 4px 0 8px 0;
    padding-left: 1.1em;
  }

  li {
    margin-bottom: 3px;
  }

  strong { font-weight: 700; }
  em { font-style: italic; }
  code {
    font-family: "Source Code Pro", "Menlo", "Consolas", monospace;
    font-size: 9.5pt;
    background: #f4f4f4;
    padding: 0 3px;
    border-radius: 2px;
  }

  blockquote {
    border-left: 2px solid var(--rule);
    margin: 6px 0;
    padding: 2px 0 2px 10px;
    color: var(--muted);
  }

  hr {
    border: none;
    border-top: 1px solid var(--rule);
    margin: 10px 0;
  }

  table {
    border-collapse: collapse;
    margin: 6px 0;
    font-size: 10pt;
  }
  th, td {
    text-align: left;
    padding: 3px 8px 3px 0;
    vertical-align: top;
  }
  th { font-weight: 600; }

  /* Print rules: trim browser chrome, set page margins, prevent awkward role splits */
  @page {
    size: letter;
    margin: 0.5in 0.6in;
  }
  @media print {
    main { padding: 0; max-width: none; }
    h2, h3, h4 { page-break-after: avoid; }
    ul, ol, p, blockquote, table { page-break-inside: avoid; }
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

Do not attempt headless PDF conversion. The user explicitly opted for manual print-to-PDF so they can preview before saving.

## Constraints

- **One file, no external dependencies.** All CSS inline. No CDN fonts, no scripts, no images. The HTML must render identically offline.
- **Letter size, half-inch margins.** Matches U.S. resume conventions and ATS expectations. Adjust to A4 only if the candidate's contact info indicates a non-U.S. location AND the resume's existing styling implies A4 expectations.
- **Serif body, sans-serif headers.** Source Serif Pro + Source Sans Pro are the design intent; the cascade falls back to Georgia / Helvetica / Arial if those aren't installed locally. All of those are ubiquitous and safe.
- **Monochrome.** No color beyond ink, muted gray, and the thin section rule. Recruiters and ATS parsers both prefer monochrome.
- **No icons. No emojis.** Even if the markdown contains an emoji, strip it from the rendered HTML.
- **No content invention.** If a section is missing from the markdown, it is missing from the HTML. Do not add a Summary if there isn't one. Do not add a Skills section if there isn't one. Mirror the source.
- **Preserve every word.** This is rendering, not editing. Quote markdown content into HTML elements verbatim.

## Edge cases worth handling

- **No `# H1` at the top.** Some resumes lead with a `## Name` or a paragraph-bold name instead of a top-level heading. Emit it as `<h1>` regardless -- the visual hierarchy expects an H1 even when the source markdown happens to use a different level.
- **Multiple `# H1`s.** Treat only the first as the candidate's identity. Subsequent `#` headings get demoted to `<h2>` so the section hierarchy remains coherent.
- **Custom section names in unfamiliar industries.** "Crew Experience" / "Field Operations" / "Studio Credits" / "Endorsements" / "Patents" / "Press" -- all are valid section names. Render them as-is.
- **Inline contact icons or unicode separators (-, |, /, .).** Keep them as text characters; the contact CSS handles spacing.
- **Skills section with grouped bullets like `**Languages:** Python, Rust, ...`**: the bold-prefixed-paragraph pattern is common. Render each as `<p><strong>Languages:</strong> Python, Rust, ...</p>`. The default `p` styling handles it cleanly.
- **Date-only italic lines under role headings**: emit `<p class="dates">`. If a candidate uses a different metadata convention (e.g., dates parenthesized in the heading itself), leave them in the heading -- don't try to extract.
