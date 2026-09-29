"""Contact sheet: input cutout | body fit overlay | VRM front | VRM side, one row per test image."""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
BLENDER = "/Applications/Blender.app/Contents/MacOS/Blender"
H = 300
rows = []
for blend in sorted((ROOT / "build" / "out").glob("*.blend")):
    name = blend.stem
    prev = ROOT / "build" / "out" / f"{name}_prev.png"
    subprocess.run([BLENDER, "-b", str(blend), "--python", str(ROOT / "template" / "render_preview.py"), "--", str(prev)],
                   env={"BLENDER_USER_RESOURCES": str(ROOT / "build" / "blender_user"), "PATH": "/usr/bin:/bin"},
                   capture_output=True)
    fit = ROOT / "build" / "fit" / name
    tiles = []
    for p in (fit / "cutout.png", fit / "body_fit.png", prev.with_name(f"{name}_prev_front.png"), prev.with_name(f"{name}_prev_side.png")):
        im = Image.open(p).convert("RGBA").resize((H, H))
        bg = Image.new("RGBA", (H, H), (235, 235, 238, 255))
        bg.alpha_composite(im)
        tiles.append(bg.convert("RGB"))
    row = Image.new("RGB", (H * 4, H), "white")
    for i, t in enumerate(tiles):
        row.paste(t, (i * H, 0))
    ImageDraw.Draw(row).text((6, 6), name, fill=(0, 0, 0))
    rows.append(row)
sheet = Image.new("RGB", (H * 4, H * len(rows)), "white")
for i, r in enumerate(rows):
    sheet.paste(r, (0, i * H))
out = ROOT / "build" / "qa_sheet.png"
sheet.save(out)
print("QA sheet →", out)
