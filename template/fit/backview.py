"""OPTIONAL: generate a back view of the person with FLUX.2-klein-4B (Apache-2.0) via mflux (MLX).

Opt-in only (photo2vrm --ai-backview / the viewer checkbox): the first run installs mflux into
template/.venv-mflux and downloads the model weights (~15 GB) from Hugging Face.
The result is segmented/centered like the input and used for back-facing texels.
"""
import subprocess
from pathlib import Path

import cv2
import numpy as np

from . import preprocess

HERE = Path(__file__).resolve().parents[1]
VENV = HERE / ".venv-mflux"
CLI = VENV / "bin" / "mflux-generate-flux2-edit"
MODEL = "flux2-klein-4b"
PROMPT = ("Show exactly the same person from directly behind (back view): same body, same clothes and "
          "colours, same hair, same shoes, same pose seen from the back, full body, centered, "
          "plain white background, even lighting.")


def ensure(log=print):
    if CLI.exists():
        return
    log("    installing mflux into template/.venv-mflux (one-time)")
    subprocess.run(["uv", "venv", "-q", "-p", "3.12", str(VENV)], check=True)
    subprocess.run(["uv", "pip", "install", "-q", "-p", str(VENV / "bin" / "python"), "mflux"], check=True)


def generate(work: Path, quantize: int = 8, seed: int = 7, log=print) -> Path:
    ensure(log)
    rgba = cv2.imread(str(work / "cutout.png"), cv2.IMREAD_UNCHANGED)
    a = rgba[..., 3:4].astype(np.float32) / 255
    front = (rgba[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    cv2.imwrite(str(work / "front_white.png"), front)
    raw = work / "back_raw.png"
    log(f"    FLUX.2-klein-4B back view (first use downloads ~15 GB of weights)")
    subprocess.run([str(CLI), "--model", MODEL, "--image-paths", str(work / "front_white.png"),
                    "--prompt", PROMPT, "--steps", "4", "--seed", str(seed), "--width", "1024",
                    "--height", "1024", "--quantize", str(quantize), "--output", str(raw)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    img = cv2.cvtColor(cv2.imread(str(raw)), cv2.COLOR_BGR2RGB)
    mask, _ = preprocess.segment(img, None)
    back, _ = preprocess.center(img, mask)
    out = work / "back_cutout.png"
    cv2.imwrite(str(out), cv2.cvtColor(back, cv2.COLOR_RGBA2BGRA))
    return out
