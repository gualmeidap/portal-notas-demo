"""Build the static site for GitHub Pages.

The output (`_site/`) is the same web UI, plus the Python package and the
pure-Python wheels it needs; `web/static/runtime.js` loads them into Pyodide
so the demo runs entirely in the visitor's browser. No server involved.

    python tools/build_site.py            # then: python -m http.server -d _site
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
# Pure-Python wheels, pinned to the versions in requirements.txt.
WHEELS = ["pypdf==5.4.0", "openpyxl==3.1.5", "et_xmlfile==2.0.0"]


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(ROOT / "web", OUT)
    (OUT / "static" / "mode.js").write_text('window.DEMO_RUNTIME = "browser";\n', encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    py = OUT / "py"
    files = []
    for src in sorted((ROOT / "app").glob("*.py")) + [ROOT / "config" / "vendor_rules.json"]:
        rel = src.relative_to(ROOT).as_posix()
        if rel == "app/main.py":
            continue  # server-only (FastAPI)
        (py / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, py / rel)
        files.append(rel)

    wheels_dir = py / "wheels"
    wheels_dir.mkdir(parents=True)
    subprocess.run([sys.executable, "-m", "pip", "download", "--quiet", "--no-deps", "--only-binary=:all:",
                    "--dest", str(wheels_dir), *WHEELS], check=True)
    wheels = sorted(p.name for p in wheels_dir.glob("*.whl"))
    if len(wheels) != len(WHEELS) or not all(w.endswith("-none-any.whl") for w in wheels):
        raise SystemExit(f"expected {len(WHEELS)} pure-Python wheels, got {wheels}")

    (py / "manifest.json").write_text(json.dumps({"files": files, "wheels": wheels}, indent=1), encoding="utf-8")
    print(f"built {OUT} ({len(files)} source files, wheels: {', '.join(wheels)})")


if __name__ == "__main__":
    main()
