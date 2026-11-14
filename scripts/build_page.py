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
    for h, e in zip(he, en):
        rows.append('<section class="blk prose">')
        for hl, el in zip(h, e):
            seg += 1
            rows.append(
                f'<div class="row" id="s{seg}"><a class="ln" href="#s{seg}">{seg}</a>'
                f'<p class="he" lang="he" dir="rtl">{html.escape(hl, quote=False)}</p>'
                f'<p class="en">{fmt_en(el)}</p></div>'
            )
        rows.append("</section>")

    note_rows = "\n".join(
        f'<li id="n{k}"><a href="#r{k}">⚠{k}</a> <span lang="he" dir="rtl" class="he-inline">{html.escape(v["he"], quote=False)}</span>'
        f' — {html.escape(v["note"], quote=False)}</li>'
        for k, v in notes.items()
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Azariah de' Rossi, Me'or Einayim</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header>
<p class="crumb"><a href="index.html">Azariah de' Rossi, <i>Me'or Einayim</i></a> · Imrei Binah</p>
<h1>{html.escape(title)}</h1>
<p class="sub">{html.escape(subtitle)} · <span lang="he" dir="rtl">{html.escape(meta["title_he"])}</span></p>
<p class="meta">{seg} segments in {len(he)} paragraphs. The division into segments and paragraphs is the translator's.
Text in <span class="ref">[gray brackets]</span> is added by the translator: references (not verified) and supplied words.
<a class="warn" href="#notes">⚠</a> marks an uncertain rendering.
Hebrew text: the <a href="{SCAN}">Vilna 1863–66 printing</a> (series Kiryat Sefer), pages {meta["pages"]}, {meta["source_note"]} The notes in Rashi type (additions by the author and by later scholars) are not included.</p>
</header>
<main>
{chr(10).join(rows)}
</main>
<footer id="notes">
<h2>Uncertain renderings</h2>
<ul class="notes">
{note_rows}
</ul>
<p><a href="index.html">Back to the project page</a></p>
</footer>
</body>
</html>
"""
    out = ROOT / "docs" / f"{stem}.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}: {len(he)} paragraphs, {seg} segments, {len(notes)} notes")
    write_index()


def write_index() -> None:
    chapters = json.loads((ROOT / "data" / "chapters.json").read_text(encoding="utf-8"))
    rows = "\n".join(
        f'<tr><td><a href="imrei-binah-{int(k):02d}.html">Imrei Binah {k}</a></td><td>{html.escape(v["title_en"])}</td>'
        f'<td>{html.escape(v["status"])}</td></tr>'
        for k, v in sorted(chapters.items(), key=lambda kv: int(kv[0])) if (ROOT / "docs" / f"imrei-binah-{int(k):02d}.html").exists())
    idx = ROOT / "docs" / "index.html"
    t = idx.read_text(encoding="utf-8")
    t = re.sub(r"(<tr><th>Chapter</th>.*?</tr>\n).*?(</table>)", lambda m: m.group(1) + rows + "\n" + m.group(2), t, flags=re.S)
    idx.write_text(t, encoding="utf-8")


if __name__ == "__main__":
    main()
