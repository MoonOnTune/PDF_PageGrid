#!/usr/bin/env python3
"""
PDF_PageGrid.py
----------------
Render each PDF into ONE high-quality image containing all its pages.
- Works on a single PDF file or an entire folder of PDFs.
- Adjustable DPI (print quality), margins, spacing, and grid layout.
- Export PNG, JPEG, or both in one run.

Dependencies:
    pip install pymupdf Pillow

Examples:
    # Single tall image (all pages stacked), 300 DPI, 20px margins, 8px spacing
    python PDF_PageGrid.py -i "/path/file.pdf" -o "/path/out" --dpi 300 --cols 1 --margin 20 --spacing 8

    # Auto grid (roughly square), 240 DPI, whole folder
    python PDF_PageGrid.py -i "/path/folder_with_pdfs" -o "/path/out" --dpi 240 --cols auto --both

    # 3 columns grid, 300 DPI, light gray background
    python PDF_PageGrid.py -i "/path/file.pdf" -o "/path/out" --dpi 300 --cols 3 --bg "#f7f7f7" --formats PNG,JPEG

Notes:
- High DPI (e.g., 300) makes very large images; ensure you have enough RAM/disk.
- If your PDF has mixed page sizes, the script pads to the largest page size so the grid stays aligned.
- Output files are PNG by default to preserve quality; you can choose JPEG if desired or both.
"""

import argparse
import math
import os
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import fitz  # PyMuPDF
except ImportError as e:
    print("ERROR: PyMuPDF (fitz) is not installed. Install with: pip install pymupdf", file=sys.stderr)
    raise

try:
    from PIL import Image, ImageColor
except ImportError as e:
    print("ERROR: Pillow is not installed. Install with: pip install Pillow", file=sys.stderr)
    raise


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render each PDF into one high-quality image containing all its pages.")
    p.add_argument("-i", "--input", required=True, help="Path to a PDF file or a folder containing PDFs.")
    p.add_argument("-o", "--output", required=True, help="Output folder for generated images.")
    p.add_argument("--dpi", type=int, default=300, help="Render DPI (quality). 300 is print quality. Default: 300")
    p.add_argument("--cols", default="auto", help="Number of columns for the grid, or '1' to stack vertically, or 'auto' for auto grid. Default: auto")
    p.add_argument("--margin", type=int, default=16, help="Outer margin (pixels) around the whole poster image. Default: 16")
    p.add_argument("--spacing", type=int, default=8, help="Spacing (pixels) between pages in the grid. Default: 8")
    p.add_argument("--bg", default="#FFFFFF", help="Background color (e.g., '#FFFFFF' or 'white'). Default: white")
    # Legacy single-format option kept for compatibility
    p.add_argument("--format", choices=["PNG", "JPG", "JPEG"], default="PNG", help="(Legacy) Single output format. Default: PNG")
    # New multi-format options
    p.add_argument("--both", action="store_true", help="Export both PNG and JPEG for each PDF.")
    p.add_argument("--formats", type=str, default="", help="Comma-separated list of formats to export, e.g. 'PNG,JPEG'. Overrides --format if provided.")
    p.add_argument("--suffix", default="_poster", help="Filename suffix before extension. Default: _poster")
    p.add_argument("--max_width", type=int, default=0, help="Optional: downscale final image if wider than this (pixels). 0 = no limit.")
    p.add_argument("--quality", type=int, default=95, help="JPEG quality if format is JPG/JPEG. Default: 95")
    p.add_argument("--verbose", action="store_true", help="Print more details.")
    return p.parse_args()


def resolve_formats(args: argparse.Namespace) -> List[str]:
    if args.formats:
        fmts = [f.strip().upper() for f in args.formats.split(",") if f.strip()]
    elif args.both:
        fmts = ["PNG", "JPEG"]
    else:
        fmts = [args.format.upper()]
    # Normalize JPG alias
    fmts = ["JPEG" if f == "JPG" else f for f in fmts]
    # Dedup, preserve order
    seen = set()
    out = []
    for f in fmts:
        if f not in ("PNG", "JPEG"):
            print(f"WARNING: Unsupported format '{f}' ignored. Supported: PNG, JPEG.", file=sys.stderr)
            continue
        if f not in seen:
            seen.add(f)
            out.append(f)
    if not out:
        out = ["PNG"]
    return out


def find_pdfs(path: Path) -> List[Path]:
    if path.is_file() and path.suffix.lower() == ".pdf":
        return [path]
    if path.is_dir():
        return sorted([p for p in path.rglob("*.pdf")])
    return []


def dpi_to_zoom(dpi: int) -> float:
    # 72 points per inch is the PDF display baseline
    return dpi / 72.0


