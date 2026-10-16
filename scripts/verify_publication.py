"""Scan working publication files and restored image metadata; never local .env.

This checks working files, not the Git index. Recheck the final export before publishing.
"""
import hashlib
import io
import json
import re
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
paths = set((ROOT / 'docs/PUBLICATION_FILES.txt').read_text().splitlines())
assets = {row['file']: row for row in json.loads((ROOT / 'docs/ASSET_INVENTORY.json').read_text())}
findings = []
excluded = {'.git', '.venv', 'venv', 'node_modules', '.validation', '__pycache__'}


def scan(name, content):
    patterns = {
        'provider credential': r'\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{20,}|(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}|AIza[A-Za-z0-9_-]{25,}|gh[pousr]_[A-Za-z0-9]{25,})\b',
        'private key': r'BEGIN [A-Z ]*PRIVATE KEY',
        'token': r'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b',
        'credential connection URL': r'\b(?:postgres(?:ql)?|mysql)://[^\s]+:[^\s]+@',
        'local filesystem path': r'(?:[A-Z]:[\\/](?:Users|Projects)[\\/]|/mnt/[a-z]/[U]sers/|/[U]sers/[^/\s]+/|/[h]ome/[^/\s]+/)',
        'institutional identifier': r'gitlab\.[\w.-]+|\bs\d{5,}\b',
    }
    for kind, pattern in patterns.items():
        if re.search(pattern, content, re.I):
            findings.append({'file': name, 'type': kind})
    for domain in re.findall(r'[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})', content, re.I):
        if not re.fullmatch(r'example\.(?:com|org|net|test)|localhost\.test', domain, re.I):
            findings.append({'file': name, 'type': 'non-example email'})


for name in sorted(paths):
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts:
        findings.append({'file': name, 'type': 'unsafe allowlist path'})
        continue
    path = ROOT / rel
    if not path.is_file():
        findings.append({'file': name, 'type': 'missing allowlisted file'})
        continue
    if any(part in excluded | {'media', 'staticfiles', '.idea', '.vscode'} for part in rel.parts) or path.suffix.lower() in {'.pdf', '.mp4', '.sqlite3', '.db', '.log', '.pyc', '.sql', '.dump'} or (path.name.startswith('.env') and path.name != '.env.example'):
        findings.append({'file': name, 'type': 'private/generated artifact'})
    data = path.read_bytes()
    if name in assets and hashlib.sha256(data).hexdigest() != assets[name]['sha256']:
        findings.append({'file': name, 'type': 'asset differs from reviewed hash'})
    if path.suffix.lower() in {'.png', '.jpg', '.jpeg'}:
        if name not in assets:
            findings.append({'file': name, 'type': 'image missing review inventory'})
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            values = list(im.info.values()) + list(im.getexif().values())
            text = '\n'.join(v.decode('utf-8', errors='replace') if isinstance(v, bytes) else str(v) for v in values)
            scan(name, text)
    else:
        scan(name, data.decode('utf-8-sig'))


def walk(directory):
    for path in directory.iterdir():
        if path.is_dir():
            if path.name not in excluded:
                yield from walk(path)
        elif path.name != '.env' and not (path.name.startswith('.env.') and path.name != '.env.example'):
            yield path.relative_to(ROOT).as_posix()


for name in set(walk(ROOT)) - paths:
    findings.append({'file': name, 'type': 'unexpected file outside publication allowlist'})

print(json.dumps({'result': 'FAIL' if findings else 'PASS', 'checked_files': len(paths),
    'reviewed_assets': len(assets), 'findings': findings,
    'scope': 'Working publication files; ignored .env, environments and validation output excluded. Git index and pixel privacy reviewed separately.'}, indent=2))
raise SystemExit(bool(findings))
