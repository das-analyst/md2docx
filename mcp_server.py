"""MCP server wrapper for the docx-generator.

Exposes the document generator as MCP tools so Claude Code (and any
OpenAI-compatible MCP client) can produce .docx files from .spec.md specs
without being told the exact CLI invocation.

Run with:  python -m mcp_server
"""

from __future__ import annotations

import asyncio
import io
import os
import re
import sys
from contextlib import redirect_stdout

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Honor a .env in the launching project before enrichment runs.
from src.cli import _load_env

_load_env()

mcp_server = Server("docx-generator")

# Regex matching renderer.py's final output line: "Saved N sections -> <path>"
_SAVED_RE = re.compile(r"Saved\s+(\d+)\s+sections\s*->\s*(.+)")


@mcp_server.list_tools()
async def _list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_docx",
            description=(
                "Generate a styled Word (.docx) document from a SpecKit .spec.md file. "
                "Use when the user asks to produce, build, or export a .docx / Word document, "
                "or to convert structured content into a formatted document. "
                "Returns the path to the generated .docx."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "spec": {
                        "type": "string",
                        "description": "Absolute or project-relative path to the .spec.md file.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": (
                            "Directory for the generated .docx. "
                            "Defaults to the directory containing the spec."
                        ),
                    },
                    "image_model": {
                        "type": "string",
                        "description": "Override the front-matter 'image_model' (images are disabled in the OpenRouter build).",
                    },
                    "refetch": {
                        "type": "boolean",
                        "description": "Re-run AI enrichment even if cached results exist.",
                    },
                    "sections": {
                        "type": "string",
                        "description": (
                            "1-based section selection. "
                            "Examples: '5' (one), '3-7' (range), '1,3,5-8' (mixed)."
                        ),
                    },
                },
                "required": ["spec"],
            },
        ),
        Tool(
            name="list_section_types",
            description=(
                "Return the valid SpecKit section types and directive syntax "
                "so you can author a correct .spec.md for generate_docx."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@mcp_server.call_tool()
async def _call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "list_section_types":
        return [_text(_SECTION_TYPES_DOC)]

    if name == "generate_docx":
        return await _generate_docx(arguments)

    return [_text(f"Unknown tool: {name}")]


async def _generate_docx(arguments: dict) -> list[TextContent]:
    from src.cli import main

    spec = arguments.get("spec", "").strip()
    output_dir = arguments.get("output_dir") or ""
    image_model = arguments.get("image_model") or None
    refetch = bool(arguments.get("refetch", False))
    sections = arguments.get("sections") or None

    if not spec:
        return [_text('{"error": "spec is required"}')]

    # Resolve relative to cwd (the project Claude Code was launched in).
    spec_path = spec if os.path.isabs(spec) else os.path.abspath(spec)

    argv: list[str] = [spec_path]
    if output_dir:
        argv.extend(["-o", output_dir])
    if image_model:
        argv.extend(["--image-model", image_model])
    if refetch:
        argv.append("--refetch")
    if sections:
        argv.extend(["--sections", sections])

    # Run the CLI in-process, capturing its stdout to parse the output path.
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            main(argv)
    except SystemExit as exc:
        message = str(exc).strip() or "CLI exited with an error"
        return [_text(f'{{"error": "{message}"}}')]
    except Exception as exc:  # noqa: BLE001 - surface any failure to Claude
        return [_text(f'{{"error": "{exc}"}}')]

    output = buf.getvalue()
    match = _SAVED_RE.search(output)
    if match:
        sections_n = int(match.group(1))
        out_path = match.group(2).strip()
        return [
            _text(
                f'{{"output_path": "{out_path}", "sections": {sections_n}}}'
            )
        ]

    # CLI ran but we couldn't parse the path; return captured output for debugging.
    return [_text(f'{{"output": {output!r}}}')]


def _text(s: str) -> TextContent:
    return TextContent(type="text", text=s)


_SECTION_TYPES_DOC = """Valid SpecKit section types for .spec.md files (exactly five):

1. title — cover page
   Directives: **Subtitle**:, **Notes**:

2. content — heading + bullet list
   Directives: **Notes**:, **ContentUrls**: (list of URLs -> triggers AI enrichment),
   **Enriched**: true (cache marker), **Image**: path,left,top,width,height,
   **ImagePrompt**: description[, left, top, width, height]

3. section-header — section break (auto page-breaks)
   Directives: **Subtitle**:, **Notes**:

4. two-column — two bullet columns
   Directives: **Left**: / **Right**: (each followed by bullets), **Notes**:

5. resource-box — labelled link tables
   Directives: **Subtitle**:, **Box**: Label followed by rows "- Name | https://url"

Front-matter keys (YAML between the opening --- fences):
   title, subtitle, output (<name>.docx), author,
   text_model (OpenRouter model id, e.g. openai/gpt-4o-mini),
   image_model (accepted, ignored in OpenRouter build),
   style.{title_font_size, subtitle_font_size, body_font_size,
           heading_font_size, heading_color, accent_color}

Sections are split by a bare --- on its own line.
The output: key names the .docx; output is versioned (doc.docx, doc_1.docx, ...).
"""


async def _async_main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
