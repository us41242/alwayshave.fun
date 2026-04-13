"""
resize_photos.py — Generate responsive hero images at multiple breakpoints.

For each trail photo, creates sized variants:
  {slug}-640.jpg   — mobile (640px wide, ~60-80KB)
  {slug}-1280.jpg  — tablet/laptop (1280px wide, ~150-200KB)
  {slug}-1920.jpg  — desktop (1920px wide, ~250-350KB)
  {slug}.jpg       — original (untouched, for 4K/retina fallback)

Skips generation if the sized file already exists and is newer than the source.
"""

import os
import subprocess
import glob

PHOTOS_DIR = "photos"
SIZES = [640, 1280, 1920]
QUALITY = 82  # JPEG quality — good balance of size vs clarity

def resize_image(src, dst, width, quality=QUALITY):
    """Resize image to given width using sips, maintaining aspect ratio."""
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(quality),
         "-Z", str(width), src, "--out", dst],
        capture_output=True
    )

def main():
    # Find all hero JPGs (not cards, not already-sized)
    pattern = os.path.join(PHOTOS_DIR, "*", "*.jpg")
    sources = []
    for f in glob.glob(pattern):
        base = os.path.basename(f)
        # Skip card images and already-sized variants
        if "-card" in base:
            continue
        if any(f"-{s}." in base for s in SIZES):
            continue
        sources.append(f)

    # Also handle the LANDING image
    landing = os.path.join(PHOTOS_DIR, "LANDINGcathedral-rock-sedona-az.jpg")
    if os.path.exists(landing):
        sources.append(landing)

    total = 0
    skipped = 0

    for src in sorted(sources):
        src_mtime = os.path.getmtime(src)
        dirname = os.path.dirname(src)
        basename = os.path.basename(src)
        name, ext = os.path.splitext(basename)

        for width in SIZES:
            dst = os.path.join(dirname, f"{name}-{width}{ext}")
            # Skip if already exists and newer than source
            if os.path.exists(dst) and os.path.getmtime(dst) >= src_mtime:
                skipped += 1
                continue

            resize_image(src, dst, width)
            size_kb = os.path.getsize(dst) / 1024
            print(f"  ✓ {dst} ({width}px, {size_kb:.0f}KB)")
            total += 1

    print(f"\nDone — {total} images generated, {skipped} skipped (up to date)")

if __name__ == "__main__":
    main()
