"""Extract plain text from a folder of PDFs (read-only helper).

Usage:
    python scripts/pdf_extract.py "C:/path/to/pdfs" --out results/pdftext

Requires ``pypdf`` (``python -m pip install pypdf``). This is intentionally simple:
it extracts text for reading/searching, not for layout fidelity.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def slugify(name: str, limit: int = 80) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    return (slug[:limit] or "document").lower()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="PDF file or directory")
    parser.add_argument("--out", default="results/pdftext", help="output directory")
    parser.add_argument("--max-pages", type=int, default=0, help="0 = all pages")
    args = parser.parse_args()

    try:
        from pypdf import PdfReader
    except ImportError:
        raise SystemExit("pypdf is missing. Install it with: python -m pip install pypdf")

    source = Path(args.source)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)

    files = [source] if source.is_file() else sorted(source.glob("*.pdf"))
    if not files:
        raise SystemExit(f"No PDFs found in {source}")

    for pdf in files:
        try:
            reader = PdfReader(str(pdf))
            pages = reader.pages[: args.max_pages] if args.max_pages else reader.pages
            text = "\n\n".join((page.extract_text() or "") for page in pages)
        except Exception as error:  # noqa: BLE001 - report and continue with the next file
            print(f"[FAIL] {pdf.name}: {type(error).__name__}: {error}")
            continue

        target = output / f"{slugify(pdf.stem)}.txt"
        target.write_text(text, encoding="utf-8")
        print(f"{pdf.name} | pages={len(reader.pages)} | chars={len(text)} | -> {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
