from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
from marker.renderers.markdown import MarkdownOutput


def save_markdown_output(rendered: MarkdownOutput, pdf_path: Path) -> None:
    stem = pdf_path.stem
    image_dir = pdf_path.parent / f"{stem}_images"
    image_dir.mkdir(parents=True, exist_ok=True)
    markdown = rendered.markdown
    for name, image in rendered.images.items():
        image = image.convert("RGB") if image.mode != "RGB" else image
        image.save(image_dir / name, "JPEG")
        # Markdown destinations cannot contain bare spaces or parentheses.
        destination = quote(f"{stem}_images/{name}", safe="/")
        markdown = markdown.replace(f"]({name})", f"]({destination})")
    tmp = pdf_path.with_suffix(".md.tmp")
    tmp.write_text(markdown, encoding="utf-8")
    tmp.replace(pdf_path.with_suffix(".md"))


def output_complete(pdf_path: Path) -> bool:
    md = pdf_path.with_suffix(".md")
    image_dir = pdf_path.parent / f"{pdf_path.stem}_images"
    return md.exists() and image_dir.exists()
