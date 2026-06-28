# spec-docx (OpenRouter build)

Generate styled **Word documents (`.docx`) from Markdown spec files** — with optional AI
enrichment powered by **OpenRouter** instead of Azure AI.

Adapted from [microsoft/documents](https://github.com/microsoft/d878ed7) (MIT), which generates
`.docx` from `.spec.md` files but is coupled to Azure AI Foundry (`AzureOpenAI` +
`DefaultAzureCredential`). This fork keeps the renderer and swaps the LLM layer to any
**OpenAI-compatible endpoint** — tested against OpenRouter — so you can run it with a single
API key and no Azure subscription.

## Why this exists

The upstream `microsoft/documents` (and its sibling `microsoft/presentations`) are great
spec-driven generators, but they assume an Azure AI Foundry project: subscription, Foundry
workspace, model deployments, `az login`. That's a real setup wall.

This fork drops that to **30 seconds**:

| | upstream | this fork |
|---|---|---|
| LLM provider | Azure AI Foundry only | any OpenAI-compatible endpoint (OpenRouter, OpenAI, local) |
| Auth | `DefaultAzureCredential` + `az login` | one API key |
| Azure subscription | required | **not required** |
| Core docx rendering | offline | offline (unchanged) |
| AI enrichment | Azure OpenAI | OpenRouter / any `openai` SDK target |
| Image generation | Azure OpenAI DALL-E | **disabled** (see note below) |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate.bat      # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Set your key (get one at https://openrouter.ai/keys):

- **Option A — `.env`:** copy `.env.example` → `.env` and set `OPENROUTER_API_KEY`.
- **Option B — environment:** `export OPENROUTER_API_KEY=...` (or add to your shell profile).

The tool loads `<cwd>/.env` with `override=False`, so existing env vars win.

## Quick start

```bash
# Run against the bundled example spec
python documents.py .speckit/specifications/example.spec.md -o output

# Or use the Windows wrapper (auto-creates venv + installs deps)
make_docx.bat .speckit/specifications/example.spec.md -o output
```

## Writing a spec

A `.spec.md` has **YAML front-matter** + a **markdown body**. Sections are separated by `---`
horizontal rules and opened with a typed header:

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

### Front-matter keys

- `text_model` — OpenRouter model ID for enrichment (e.g. `openai/gpt-4o-mini`,
  `anthropic/claude-3.5-sonnet`, `google/gemini-2.0-flash-001`). Optional; enrichment is skipped
  if unset.
- `image_model` — accepted but **ignored** (images disabled in this build; see note below).
- `style.*` — fonts and colors for the document theme.

### CLI flags

```
python documents.py <spec> [-o output_dir] [--image-model MODEL] [--refetch] [--sections SELECTION]
```

`--sections` is 1-indexed: `1`, `3-7`, `1,3-8`.

## AI enrichment (optional)

Add a `**ContentUrls**` block to a `## [content]`, `## [two-column]`, or notes section and the
tool fetches each URL, then asks the configured model to synthesize supplemental bullets/notes:

```markdown
## [content] My Section

- Seed bullet

**ContentUrls**:
- https://example.com
```

Without `content_urls`, **no model call happens** and the docx builds fully offline. Enrichment
is additive — your spec is the source of truth.

## Using with Claude Code (or any LLM agent)

Because the interface is "write a `.spec.md`, run a one-line command, get a `.docx`", this tool
works well as a generation step inside an LLM agent loop. Claude Code (or similar) can author
the spec from a conversation or a source document, invoke `documents.py`, and return the
resulting Word file. No Azure infra to provision, no credentials to manage beyond one key.

## Image generation — disabled, be aware

OpenRouter does not currently expose a stable `/images/generations` endpoint, so image
generation is a **no-op** in this build. `image_prompt` directives are skipped with a printed
warning; the docx still builds cleanly. To re-enable images, point the client at a provider with
an OpenAI-compatible images endpoint (e.g. OpenAI directly) and wire it into `src/images.py`.

## Project layout

```
documents.py              thin CLI wrapper
make_docx.bat             Windows convenience wrapper (venv + deps)
requirements.txt          python-docx, pyyaml, lxml, python-dotenv, openai
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
