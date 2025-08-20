# PDF-PageGrid

Turn each PDF into **one** high‑quality image containing all its pages—perfect for thumbnails, previews, and archives.

**Key features**
- Batch mode (point at a folder of PDFs)
- Print‑quality DPI (default 300)
- Auto or fixed page grid
- Configurable margins, spacing, background
- Export **PNG, JPEG, or both** in one run

## Install
```bash
pip install pymupdf Pillow
```

## Usage
Convert a single PDF:
```bash
python PDF_PageGrid.py -i "/path/file.pdf" -o "/path/out"
```

Batch convert a folder and export both PNG and JPEG:
```bash
python PDF_PageGrid.py -i "/path/folder" -o "/path/out" --both
```

Auto grid at 240 DPI:
```bash
python PDF_PageGrid.py -i "/path/folder" -o "/path/out" --dpi 240 --cols auto
```

### Common flags
- `--dpi 300` : render quality (higher = sharper & larger)
- `--cols 1|auto|N` : vertical stack, automatic grid, or fixed columns
- `--margin 16` : outer margin (pixels)
- `--spacing 8` : space between pages (pixels)
- `--bg "#FFFFFF"` : background color
- `--both` : export PNG + JPEG
- `--formats PNG,JPEG` : custom list of formats
- `--max_width 20000` : optional downscale of the final image
- `--quality 95` : JPEG quality (if exporting JPEG)

> PNG is lossless and ideal for print/archival; JPEG is smaller and good for sharing.
