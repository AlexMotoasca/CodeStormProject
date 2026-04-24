"""Standalone PDF editor with layout-aware regeneration.

This tool is isolated from the Chainlit/Gemini flow so you can work
independently without touching teammates' files.

What it does:
- Lists PDFs from ./PDFs
- Extracts editable text from the selected PDF
- Keeps page/span layout metadata from the original file
- Saves an edited PDF that reuses original text boxes as template

Run:
    python pdf_editor_standalone.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

import fitz


PDF_DIR = Path("PDFs")
OUTPUT_DIR = Path("edited_pdf")


@dataclass
class SpanTemplate:
    page_index: int
    bbox: tuple[float, float, float, float]
    font_size: float
    color: int
    text: str


class PdfEditorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PDF List Editor (Standalone)")
        self.root.geometry("1100x700")

        self.current_pdf: Path | None = None
        self.current_spans: list[SpanTemplate] = []

        self._build_layout()
        self.refresh_pdf_list()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        left_panel = ttk.Frame(container)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)

        right_panel = ttk.Frame(container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        ttk.Label(left_panel, text="PDF files", font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.pdf_listbox = tk.Listbox(left_panel, width=40, height=30)
        self.pdf_listbox.pack(fill=tk.Y, pady=(8, 8))
        self.pdf_listbox.bind("<<ListboxSelect>>", self._on_pdf_selected)

        button_row = ttk.Frame(left_panel)
        button_row.pack(fill=tk.X)
        ttk.Button(button_row, text="Refresh", command=self.refresh_pdf_list).pack(side=tk.LEFT)
        ttk.Button(button_row, text="Load", command=self.load_selected_pdf).pack(side=tk.LEFT, padx=8)

        header_row = ttk.Frame(right_panel)
        header_row.pack(fill=tk.X)

        self.current_label = ttk.Label(header_row, text="No PDF loaded")
        self.current_label.pack(side=tk.LEFT)

        ttk.Button(header_row, text="Save Edited PDF", command=self.save_edited_pdf).pack(side=tk.RIGHT)

        self.editor = tk.Text(right_panel, wrap=tk.WORD, undo=True)
        self.editor.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    def refresh_pdf_list(self) -> None:
        PDF_DIR.mkdir(parents=True, exist_ok=True)
        pdfs = sorted(PDF_DIR.glob("*.pdf"), key=lambda p: p.name.lower())

        self.pdf_listbox.delete(0, tk.END)
        for pdf in pdfs:
            self.pdf_listbox.insert(tk.END, pdf.name)

        if not pdfs:
            messagebox.showinfo("Info", f"No PDF files found in: {PDF_DIR.resolve()}")

    def _on_pdf_selected(self, _event: object) -> None:
        if self.pdf_listbox.curselection():
            self.load_selected_pdf()

    def load_selected_pdf(self) -> None:
        selection = self.pdf_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select a PDF first.")
            return

        file_name = self.pdf_listbox.get(selection[0])
        pdf_path = PDF_DIR / file_name

        try:
            text, spans = self._extract_text_and_layout(pdf_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not read {file_name}\n\n{exc}")
            return

        self.current_pdf = pdf_path
        self.current_spans = spans
        self.current_label.config(text=f"Loaded: {file_name}")
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", text)

    @staticmethod
    def _extract_text_and_layout(pdf_path: Path) -> tuple[str, list[SpanTemplate]]:
        doc = fitz.open(str(pdf_path))
        spans: list[SpanTemplate] = []
        lines: list[str] = []

        for page_index, page in enumerate(doc):
            data = page.get_text("dict")
            for block in data.get("blocks", []):
                if block.get("type") != 0:
                    continue

                for line in block.get("lines", []):
                    line_text_parts: list[str] = []
                    for span in line.get("spans", []):
                        raw_text = span.get("text", "")
                        if not raw_text:
                            continue

                        spans.append(
                            SpanTemplate(
                                page_index=page_index,
                                bbox=tuple(span.get("bbox", (0, 0, 0, 0))),
                                font_size=float(span.get("size", 11.0)),
                                color=int(span.get("color", 0)),
                                text=raw_text,
                            )
                        )
                        line_text_parts.append(raw_text)

                    if line_text_parts:
                        lines.append("".join(line_text_parts))

        doc.close()
        return "\n".join(lines).strip(), spans

    def save_edited_pdf(self) -> None:
        if self.current_pdf is None:
            messagebox.showwarning("Warning", "Load a PDF before saving.")
            return

        if not self.current_spans:
            messagebox.showwarning("Warning", "No layout template found for this PDF.")
            return

        content = self.editor.get("1.0", tk.END).rstrip()
        if not content:
            messagebox.showwarning("Warning", "Editor is empty. Nothing to save.")
            return

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_file = OUTPUT_DIR / f"{self.current_pdf.stem}_edited.pdf"

        try:
            self._write_layout_preserved_pdf(self.current_pdf, content, self.current_spans, output_file)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not save file\n\n{exc}")
            return

        messagebox.showinfo("Saved", f"Edited PDF saved to:\n{output_file.resolve()}")

    @staticmethod
    def _chunk_text_for_spans(edited_text: str, templates: list[SpanTemplate]) -> list[str]:
        normalized = " ".join(edited_text.replace("\r", "").split())
        if not normalized:
            return [""] * len(templates)

        lengths = [max(1, len(t.text)) for t in templates]
        total = sum(lengths)
        target = len(normalized)

        chunk_sizes = [max(1, round(target * ln / total)) for ln in lengths]

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

    @staticmethod
    def _rgb_from_color_int(color_value: int) -> tuple[float, float, float]:
        red = ((color_value >> 16) & 255) / 255.0
        green = ((color_value >> 8) & 255) / 255.0
        blue = (color_value & 255) / 255.0
        return red, green, blue

    @classmethod
    def _write_layout_preserved_pdf(
        cls,
        source_pdf: Path,
        edited_text: str,
        templates: list[SpanTemplate],
        output_file: Path,
    ) -> None:
        doc = fitz.open(str(source_pdf))
        chunks = cls._chunk_text_for_spans(edited_text, templates)

        for span, new_text in zip(templates, chunks):
            page = doc[span.page_index]
            rect = fitz.Rect(span.bbox)

            page.draw_rect(rect, fill=(1, 1, 1), color=(1, 1, 1), overlay=True)
            page.insert_textbox(
                rect,
                new_text,
                fontsize=max(6.0, span.font_size),
                fontname="helv",
                color=(0, 0, 0),
                align=fitz.TEXT_ALIGN_LEFT,
            )

        doc.save(str(output_file))
        doc.close()


def main() -> None:
    root = tk.Tk()
    PdfEditorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

