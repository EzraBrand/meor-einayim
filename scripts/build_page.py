"""Build the side-by-side page for one chapter of Imrei Binah.

Usage: py -3.13 scripts/build_page.py 16
The title, subtitle, Hebrew title, printed pages and status come from data/chapters.json.
The script also rewrites the chapter table of docs/index.html from data/chapters.json.

Inputs (in data/):
  imrei-binah-NN.he.txt      one Hebrew segment on each line; a blank line between paragraphs
  imrei-binah-NN.en.txt      one English segment for each Hebrew segment, same blank lines
  imrei-binah-NN.notes.json  notes for the marks "⚠n"
Output: docs/imrei-binah-NN.html
The script stops if the Hebrew and English paragraph or segment counts do not agree.
"""
import html
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
SCAN = "https://archive.org/details/sefermeorenayim00ross"
REPO = "https://github.com/EzraBrand/meor-einayim"
# set the saved theme before the first paint (no flash)
FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif:ital,wght@0,400;0,600;1,400&family=Noto+Serif+Hebrew:wght@400;600&display=swap">\n'
THEME_JS = "<script>try{var t=localStorage.getItem('me-theme');if(t)document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>"


def site_header(active: str = "") -> str:
    links = [("index.html", "Chapters"), (REPO, "Code and data (GitHub)")]
    nav = " ".join(f'<a href="{h}"{' aria-current="page"' if h == active else ''}>{t}</a>' for h, t in links)
    nav += ('<label class="theme">Theme <select id="theme" aria-label="Colour theme">'
            '<option value="">Auto</option><option value="light">Light</option><option value="paper">Paper</option>'
            '<option value="dark">Dark</option></select></label>')
    return (f'<header class="site"><a class="brand" href="index.html">Azariah de\' Rossi, <i>Me\'or Einayim</i> '
            f'<span>· Hebrew and English</span></a><nav>{nav}</nav></header>')


def read_blocks(path: Path):
    blocks, cur = [], []
    for raw in path.read_text(encoding="utf-8").split("\n"):
        line = raw.strip()
        if line:
            cur.append(line)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


def fmt_en(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]", r'<span class="ref">[\1]</span>', text)
    text = re.sub(r"\s*⚠(\d+)", r'<a class="warn" href="#n\1" id="r\1" title="uncertain rendering">⚠\1</a>', text)
    return text


