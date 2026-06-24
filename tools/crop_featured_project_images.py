from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "static" / "images" / "projects"
FILES = [
    "stacknscroll-live.png",
    "passionateteachingjourney-live.png",
    "jamisonstamps-live.png",
    "passwordcheck-live.png",
    "hackernews-live.png",
    "dnd5etools-live.png",
]


def crop_and_normalize(path: Path) -> str:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    pix = img.load()

    min_x, min_y = w, h
    max_x, max_y = 0, 0
    found = False

    for y in range(h):
        for x in range(w):
            r, g, b = pix[x, y]
            if (r + g + b) > 42:
                found = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if not found:
        return f"skip:{path.name}:no non-dark pixels"

    pad = 14
    left = max(0, min_x - pad)
    top = max(0, min_y - pad)
    right = min(w, max_x + pad)
    bottom = min(h, max_y + pad)

    target_ratio = 16 / 9
    cw = right - left
    ch = bottom - top
    cur_ratio = cw / ch if ch else target_ratio

    if cur_ratio > target_ratio:
        new_h = int(cw / target_ratio)
        delta = new_h - ch
        top = max(0, top - delta // 2)
        bottom = min(h, bottom + (delta - delta // 2))
    else:
        new_w = int(ch * target_ratio)
        delta = new_w - cw
        left = max(0, left - delta // 2)
        right = min(w, right + (delta - delta // 2))

    cw = right - left
    ch = bottom - top
    cur_ratio = cw / ch if ch else target_ratio

    if abs(cur_ratio - target_ratio) > 0.02:
        if cur_ratio > target_ratio:
            new_w = int(ch * target_ratio)
            dx = (cw - new_w) // 2
            left += dx
            right = left + new_w
        else:
            new_h = int(cw / target_ratio)
            dy = (ch - new_h) // 2
            top += dy
            bottom = top + new_h

    out = img.crop((left, top, right, bottom)).resize((1280, 720), Image.Resampling.LANCZOS)
    out.save(path, optimize=True)
    return f"updated:{path.name}:{left},{top},{right},{bottom}"


def main() -> None:
    for name in FILES:
        path = ROOT / name
        if not path.exists():
            print(f"skip:{name}:missing")
            continue
        print(crop_and_normalize(path))


if __name__ == "__main__":
    main()
