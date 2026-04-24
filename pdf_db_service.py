"""Database-backed PDF utilities for Chainlit actions.

This module keeps DB access and layout-aware PDF regeneration in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import re

from dotenv import load_dotenv
import fitz

# psycopg2 is optional; provide a filesystem fallback when not available
try:
    import psycopg2
    import psycopg2.extras
    HAS_PG = True
except Exception:
    psycopg2 = None
    HAS_PG = False


load_dotenv()

PREVIEW_DIR = Path(".files") / "db_pdf_previews"
BLACK_TEXT_COLOR = (0.0, 0.0, 0.0)
FALLBACK_DB_DIR = Path(".files") / "pdf_store"


@dataclass
class SpanTemplate:
    page_index: int
    bbox: tuple[float, float, float, float]
    font_size: float
    color: int
    text: str


def _db_config() -> dict:
    return {
        "database": os.getenv("DB_NAME", "codestorm"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "5432")),
    }


def list_pdf_names() -> list[str]:
    if HAS_PG:
        conn = psycopg2.connect(**_db_config())
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT DISTINCT nume_fisier FROM documente_scoala ORDER BY nume_fisier")
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
    else:
        FALLBACK_DB_DIR.mkdir(parents=True, exist_ok=True)
        return [p.name for p in sorted(FALLBACK_DB_DIR.glob("*.pdf"))]


def get_pdf_bytes(pdf_name: str) -> bytes | None:
    if HAS_PG:
        conn = psycopg2.connect(**_db_config())
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT fisier_pdf FROM documente_scoala WHERE nume_fisier = %s LIMIT 1",
                (pdf_name,),
            )
            row = cursor.fetchone()
            return bytes(row[0]) if row and row[0] is not None else None
        finally:
            cursor.close()
            conn.close()
    else:
        FALLBACK_DB_DIR.mkdir(parents=True, exist_ok=True)
        file_path = FALLBACK_DB_DIR / pdf_name
        if not file_path.exists():
            # also try with .pdf extension
            file_path = FALLBACK_DB_DIR / f"{pdf_name}.pdf"
            if not file_path.exists():
                return None
        return file_path.read_bytes()


def save_pdf_bytes(pdf_name: str, pdf_bytes: bytes) -> int:
    if HAS_PG:
        conn = psycopg2.connect(**_db_config())
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE documente_scoala SET fisier_pdf = %s WHERE nume_fisier = %s",
                (psycopg2.Binary(pdf_bytes), pdf_name),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            cursor.close()
            conn.close()
    else:
        FALLBACK_DB_DIR.mkdir(parents=True, exist_ok=True)
        # save to filename with .pdf extension
        file_path = FALLBACK_DB_DIR / (pdf_name if pdf_name.lower().endswith('.pdf') else f"{pdf_name}.pdf")
        file_path.write_bytes(pdf_bytes)
        return 1


def extract_text_and_layout(pdf_bytes: bytes) -> tuple[str, list[SpanTemplate]]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    spans: list[SpanTemplate] = []
    lines: list[str] = []

    for page_index, page in enumerate(doc):
        data = page.get_text("dict")
        for block in data.get("blocks", []):
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                line_parts: list[str] = []
                for span in line.get("spans", []):
                    raw_text = span.get("text", "")
                    if not raw_text:
                        continue

                    bbox_vals = span.get("bbox", (0.0, 0.0, 0.0, 0.0))
                    bbox = (
                        float(bbox_vals[0]),
                        float(bbox_vals[1]),
                        float(bbox_vals[2]),
                        float(bbox_vals[3]),
                    )

                    spans.append(
                        SpanTemplate(
                            page_index=page_index,
                            bbox=bbox,
                            font_size=float(span.get("size", 11.0)),
                            color=int(span.get("color", 0)),
                            text=raw_text,
                        )
                    )
                    line_parts.append(raw_text)

                if line_parts:
                    lines.append("".join(line_parts))

    doc.close()
    return "\n".join(lines).strip(), spans


def _chunk_text_for_spans(edited_text: str, templates: list[SpanTemplate]) -> list[str]:
    normalized = " ".join(edited_text.replace("\r", "").split())
    if not normalized:
        return [""] * len(templates)

    lengths = [max(1, len(item.text)) for item in templates]
    total = sum(lengths)
    target = len(normalized)

    chunk_sizes = [max(1, round(target * length / total)) for length in lengths]

    drift = sum(chunk_sizes) - target
    idx = len(chunk_sizes) - 1
    while drift > 0 and idx >= 0:
        if chunk_sizes[idx] > 1:
            chunk_sizes[idx] -= 1
            drift -= 1
        else:
            idx -= 1

    idx = len(chunk_sizes) - 1
    while drift < 0 and idx >= 0:
        chunk_sizes[idx] += 1
        drift += 1
        idx -= 1
        if idx < 0:
            idx = len(chunk_sizes) - 1

    chunks: list[str] = []
    pos = 0
    for size in chunk_sizes:
        chunks.append(normalized[pos:pos + size])
        pos += size

    return chunks


def regenerate_pdf_with_layout(original_pdf: bytes, edited_text: str, templates: list[SpanTemplate]) -> bytes:
    doc = fitz.open(stream=original_pdf, filetype="pdf")
    chunks = _chunk_text_for_spans(edited_text, templates)

    for span, new_text in zip(templates, chunks):
        page = doc[span.page_index]
        rect = fitz.Rect(span.bbox)

        page.draw_rect(rect, fill=(1, 1, 1), color=(1, 1, 1), overlay=True)
        page.insert_textbox(
            rect,
            new_text,
            fontsize=max(6.0, span.font_size),
            fontname="helv",
            # Always force edited text to black, regardless of original span color.
            color=BLACK_TEXT_COLOR,
            align=fitz.TEXT_ALIGN_LEFT,
            render_mode=0,
            stroke_opacity=1,
            fill_opacity=1,
        )

    out = doc.tobytes()
    doc.close()
    return out


def write_preview_pdf(pdf_name: str, pdf_bytes: bytes, suffix: str = "") -> str:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(pdf_name).stem)
    file_path = PREVIEW_DIR / f"{safe_name}{suffix}.pdf"
    file_path.write_bytes(pdf_bytes)
    return str(file_path)
