"""Build a versioned runnable ZIP without repository secrets or test databases."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(version: str, output_dir: Path) -> Path:
    if not re.fullmatch(r'[A-Za-z0-9._-]+', version):
        raise ValueError('Version must contain only letters, digits, dots, underscores or hyphens')
    names = ['app.py', 'domain.py', 'schema.sql', 'requirements-runtime-lock.txt']
    paths = [ROOT / name for name in names]
    paths.extend(sorted((ROOT / 'templates').glob('*.html')))
    paths.extend(sorted((ROOT / 'static').rglob('*')))
    paths = [p for p in paths if p.is_file()]
    for path in paths:
        if path.is_symlink():
            raise ValueError('Artifact inputs must be regular project files')
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f'StudySpot-{version}.zip'
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    readme = f"""# StudySpot runnable build {version}

Requires Python 3.12. Extract the ZIP first, then open a terminal in the extracted folder.

python -m pip install -r requirements-runtime-lock.txt
python app.py

Open http://127.0.0.1:5000 in a browser. Stop the app with Ctrl+C.
The app creates a local instance directory, sample database and session key on first run.
The eight locations are fictional samples. Reports are saved locally across restarts.
Accounts, favorites, maps and verified live campus data are not implemented.
This build does not include the development test suite; see the project repository for tests.

Repository: https://github.com/hailong0410/StudySpot
""".encode()
    hashes['README.md'] = hashlib.sha256(readme).hexdigest()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in paths:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr('README.md', readme)
        archive.writestr('BUILD_INFO.json', json.dumps({'version': version, 'files_sha256': hashes}, indent=2))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'dist')
    options = parser.parse_args()
    print(build(options.version, options.output_dir))