def render_pdf_pages(pdf_path: Path, dpi: int, verbose: bool=False) -> List[Image.Image]:
    """Render each page of a PDF to a PIL Image at the requested DPI."""
    if verbose:
        print(f"[render] {pdf_path.name} @ {dpi} DPI")

    zoom = dpi_to_zoom(dpi)
    mat = fitz.Matrix(zoom, zoom)

    images: List[Image.Image] = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            pm = page.get_pixmap(matrix=mat, alpha=False)  # RGB
            img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
            images.append(img)
            if verbose:
                print(f"  - page {i+1}/{len(doc)} -> {img.size[0]}x{img.size[1]}")
    return images


def compute_grid(n_pages: int, cols: str) -> Tuple[int, int]:
    """Return (columns, rows)."""
    if cols == "1":
        return 1, n_pages
    if cols.lower() == "auto":
        c = math.ceil(math.sqrt(n_pages))
        r = math.ceil(n_pages / c)
        return c, r
    # explicit integer
    c = max(1, int(cols))
    r = math.ceil(n_pages / c)
    return c, r


def make_poster(images: List[Image.Image], cols: int, rows: int, margin: int, spacing: int, bg: str, verbose: bool=False) -> Image.Image:
    """Compose images into a single grid poster with uniform cells padded to the max page size."""
    if not images:
        raise ValueError("No images to compose.")

    # Convert bg to RGB
    bg_rgb = ImageColor.getrgb(bg)

    # Determine cell size: max width/height across pages
    cell_w = max(im.width for im in images)
    cell_h = max(im.height for im in images)

    grid_w = cols * cell_w + (cols - 1) * spacing
    grid_h = rows * cell_h + (rows - 1) * spacing

    total_w = grid_w + 2 * margin
    total_h = grid_h + 2 * margin

    if verbose:
        print(f"[compose] grid {cols}x{rows}, cell={cell_w}x{cell_h}, total={total_w}x{total_h}")

    poster = Image.new("RGB", (total_w, total_h), bg_rgb)

    # Paste each page centered in its cell
    for idx, im in enumerate(images):
        r = idx // cols
        c = idx % cols
        x0 = margin + c * (cell_w + spacing)
        y0 = margin + r * (cell_h + spacing)
        # Center the page image in the cell
        off_x = x0 + (cell_w - im.width) // 2
        off_y = y0 + (cell_h - im.height) // 2
        poster.paste(im, (off_x, off_y))

    return poster


def downscale_if_needed(img: Image.Image, max_width: int, verbose: bool=False) -> Image.Image:
    if max_width <= 0 or img.width <= max_width:
        return img
    ratio = max_width / img.width
    new_size = (max_width, max(1, int(img.height * ratio)))
    if verbose:
        print(f"[resize] {img.width}x{img.height} -> {new_size[0]}x{new_size[1]}")
    return img.resize(new_size, Image.LANCZOS)


def save_image(img: Image.Image, out_path: Path, fmt: str, quality: int=95, verbose: bool=False) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt.upper() == "JPEG":
        img.save(out_path, format="JPEG", quality=quality, subsampling=0, optimize=True)
    else:
        img.save(out_path, format="PNG", optimize=True)
    if verbose:
        print(f"[save] {out_path} ({fmt})")


def process_pdf(pdf_path: Path, out_dir: Path, dpi: int, cols_spec: str, margin: int, spacing: int, bg: str, fmts: List[str], suffix: str, max_width: int, quality: int, verbose: bool=False) -> List[Path]:
    pages = render_pdf_pages(pdf_path, dpi=dpi, verbose=verbose)
    cols, rows = compute_grid(len(pages), cols_spec)
    poster = make_poster(pages, cols, rows, margin, spacing, bg, verbose=verbose)
    poster = downscale_if_needed(poster, max_width=max_width, verbose=verbose)

    out_paths = []
    for fmt in fmts:
        ext = ".jpg" if fmt.upper() == "JPEG" else ".png"
        stem = pdf_path.stem + suffix
        out_path = out_dir / f"{stem}{ext}"
        save_image(poster, out_path, fmt=fmt.upper(), quality=quality, verbose=verbose)
        out_paths.append(out_path)
    return out_paths


def main():
    args = parse_args()
    fmts = resolve_formats(args)
    in_path = Path(args.input).expanduser()
    out_dir = Path(args.output).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    pdfs = find_pdfs(in_path)
    if not pdfs:
        print("No PDFs found. Provide a path to a PDF or a folder containing PDFs.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(pdfs)} PDF(s). Output -> {out_dir}. Formats: {', '.join(fmts)}")
    for pdf in pdfs:
        try:
            outs = process_pdf(
                pdf_path=pdf,
                out_dir=out_dir,
                dpi=args.dpi,
                cols_spec=args.cols,
                margin=args.margin,
                spacing=args.spacing,
                bg=args.bg,
                fmts=fmts,
                suffix=args.suffix,
                max_width=args.max_width,
                quality=args.quality,
                verbose=args.verbose,
            )
            names = ", ".join(p.name for p in outs)
            print(f"OK: {pdf.name} -> {names}")
        except Exception as e:
            print(f"ERROR processing {pdf}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
