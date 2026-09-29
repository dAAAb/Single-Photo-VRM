"""Local API for the viewer: photo → VRM jobs (stdlib only, binds to 127.0.0.1).

    .venv/bin/python server.py            # http://127.0.0.1:5189

POST /api/photo2vrm?gender=female|male   body = image bytes, header X-Filename
GET  /api/jobs/<id>                      status, log lines, output file names
GET  /api/files/<id>/<name>              result files (VRMs and QA images)
"""
import json
import re
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
UPLOADS = ROOT / "build" / "uploads"
MAX_BYTES = 30 * 1024 * 1024
jobs: dict[str, dict] = {}
run_lock = threading.Lock()  # one heavy job at a time
OUTPUTS = {  # name → path template ({id})
    "vrm0": "build/out/{id}.vrm0.vrm", "vrm1": "build/out/{id}.vrm1.vrm",
    "cutout": "build/fit/{id}/cutout.png", "detections": "build/fit/{id}/detections.png",
    "body_fit": "build/fit/{id}/body_fit.png", "face_fit": "build/fit/{id}/face_fit.png",
}


def run_job(job_id: str, image: Path, gender: str | None):
    job = jobs[job_id]
    with run_lock:
        job["status"] = "running"
        cmd = [sys.executable, str(HERE / "photo2vrm.py"), str(image)] + (["--gender", gender] if gender else [])
        p = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in p.stdout:
            if line.startswith("[photo2vrm]") or "Error" in line or "failed" in line:
                job["log"].append(line.replace("[photo2vrm] ", "").rstrip())
        p.wait()
        job["outputs"] = [k for k, t in OUTPUTS.items() if (ROOT / t.format(id=job_id)).exists()]
        job["status"] = "done" if p.returncode == 0 and "vrm0" in job["outputs"] else "error"


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path != "/api/photo2vrm":
            return self._json({"error": "not found"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        if not 0 < n <= MAX_BYTES:
            return self._json({"error": "empty or too large"}, 413)
        ext = Path(self.headers.get("X-Filename", "photo.png")).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".webp"):
            return self._json({"error": "unsupported image type"}, 415)
        gender = parse_qs(u.query).get("gender", [None])[0]
        gender = gender if gender in ("female", "male") else None
        job_id = uuid.uuid4().hex[:12]
        UPLOADS.mkdir(parents=True, exist_ok=True)
        img = UPLOADS / f"{job_id}{ext}"
        img.write_bytes(self.rfile.read(n))
        jobs[job_id] = {"status": "queued", "log": [], "outputs": []}
        threading.Thread(target=run_job, args=(job_id, img, gender), daemon=True).start()
        self._json({"id": job_id})

    def do_GET(self):
        m = re.fullmatch(r"/api/jobs/([0-9a-f]{12})", self.path)
        if m:
            return self._json(jobs.get(m[1]) or {"status": "unknown"}, 200 if m[1] in jobs else 404)
        m = re.fullmatch(r"/api/files/([0-9a-f]{12})/([a-z_0-9]+)", self.path)
        if m and m[2] in OUTPUTS:
            f = ROOT / OUTPUTS[m[2]].format(id=m[1])
            if f.exists():
                b = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "model/gltf-binary" if f.suffix == ".vrm" else "image/png")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers()
                return self.wfile.write(b)
        self._json({"error": "not found"}, 404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("photo2vrm API on http://127.0.0.1:5189")
    ThreadingHTTPServer(("127.0.0.1", 5189), Handler).serve_forever()
