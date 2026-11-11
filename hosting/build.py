"""Package the existing StudySpot UI for the hosted shared-data runtime."""

import json
from pathlib import Path
import re
import shutil
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app  # noqa: E402
from domain import CROWD, NOISE  # noqa: E402


def build() -> None:
    catalog = json.loads((ROOT / "campus-spaces.json").read_text(encoding="utf-8"))
    assets = {
        name: (ROOT / "static" / name).read_text(encoding="utf-8")
        for name in ("style.css", "live-observations.js")
    }
    assets["campus-search.js"] = (ROOT / "hosting" / "campus-search.js").read_text(encoding="utf-8")
    pages = {}
    with TemporaryDirectory() as temp:
        app = create_app({
            "DATASET": "campus",
            "DATABASE": str(Path(temp) / "build.sqlite3"),
            "SECRET_KEY": "build-only",
        })
        with app.test_client() as client:
            pages["/"] = client.get("/").get_data(as_text=True).replace(
                "</body>", '<script src="/static/campus-search.js" defer></script></body>',
            )
            for entry in catalog:
                path = f'/spaces/{entry["id"]}'
                page = client.get(path).get_data(as_text=True)
                page = re.sub(r'<input type="hidden" name="csrf_token" value="[^"]+">', '', page)
                fragment = client.get(path + "/live").get_data(as_text=True).strip()
                if page.count(fragment) != 1:
                    raise ValueError(f"Unable to locate observation panel in {path}")
                pages[path] = page.replace(fragment, "<!--OBSERVATIONS-->")

    output = ROOT / "dist"
    server = output / "server"
    server.mkdir(exist_ok=True, parents=True)
    data = {"pages": pages, "assets": assets, "crowd": CROWD, "noise": NOISE}
    worker = (ROOT / "hosting" / "worker.js").read_text(encoding="utf-8")
    (server / "index.js").write_text(
        f"const data = {json.dumps(data, ensure_ascii=True)};\n{worker}", encoding="utf-8",
    )
    manifest = output / ".openai"
    manifest.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / ".openai" / "hosting.json", manifest / "hosting.json")
    shutil.copytree(ROOT / "hosting" / "drizzle", manifest / "drizzle", dirs_exist_ok=True)


if __name__ == "__main__":
    build()
