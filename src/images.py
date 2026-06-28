"""Image generation — DISABLED for the OpenRouter build.

OpenRouter does not currently expose a stable /images/generations endpoint,
so image generation is intentionally a no-op here. ImagePrompt directives
are skipped with a printed warning. The docx core generation is unaffected.

To re-enable images, configure a provider that exposes an OpenAI-compatible
images endpoint (e.g. OpenAI directly, or a local endpoint) and point the
client/base URL + auth at it.
"""

from __future__ import annotations

from typing import Any


def generate_image(
    prompt: str,
    output_dir: str,
    model: str,
    size: str = "1024x1024",
) -> str | None:
    """No-op: image generation is not available via OpenRouter.

    Returns None so callers treat it like a failed/omitted image.
    """
    print(
        f"  [images] Skipping image generation (not supported via OpenRouter): "
        f"{prompt[:80]}..."
    )
    return None


def resolve_image_prompt(
    section_data: dict,
    output_dir: str,
    default_model: str = "",
) -> None:
    """No-op: leave the section unchanged; warn if an ImagePrompt was set."""
    ip = section_data.get("image_prompt")
    if not ip:
        return
    print(
        "  [images] ImagePrompt present but image generation is disabled in the "
        "OpenRouter build. Set up an images-compatible endpoint to enable."
    )
