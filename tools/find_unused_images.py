import re
from pathlib import Path

root = Path(__file__).resolve().parents[1]
img_root = root / "static" / "images"
img_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"}
text_exts = {
    ".html", ".jinja", ".j2", ".css", ".js", ".py", ".md", ".txt", ".json",
    ".yml", ".yaml", ".xml", ".ini", ".cfg", ".conf", ".env", ".ps1", ".sh",
}

all_images = sorted(
    p.relative_to(root).as_posix()
    for p in img_root.rglob("*")
    if p.is_file() and p.suffix.lower() in img_exts
)

refs = set()
pattern = re.compile(
    r"images/[A-Za-z0-9_./%\-]+\.(?:png|jpg|jpeg|webp|gif|svg|avif)",
    re.IGNORECASE,
)

for p in root.rglob("*"):
    if not p.is_file():
        continue
    rel = p.relative_to(root).as_posix()
    if rel.startswith(".git/") or rel.startswith(".venv/"):
        continue
    if p.suffix.lower() not in text_exts:
        continue
    try:
        data = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for match in pattern.findall(data):
        normalized = ("static/" + match.split("?", 1)[0].split("#", 1)[0]).replace("%20", " ")
        refs.add(normalized)

unused = [path for path in all_images if path not in refs]

print(f"ALL_IMAGES {len(all_images)}")
print(f"REFERENCED_IMAGES {len(refs)}")
print(f"UNUSED_IMAGES {len(unused)}")
for path in unused:
    print(path)
