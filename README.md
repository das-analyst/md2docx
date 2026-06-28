# md2docx (OpenRouter build)

Generate styled **Word documents (`.docx`) from Markdown spec files** — with optional AI
enrichment powered by **OpenRouter** instead of Azure AI.

> **Works as a Claude Code tool (or any LLM agent):** the sibling
> [`mba_ai`](https://github.com/das-analyst/mba_ai) project registers this as an MCP server
> via its `.mcp.json`. Because the interface is "write a `.spec.md`, run one command, get a
> `.docx`", Claude can author the spec in conversation, invoke the tool, and return the
> resulting Word file. No Azure infra to provision, one API key.

**What this doesn't do yet:** image generation is **disabled** — OpenRouter has no stable
`/images/generations` endpoint, so `image_prompt` directives are skipped (with a warning);
the docx still builds cleanly. Enrichment itself is **optional** — with no `**ContentUrls**`
block, the docs build fully offline. To re-enable images, point `src/images.py` at a provider
with an OpenAI-compatible images endpoint (e.g. OpenAI directly).

## Quick start in 3 steps

1. **Install deps**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate.bat      # Windows
   # source .venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   ```
2. **Set your key** — get one at https://openrouter.ai/keys. Copy `.env.example` → `.env` and
   set `OPENROUTER_API_KEY`, or export it (`export OPENROUTER_API_KEY=...`). The tool loads
   `<cwd>/.env` with `override=False`, so existing env vars win.
3. **Run the bundled example**
   ```bash
   python documents.py .speckit/specifications/example.spec.md -o output
   ```
   Or on Windows, the wrapper auto-creates the venv and installs deps:
   ```bat
   make_docx.bat .speckit/specifications/example.spec.md -o output
   ```

Open `output/example.docx` — done.

## How it works

```
your.spec.md  ──▶  documents.py  ──▶  your.docx
   (front-matter         (parse → enrich? → render)      (styled Word file)
    + sections)
```

- **Your spec is the source of truth.** Sections, bullets, and layout come from markdown.
- **Enrichment is additive and optional.** Add a `**ContentUrls**` block to a section and the
  tool fetches each URL, then asks the configured model to synthesize supplemental bullets or
  notes. No `content_urls` → no model call → fully offline.
- **Output is versioned** (`doc.docx`, `doc_1.docx`, ...) so existing files are never overwritten.

## Why this exists

Adapted from [microsoft/documents](https://github.com/microsoft/documents/tree/d878ed7) (MIT),
which generates `.docx` from `.spec.md` files but is coupled to Azure AI Foundry
(`AzureOpenAI` + `DefaultAzureCredential`). This fork keeps the renderer and swaps the LLM
layer to any **OpenAI-compatible endpoint** — tested against OpenRouter — so you can run it with
a single API key and no Azure subscription.

The upstream `microsoft/documents` (and its sibling `microsoft/presentations`) are great
spec-driven generators, but they assume an Azure AI Foundry project: subscription, Foundry
workspace, model deployments, `az login`. That's a real setup wall. This fork drops that to
**30 seconds**:

| | upstream | md2docx |
|---|---|---|
| LLM provider | Azure AI Foundry only | any OpenAI-compatible endpoint (OpenRouter, OpenAI, local) |
| Auth | `DefaultAzureCredential` + `az login` | one API key |
| Azure subscription | required | **not required** |
| Core docx rendering | offline | offline (unchanged) |
| AI enrichment | Azure OpenAI | OpenRouter / any `openai` SDK target |
| Image generation | Azure OpenAI DALL-E | **disabled** (see note above) |

## Writing a spec

A `.spec.md` has **YAML front-matter** + a **markdown body**. Sections are separated by `---`
horizontal rules and opened with a typed header.

**Save the block below as `my.spec.md`, edit the content, then run
`python documents.py my.spec.md`:**

```markdown
---
title: My Document
subtitle: Optional subtitle
output: My_Document.docx
author: Optional author
text_model: openai/gpt-4o-mini
style:
  title_font_size: 28
  subtitle_font_size: 14
  body_font_size: 11
  heading_font_size: 16
  heading_color: "1F3864"
  accent_color: "2E75B6"
---

## [title] Document Title

**Subtitle:** Optional subtitle text

---

## [content] Section With Bullets

- First bullet
- Second bullet
- First bullet

**ContentUrls**:                              # optional — triggers AI enrichment
- https://example.com

---

## [two-column] Split Section

**Left**:
- Left bullet

**Right**:
- Right bullet

---

## [section-header] Section Break

---

## [resource-box] Resources

**Box**: Links
- Example | https://example.com
```

### Section types (exactly these five)

- `title` — cover page; directives `**Subtitle**:`, `**Notes**:`
- `content` — heading + bullets; directives `**Notes**:`, `**ContentUrls**:`,
  `**Enriched**: true`, `**Image**:`, `**ImagePrompt**:`
- `section-header` — section break (auto page-breaks)
- `two-column` — two bullet columns; directives `**Left**:` / `**Right**:`
- `resource-box` — labelled link tables; directives `**Box**: Label` then rows
  `- Name | https://url`

### Front-matter keys

- `text_model` — OpenRouter model ID for enrichment (e.g. `openai/gpt-4o-mini`,
  `anthropic/claude-3.5-sonnet`, `google/gemini-2.0-flash-001`). Optional; enrichment is skipped
  if unset.
- `image_model` — accepted but **ignored** (images disabled in this build; see note above).
- `style.*` — fonts and colors for the document theme.

### CLI flags

```
python documents.py <spec> [-o output_dir] [--image-model MODEL] [--refetch] [--sections SELECTION]
```

`--sections` is 1-indexed: `1`, `3-7`, `1,3-8`. `--refetch` re-runs AI enrichment even if a
cached result is already in the spec.

## AI enrichment (optional, additive)

Add a `**ContentUrls**` block to a `## [content]`, `## [two-column]`, or notes section and the
tool fetches each URL, then asks the configured model to synthesize supplemental bullets/notes:

```markdown
## [content] My Section

- Seed bullet

**ContentUrls**:
- https://example.com
```

Without `content_urls`, **no model call happens** and the docx builds fully offline. Enrichment
never overwrites your spec — it appends supplemental material.

## Project layout

```
documents.py              thin CLI wrapper
make_docx.bat             Windows convenience wrapper (venv + deps)
mcp_server.py             MCP server (use as a Claude Code / agent tool)
requirements.txt          python-docx, pyyaml, lxml, python-dotenv, openai, mcp
src/
  cli.py                  arg parsing + .env loading
  spec_parser.py          .spec.md -> metadata + section list
  renderer.py             orchestrates enrichment + section building -> docx
  sections.py             section builders (title, content, two-column, etc.)
  style.py                front-matter style -> document theme
  enrichment.py           URL fetching + OpenRouter chat completions (the swapped module)
  images.py               image generation (no-op in this build)
  spec_writer.py          writes enriched spec back to disk
```

## License

MIT. This fork retains the upstream [MIT license](LICENSE) from
[microsoft/documents](https://github.com/microsoft/documents). Forked from commit
`d878ed7`.