def main() -> None:
    num = int(sys.argv[1])
    meta = json.loads((ROOT / "data" / "chapters.json").read_text(encoding="utf-8"))[str(num)]
    title, subtitle = f"Imrei Binah, chapter {num}", meta["title_en"]
    stem = f"imrei-binah-{num:02d}"
    he = read_blocks(ROOT / "data" / f"{stem}.he.txt")
    en = read_blocks(ROOT / "data" / f"{stem}.en.txt")
    notes = json.loads((ROOT / "data" / f"{stem}.notes.json").read_text(encoding="utf-8"))

    bad = 0
    if len(he) != len(en):
        bad += 1
        print(f"paragraph count: Hebrew {len(he)}, English {len(en)}")
    for i, (h, e) in enumerate(zip(he, en)):
        if len(h) != len(e):
            bad += 1
            print(f"paragraph {i + 1}: Hebrew {len(h)} segments, English {len(e)}: {e[0][:50]}")
    marks = set(re.findall(r"⚠(\d+)", "\n".join(l for b in en for l in b)))
    if marks != set(notes):
        bad += 1
        print(f"note marks {sorted(marks, key=int)} do not agree with notes {sorted(notes, key=int)}")
    if bad:
        sys.exit("alignment errors; no page written")

    rows, seg = [], 0
    for pnum, (h, e) in enumerate(zip(he, en), 1):
        rows.append(f'<section class="blk prose" id="p{pnum}">')
        for j, (hl, el) in enumerate(zip(h, e)):
            seg += 1
            # a fixed link to the paragraph, as the Bochart reader: the ¶ at its end (chapter.html#p3)
            anchor = (f' <a class="anchor" href="#p{pnum}" title="Link to paragraph {pnum}" '
                      f'aria-label="Link to paragraph {pnum}">¶</a>') if j == len(h) - 1 else ""
            rows.append(
                f'<div class="row" id="s{seg}"><a class="ln" href="#s{seg}" title="Link to segment {seg}">{seg}</a>'
                f'<p class="he" lang="he" dir="rtl">{html.escape(hl, quote=False)}</p>'
                f'<p class="en">{fmt_en(el)}{anchor}</p></div>'
            )
        rows.append("</section>")

    note_rows = "\n".join(
        f'<li id="n{k}"><a href="#r{k}">⚠{k}</a> <span lang="he" dir="rtl" class="he-inline">{html.escape(v["he"], quote=False)}</span>'
        f' — {html.escape(v["note"], quote=False)}</li>'
        for k, v in notes.items()
    )

    done = sorted(int(k) for k in json.loads((ROOT / "data" / "chapters.json").read_text(encoding="utf-8"))
                  if (ROOT / "data" / f"imrei-binah-{int(k):02d}.en.txt").exists())
    i = done.index(num)
    prevnext = " · ".join(x for x in [
        f'<a href="imrei-binah-{done[i - 1]:02d}.html" rel="prev">← Chapter {done[i - 1]}</a>' if i > 0 else "",
        f'<a href="imrei-binah-{done[i + 1]:02d}.html" rel="next">Chapter {done[i + 1]} →</a>' if i + 1 < len(done) else ""] if x)
    thumbs = scan_thumbs(meta["leaves"])
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Azariah de' Rossi, Me'or Einayim</title>
{FONTS}<link rel="stylesheet" href="style.css?v={stamp('style.css')}">
{THEME_JS}
</head>
<body>
{site_header()}
<header class="chapter">
<p class="crumb"><a href="index.html">All chapters</a> · Imrei Binah {num} · {prevnext}</p>
<h1>{html.escape(title)}</h1>
<p class="sub">{html.escape(subtitle)} · <span lang="he" dir="rtl">{html.escape(meta["title_he"])}</span></p>
<details class="about"><summary>About this text</summary>
<p class="meta">{html.escape(meta["status"])}</p>
<p class="meta">{seg} segments in {len(he)} paragraphs. The division into segments and paragraphs is the translator's.
Text in <span class="ref">[gray brackets]</span> is added by the translator: references (not verified) and supplied words.
<a class="warn" href="#notes">⚠</a> marks an uncertain rendering.
Fixed links: <code>#p3</code> is a paragraph (the ¶ at its end), <code>#s12</code> a segment (its number).
Hebrew text: the <a href="{SCAN}">Vilna 1863–66 printing</a> (series Kiryat Sefer), pages {meta["pages"]}, {meta["source_note"]} The notes in Rashi type (additions by the author and by later scholars) are not included.</p>
</details>
<div class="scans" aria-label="Scans of the printed pages">{thumbs}</div>
</header>
<main>
{chr(10).join(rows)}
</main>
<footer id="notes">
<h2>Uncertain renderings</h2>
<ul class="notes">
{note_rows}
</ul>
<p>{prevnext} · <a href="index.html">All chapters</a> · <a href="{REPO}">Code and data (GitHub)</a></p>
</footer>
<script src="app.js?v={stamp('app.js')}"></script>
</body>
</html>
"""
    out = ROOT / "docs" / f"{stem}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}: {len(he)} paragraphs, {seg} segments, {len(notes)} notes")
    write_index()


def scan_thumbs(leaves) -> str:
    """Thumbnails of the chapter's scan pages, each linking to the page in the archive.org viewer.
    Made from the page images in source/pages/ and kept in docs/scans/ (archive.org's IIIF server
    is too slow on some pages to serve them live). Printed page = scan leaf - 24."""
    from PIL import Image
    out = []
    for leaf in range(leaves[0], leaves[1] + 1):
        t = ROOT / "docs" / "scans" / f"{leaf}.jpg"
        if not t.exists():
            src = ROOT / "source" / "pages" / f"{leaf}.jpg"
            if not src.exists():
                continue
            t.parent.mkdir(exist_ok=True)
            im = Image.open(src).convert("RGB")
            im.thumbnail((160, 400))
            im.save(t, quality=70, optimize=True)
        out.append(f'<a href="https://archive.org/details/sefermeorenayim00ross/page/n{leaf - 1}/mode/1up" target="_blank" '
                   f'rel="noopener" title="Scan of page {leaf - 24} (archive.org)"><img loading="lazy" src="scans/{leaf}.jpg" '
                   f'alt="Scan of page {leaf - 24}" width="80"><span>p. {leaf - 24}</span></a>')
    return "".join(out)


def stamp(name: str) -> str:
    """Short hash of a docs/ file, so a browser never pairs a new page with an old cached file."""
    import hashlib
    return hashlib.sha1((ROOT / "docs" / name).read_bytes()).hexdigest()[:8]


def write_index() -> None:
    chapters = json.loads((ROOT / "data" / "chapters.json").read_text(encoding="utf-8"))
    rows = "\n".join(
        f'<tr><td><a href="imrei-binah-{int(k):02d}.html">Imrei Binah {k}</a></td><td>{html.escape(v["title_en"])}</td></tr>'
        for k, v in sorted(chapters.items(), key=lambda kv: int(kv[0])) if (ROOT / "docs" / f"imrei-binah-{int(k):02d}.html").exists())
    idx = ROOT / "docs" / "index.html"
    t = idx.read_text(encoding="utf-8")
    t = re.sub(r"(<tr><th>Chapter</th>.*?</tr>\n).*?(</table>)", lambda m: m.group(1) + rows + "\n" + m.group(2), t, flags=re.S)
    # shared head and site header
    t = re.sub(r'<link rel="stylesheet" href="style\.css[^"]*">\n(<script>try.*?</script>\n)?',
               lambda m: f'<link rel="stylesheet" href="style.css?v={stamp("style.css")}">\n{THEME_JS}\n', t, count=1)
    if "fonts.googleapis.com" not in t:
        t = t.replace('<link rel="stylesheet" href="style.css', FONTS + '<link rel="stylesheet" href="style.css', 1)
    t = re.sub(r'<body>\n(<header class="site">.*?</header>\n)?', lambda m: "<body>\n" + site_header("index.html") + "\n", t, count=1)
    t = re.sub(r'(<script src="app\.js[^"]*"></script>\n)?</body>', lambda m: f'<script src="app.js?v={stamp("app.js")}"></script>\n</body>', t, count=1)
    idx.write_text(t, encoding="utf-8")


if __name__ == "__main__":
    main()
