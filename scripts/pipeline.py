"""Chapter pipeline for Imrei Binah (14-Nov-2026), chosen by scripts/model_eval.py.

  py -3.13 scripts/pipeline.py ocr 233 260 [--model M]   page images -> data/ocr/<model>/<leaf>.json
  py -3.13 scripts/pipeline.py chapters                  chapter headings found in the Opus OCR
  py -3.13 scripts/pipeline.py vote 17                    3-reader vote -> data/votes/17.json + crops of the places to check
  py -3.13 scripts/pipeline.py assemble 17                Opus text + data/fixes.json -> data/imrei-binah-17.he.txt
  py -3.13 scripts/pipeline.py translate 17               Opus @low -> .en.txt + .notes.json
  py -3.13 scripts/pipeline.py build 17                   docs/imrei-binah-17.html (via build_page.py) + index

Steps: OCR by three readers (Opus 5.5 @low main; Gemini 3.8 Flash and Gemini 3.1 Pro). Where one
other reader agrees with Opus, Opus stands; where both others agree against Opus, their reading is
taken; otherwise the place is checked on the scan (the reading goes in data/votes/<n>.json). On
chapter 16 this cut the Opus errors from 17 to 11 with 1 place to check. Errors that all readers
share are not found. Free corrections go in data/fixes.json (chapter -> list of [old, new]). Then code splits the text into segments,
Opus translates, and build_page.py writes the page.
Chapter metadata (title, leaves, Hebrew heading) is in data/chapters.json.
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_eval as ME  # noqa: E402  (call(), OCR_PROMPT, norm())

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OCR = DATA / "ocr"
PAGES = ROOT / "source" / "pages"
CROPS = ROOT / "logs" / "crops"
MAIN, SECOND, THIRD = "anthropic/claude-opus-5.5@low", "google/gemini-3.8-flash@low", "google/gemini-3.1-pro-preview@low"
TR_MODEL = "anthropic/claude-opus-5.5@low"
HEB_NUM = {"א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9, "י": 10, "כ": 20,
           "ל": 30, "מ": 40, "נ": 50, "ס": 60}


def image_file(leaf: int) -> Path:
    """archive.org's IIIF server times out on some pages; the /download/ page URL does not."""
    f = PAGES / f"{leaf}.jpg"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(f"https://archive.org/download/sefermeorenayim00ross/page/n{leaf - 1}_w1600.jpg", timeout=300)
        r.raise_for_status()
        f.write_bytes(r.content)
    return f


def data_url(leaf: int) -> str:
    import base64
    return "data:image/jpeg;base64," + base64.b64encode(image_file(leaf).read_bytes()).decode()


def mdir(spec: str) -> Path:
    return OCR / spec.replace("/", "_")


def cmd_ocr(a, b, specs):
    jobs = [(s, leaf) for s in specs for leaf in range(a, b + 1) if not (mdir(s) / f"{leaf}.json").exists()]
    for leaf in range(a, b + 1):
        image_file(leaf)
    total = [0.0]

    def one(job):
        spec, leaf = job
        model, _, effort = spec.partition("@")
        msg = [{"role": "user", "content": [{"type": "text", "text": ME.OCR_PROMPT},
                                            {"type": "image_url", "image_url": {"url": data_url(leaf)}}]}]
        res = ME.call(model, msg, effort or None)
        if "error" not in res:
            mdir(spec).mkdir(parents=True, exist_ok=True)
            (mdir(spec) / f"{leaf}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            total[0] += res["cost"]
        print(f"{spec} {leaf}: ${res.get('cost', 0):.4f} {res.get('error', '')[:200]}", flush=True)

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, jobs))
    print(f"done {len(jobs)} calls, ${total[0]:.3f}")


def batch_result(d: dict, seconds: float) -> dict:
    """A Batch API result in the same shape as model_eval.call()."""
    if "error" in d or "choices" not in d:
        return {"error": str(d.get("error", d))[:500]}
    u = d.get("usage", {})
    ch = d["choices"][0]
    if ch.get("finish_reason") not in ("stop", "end_turn"):
        return {"error": f"finish_reason={ch.get('finish_reason')}, cost ${u.get('cost', 0):.4f}"}
    return {"text": ch["message"].get("content") or "", "provider": d.get("provider"), "engine": "openrouter batch",
            "in": u.get("prompt_tokens"), "out": u.get("completion_tokens"),
            "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "cost": u.get("cost", 0), "seconds": round(seconds, 1)}


def cmd_ocr_batch(ranges, specs):
    """OCR through the OpenRouter Batch API (half price). The page images go to the public crops repo
    (crophost.py, shared with Bochart; `py -3.13 scripts/crophost.py clean` empties it after the run),
    because a chat/completions batch takes only image URLs. The readers run as three batches at once."""
    import io
    import time
    from concurrent.futures import ThreadPoolExecutor as TPE
    from PIL import Image
    os.environ.setdefault("OPENROUTER_KEY_FILE", str(ME.KEY))
    import crophost
    import orbatch
    leaves = [l for a, b in ranges for l in range(a, b + 1)]
    todo = {s: [l for l in leaves if not (mdir(s) / f"{l}.json").exists()] for s in specs}
    need = sorted({l for ls in todo.values() for l in ls})
    if not need:
        print("all pages done already")
        return
    imgs = {}
    for leaf in need:
        im = Image.open(image_file(leaf)).convert("RGB")
        if im.width > 1600:
            im = im.resize((1600, round(im.height * 1600 / im.width)))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        imgs[f"meor/{leaf}.jpg"] = buf.getvalue()
    # OCR_BATCH_STAMP=2026-11-14_1651 resumes the batches of a stopped run (state files in logs/):
    # nothing is published or submitted again.
    stamp = os.environ.get("OCR_BATCH_STAMP") or time.strftime("%Y-%m-%d_%H%M")
    urls = {k: "" for k in imgs} if os.environ.get("OCR_BATCH_STAMP") else crophost.publish(imgs)

    def one(spec):
        if not todo[spec]:
            return
        model, _, effort = spec.partition("@")
        bodies = {}
        for leaf in todo[spec]:
            b = {"max_tokens": 6000, "temperature": 0, "usage": {"include": True},
                 "messages": [{"role": "user", "content": [
                     {"type": "text", "text": ME.OCR_PROMPT},
                     {"type": "image_url", "image_url": {"url": urls[f"meor/{leaf}.jpg"]}}]}]}
            if effort:
                b["reasoning"] = {"effort": effort}
            bodies[f"L{leaf}"] = b
        t = time.monotonic()
        res = orbatch.run_batch(model, bodies, log_name=f"ocr_{spec.replace('/', '_').replace('@', '_')}_{stamp}")
        cost, ok = 0.0, 0
        for leaf in todo[spec]:
            r = batch_result(res.get(f"L{leaf}", {"error": "no result"}), time.monotonic() - t)
            if "error" in r or len(r["text"]) < 300:
                print(f"{spec} {leaf}: FAILED {r.get('error', 'short text')}", flush=True)
                continue
            mdir(spec).mkdir(parents=True, exist_ok=True)
            (mdir(spec) / f"{leaf}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
            cost += r["cost"]
            ok += 1
        print(f"{spec}: {ok}/{len(todo[spec])} pages, ${cost:.3f}", flush=True)

    with TPE(len(specs)) as ex:
        list(ex.map(one, specs))


def page_text(spec: str, leaf: int) -> str:
    return json.loads((mdir(spec) / f"{leaf}.json").read_text(encoding="utf-8"))["text"]


def heb_value(s: str) -> int:
    return sum(HEB_NUM.get(c, 0) for c in s)


HEAD = re.compile(r"(?m)^\s*פרק\s+([א-ס]{1,2})\b")


def cmd_chapters():
    leaves = sorted(int(f.stem) for f in mdir(MAIN).glob("*.json"))
    for leaf in leaves:
        for m in HEAD.finditer(page_text(MAIN, leaf)):
            print(f"leaf {leaf}: chapter {heb_value(m.group(1))} ({m.group(0).strip()})")
            # the title (small type) is the line before the heading; Opus sometimes leaves it out
            for spec in (MAIN, SECOND, THIRD):
                f = mdir(spec) / f"{leaf}.json"
                if not f.exists():
                    continue
                t = page_text(spec, leaf)
                hs = [h for h in HEAD.finditer(t) if heb_value(h.group(1)) == heb_value(m.group(1))]
                if hs:
                    before = t[:hs[0].start()].rstrip().split("\n")
                    print(f"    {spec.split('/')[1][:18]:18} title? {before[-1][-160:] if before else ''}")


def chapter_meta(n: int) -> dict:
    return json.loads((DATA / "chapters.json").read_text(encoding="utf-8"))[str(n)]


def joined(spec: str, leaves) -> str:
    """Pages joined; a catchword (the last line of a page, 1-2 words, that the next page begins
    with) is dropped."""
    pages = [page_text(spec, leaf).strip() for leaf in leaves]
    for i in range(len(pages) - 1):
        lines = pages[i].split("\n")
        last = lines[-1].strip()
        if 0 < len(last.split()) <= 2 and pages[i + 1].lstrip().startswith(last.rstrip(".,")):
            pages[i] = "\n".join(lines[:-1])
    return "\n".join(pages)


def chapter_text(spec: str, n: int) -> str:
    """The chapter's text from one reader: from the heading 'פרק n' (and the title line before it)
    to the title line of the next chapter."""
    meta = chapter_meta(n)
    text = joined(spec, range(meta["leaves"][0], meta["leaves"][1] + 1))
    heads = [m for m in HEAD.finditer(text)]

    def after_title(k: int):
        """A reader may misread the chapter number (Flash: כז for כט): take the first heading
        after the chapter's title."""
        km = json.loads((DATA / "chapters.json").read_text(encoding="utf-8")).get(str(k))
        if not km:
            return None
        # up to 10 words of the title (chapters 37-39 share their first 6), with any spacing or
        # punctuation between them (the readers differ there)
        words = [re.escape(w.strip(".,:;•")) for w in km["title_he"].split()[:10] if w.strip(".,:;•")]
        if not words:  # chapter 1 has no title in the print: by number
            return None
        t = re.search(r"[\s.,:;•]+".join(words), text)
        return next((m for m in heads if t and m.start() > t.start()), None)

    # a chapter starts at the heading after its title; a reader can misread the number (Gemini Pro:
    # לז for לו, Flash: כז for כט). Without the title (Opus sometimes leaves it out): by number.
    start = after_title(n) or next((m for m in heads if heb_value(m.group(1)) == n), None)
    if start is None:
        sys.exit(f"{spec}: no heading for chapter {n}")
    nxt = [m for m in [after_title(n + 1)] if m and m.start() > start.start()] or \
        [m for m in heads if heb_value(m.group(1)) == n + 1 and m.start() > start.start()]
    body = text[start.end():nxt[0].start() if nxt else len(text)].strip()
    if nxt:  # drop the next chapter's title (some readers leave it out)
        nmeta = json.loads((DATA / "chapters.json").read_text(encoding="utf-8"))[str(n + 1)]
        key = nmeta.get("strip_from") or " ".join(nmeta["title_he"].split()[:3])  # strip_from: a section heading
        i = body.rfind(key)
        if i >= 0 and len(body) - i < len(nmeta["title_he"]) + 200:  # ch. 35's title has 450 letters
            body = body[:i]
    return body.strip()


def cmd_vote(n: int):
    """Vote of the three readers; crops of the places to check go to logs/crops/<n>/.
    Writes data/votes/<n>.json. For each 'check' item, write the reading from the scan into
    "reading" (or set "decision" to "main"), then run assemble."""
    from PIL import Image
    meta = chapter_meta(n)
    out_json = DATA / "votes" / f"{n}.json"
    if out_json.exists():
        sys.exit(f"{out_json} exists (it may hold scan decisions); delete it to vote again")
    main = chapter_text(MAIN, n)
    items = vote(main, [chapter_text(SECOND, n), chapter_text(THIRD, n)])
    leaves = range(meta["leaves"][0], meta["leaves"][1] + 1)
    pos = []
    for leaf in leaves:
        w = ME.norm(page_text(MAIN, leaf)).split()
        pos += [(leaf, i / max(1, len(w))) for i in range(len(w))]
    full = ME.norm(joined(MAIN, leaves)).split()
    a = ME.norm(main).split()
    off = next(i for i in range(len(full)) if full[i:i + 6] == a[:6])
    crops = CROPS / str(n)
    crops.mkdir(parents=True, exist_ok=True)
    starts = set()  # main-word indices that begin a page (relative to the chapter)
    acc = 0
    for leaf in leaves:
        starts.add(acc - off)
        acc += len(ME.norm(page_text(MAIN, leaf)).split())
    for k, it in enumerate(items):
        it["k"] = k
        leaf, frac = pos[min(off + it["i1"], len(pos) - 1)]
        it["leaf"] = leaf
        if it["decision"] != "main" and it["i1"] == it["i2"] and it["i1"] in starts:
            it["decision"], it["reading"], it["why"] = "main", "", "catchword"  # the others kept the catchword
        if it["decision"] == "check":
            im = Image.open(image_file(leaf))
            y, h = int(im.height * (0.05 + frac * 0.9)), int(im.height * 0.08)
            im.crop((int(im.width * 0.06), max(0, y - h), im.width, min(im.height, y + h))).save(crops / f"{k:03d}_{leaf}.jpg", quality=85)
    out_json.parent.mkdir(exist_ok=True)
    out_json.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(Counter(i["decision"] for i in items))
    for it in items:
        if it["decision"] != "main":
            print(f"{it['k']:3} {it['leaf']} {it['decision']:6} opus [{it['main']}] others {it['others']}   {it['context']}")


def tokens(text: str):
    """Raw whitespace tokens and, for each normalized word, the index of its raw token."""
    raw = text.split()
    words, where = [], []
    for i, t in enumerate(raw):
        for w in ME.norm(t).split():
            words.append(w)
            where.append(i)
    return raw, words, where


def vote(main: str, others: list[str]) -> list[dict]:
    """Places where a second reader differs from the main reader (spans of main words).
    decision: 'main' if any other reader agrees with main there; 'others' if all other readers
    agree with one another against main; else 'check'."""
    import difflib
    _, a, _ = tokens(main)
    spans = {}
    for r, text in enumerate(others):
        b = ME.norm(text).split()
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op != "equal":
                spans.setdefault((i1, i2), {})[r] = " ".join(b[j1:j2])
    items = []
    for (i1, i2), got in sorted(spans.items()):
        readings = [got.get(r) for r in range(len(others))]
        # a reader with no difference at exactly this span agrees with main, unless it differs on an
        # overlapping span (then its reading is unknown here)
        overlap = {r for (k1, k2), g in spans.items() if (k1, k2) != (i1, i2) and k1 < max(i2, i1 + 1) and k2 > i1 - (i1 == i2) for r in g}
        agrees_main = [r for r in range(len(others)) if readings[r] is None and r not in overlap]
        if agrees_main:
            decision, reading = "main", " ".join(a[i1:i2])
        elif i1 == i2 and i1 > 0 and all(x and x.split()[0] == a[i1 - 1] for x in readings if x):
            # both Geminis repeat the word before (קמ"ג קמ"ג, הים הים: 12 times in tranches 2-3, never right)
            decision, reading = "main", ""
        elif all(x is not None for x in readings) and len(set(readings)) == 1:
            decision, reading = "others", readings[0]
        else:
            decision, reading = "check", None
        items.append({"i1": i1, "i2": i2, "main": " ".join(a[i1:i2]), "others": readings,
                      "context": " ".join(a[max(0, i1 - 4):i1]) + " [" + " ".join(a[i1:i2]) + "] " + " ".join(a[i2:i2 + 4]),
                      "decision": decision, "reading": reading})
    return items


def apply_votes(main: str, items: list[dict]) -> str:
    """Replace the voted spans in the raw main text, from the end backwards."""
    raw, words, where = tokens(main)
    for it in sorted(items, key=lambda x: -x["i1"]):
        if it["decision"] == "main" or it["reading"] is None:
            continue
        if it["i1"] < it["i2"]:
            t1, t2 = where[it["i1"]], where[it["i2"] - 1]
            tail = raw[t2][len(raw[t2].rstrip(",;:.)")):] if raw[t2].rstrip(",;:.)") else ""
            raw[t1:t2 + 1] = (it["reading"] + tail).split() if it["reading"] else ([tail] if tail else [])
        else:  # insertion before word i1
            t = where[it["i1"]] if it["i1"] < len(where) else len(raw)
            raw[t:t] = it["reading"].split()
    return " ".join(raw)


def segment(text: str) -> list[list[str]]:
    """Split into segments at , ; : . (at least 8 words each) and into paragraphs of about 10
    segments, closed at a full stop or colon."""
    text = re.sub(r"\s+", " ", text).strip()
    pieces = re.findall(r"[^,;:.]+[,;:.]?", text)
    segs, cur = [], ""
    for p in pieces:
        cur = (cur + " " + p.strip()).strip() if cur else p.strip()
        if len(cur.split()) >= 8 and cur[-1:] in ",;:.":
            segs.append(cur)
            cur = ""
    if cur:
        if segs and len(cur.split()) < 5:
            segs[-1] += " " + cur
        else:
            segs.append(cur)
    paras, para = [], []
    for s in segs:
        para.append(s)
        if len(para) >= 8 and s[-1] in ".:":
            paras.append(para)
            para = []
    if para:
        paras.append(para)
    return paras


def cmd_assemble(n: int):
    items = json.loads((DATA / "votes" / f"{n}.json").read_text(encoding="utf-8"))
    todo = [it["k"] for it in items if it["decision"] == "check" and it["reading"] is None]
    if todo:
        sys.exit(f"items not decided on the scan: {todo}")
    text = apply_votes(chapter_text(MAIN, n), items)
    fixes = json.loads((DATA / "fixes.json").read_text(encoding="utf-8")).get(str(n), [])
    for old, new in fixes:  # free corrections after the vote, as [old, new] strings
        c = text.count(old)
        if c != 1:
            sys.exit(f"fix {old!r} -> {new!r}: found {c} times (must be 1)")
        text = text.replace(old, new)
    text = re.sub(r"\s*\*+\s*\)|\s*\*+", "", text)  # the author's note marks: the notes are not included
    paras = segment(text)
    out = DATA / f"imrei-binah-{n:02d}.he.txt"
    out.write_text("\n\n".join("\n".join(p) for p in paras) + "\n", encoding="utf-8")
    changed = sum(1 for it in items if it["decision"] != "main")
    print(f"wrote {out}: {len(paras)} paragraphs, {sum(map(len, paras))} segments, {changed} voted changes, {len(fixes)} fixes")


TR_PROMPT = """\
Below is chapter {n} of Imrei Binah, the third part of Azariah de' Rossi's Me'or Einayim (Mantua \
1573-75), a critical study of rabbinic chronology and aggadah. The chapter's title: {title_he}. \
The Hebrew is the Vilna 1863-66 printing, given as numbered segments.

Translate it into English for scholars of Jewish history and rabbinic literature.
Rules:
- Return a JSON object {{"en": [...], "notes": [...]}}. "en" has exactly one English string for each \
Hebrew segment, in the same order ({count} segments). Do not merge or split segments.
- Accurate, clear scholarly English; not archaic, not a paraphrase. Keep the author's hedges and irony.
- Biblical and rabbinic quotations are translated, inside quotation marks. Add the reference in \
[square brackets] only when you are sure of it ("[Ps 147:5]", "[b. Gittin 56b]", "[Bereshit Rabbah 10]").
- Keep the author's own references as he gives them; do not change a number to a modern edition. \
If you think a number is wrong, keep it and say so in a note.
- Names of works in their usual English scholarly form (Bereshit Rabbah, Pirkei de-Rabbi Eliezer).
- Words you add for sense go in [square brackets].
- European authors and works written in Hebrew letters: give the usual English or Latin form ONLY \
if you are sure of the identification; otherwise transliterate the Hebrew and add a note. Never guess \
a name.
- Do not call a spelling a misprint and do not emend it: the author's Hebrew has variant forms of \
its own (for example רתוי for ראוי). Translate the sense; add a note only when the meaning itself is unclear.
- Where the reading or the sense is uncertain, end the segment with "⚠" and add a note: \
{{"seg": <segment number>, "he": "<the Hebrew words concerned>", "note": "<one or two sentences>"}}.
- The chapter title above is not one of the segments.

Segments:
{segs}"""


PART_MAX = 260  # segments in one call: chapter 40 (630 segments) hit the 65,536 output-token limit


def translate_call(n: int, he: list[str], raw: Path) -> tuple[list, list, float]:
    """One model call for the segments `he` (the raw answer is cached in `raw`): English, notes, cost."""
    meta = chapter_meta(n)
    prompt = TR_PROMPT.format(n=n, title_he=meta["title_he"], count=len(he),
                              segs="\n".join(f"{i + 1}. {s}" for i, s in enumerate(he)))
    if raw.exists():
        res = json.loads(raw.read_text(encoding="utf-8"))
    else:
        model, _, effort = TR_MODEL.partition("@")
        res = ME.call(model, [{"role": "user", "content": prompt}], effort or None, json_mode=True)
        if "error" in res:
            sys.exit(res["error"])
        raw.parent.mkdir(exist_ok=True)
        raw.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    body = re.sub(r"^```(json)?|```$", "", res["text"].strip()).strip()
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        # Opus sometimes leaves quotation marks inside a string unescaped (ch. 23: ("Elilim")).
        # The strings are one to a line: escape every quote between the line's first and last quote.
        def fix(line: str) -> str:
            # a note on one line with unescaped gershayim in "he" (ch. 40: "דכ"א תשצ"ט")
            nm = re.match(r'^(\s*\{"seg":\s*\d+,\s*"he":\s*")(.*)(",\s*"note":\s*")(.*)("\s*\}\s*,?)$', line)
            if nm:
                esc = lambda x: re.sub(r'(?<!\\)"', r'\\"', x)
                return nm.group(1) + esc(nm.group(2)) + nm.group(3) + esc(nm.group(4)) + nm.group(5)
            m = re.match(r'^(\s*(?:"[a-z]+":\s*)?")(.*)("\s*[,\]}]?\s*,?)$', line)
            if not m or line.strip().startswith(("{", "}", "[", "]")):
                return line
            return m.group(1) + re.sub(r'(?<!\\)"', r'\\"', m.group(2)) + m.group(3)
        d = json.loads("\n".join(fix(l) for l in body.split("\n")))
        print(f"chapter {n}: repaired unescaped quotes in the JSON")
    en, notes = d["en"], d.get("notes", [])
    for x in notes:  # ch. 37: a note came without its Hebrew words
        x.setdefault("he", ""); x.setdefault("note", "")
    if len(en) != len(he):
        sys.exit(f"{len(en)} English segments for {len(he)} Hebrew; see {raw}")
    return en, notes, res["cost"]


def cmd_translate(n: int):
    blocks = [[l.strip() for l in b.split("\n") if l.strip()]
              for b in (DATA / f"imrei-binah-{n:02d}.he.txt").read_text(encoding="utf-8").strip().split("\n\n")]
    he = [l for b in blocks for l in b]
    raw = DATA / "translate" / f"translate_{n:02d}.json"
    whole = raw.exists() and json.loads(raw.read_text(encoding="utf-8")).get("out", 0) < 60000  # not cut off
    if len(he) <= PART_MAX + 100 or whole:
        en, notes, cost = translate_call(n, he, raw)
    else:  # parts of whole paragraphs, of about equal size
        k = -(-len(he) // PART_MAX)
        size, parts, cur = len(he) / k, [], []
        for b in blocks:
            if cur and len(parts) < k - 1 and len(cur) + len(b) / 2 > size:
                parts.append(cur)
                cur = []
            cur = cur + b
        parts.append(cur)
        en, notes, cost = [], [], 0.0
        for i, part in enumerate(parts):
            e, nt, c = translate_call(n, part, DATA / "translate" / f"translate_{n:02d}.part{i + 1}of{len(parts)}.json")
            for x in nt:
                x["seg"] = int(x["seg"]) + len(en)
            en, notes, cost = en + e, notes + nt, cost + c
        print(f"chapter {n}: translated in {len(parts)} parts")
    res = {"cost": cost}
    # English corrections after review: data/en_fixes.json {chapter: [[old, new], ...]}, applied to the
    # segments and the notes; each old string must occur exactly once
    en = [re.sub(r"\*+\)?", "", e).replace("  ", " ").strip() for e in en]  # note marks, *emphasis*
    fixes = json.loads((DATA / "en_fixes.json").read_text(encoding="utf-8")).get(str(n), [])
    for old, new in fixes:
        hits = [i for i, e in enumerate(en) if old in e] + [f"note{j}" for j, x in enumerate(notes) if old in x["note"] or old in x["he"]]
        if len(hits) != 1:
            sys.exit(f"en fix {old!r}: found in {hits} (must be exactly 1)")
        en = [e.replace(old, new) for e in en]
        for x in notes:
            x["note"], x["he"] = x["note"].replace(old, new), x["he"].replace(old, new)
    notes = [x for x in notes if x["note"] != "DROP"]
    # number the ⚠ marks in order and attach the notes
    by_seg = {}
    for x in notes:
        by_seg.setdefault(int(x["seg"]), []).append(x)
    out_notes, k = {}, 0
    for i in range(len(en)):
        en[i] = re.sub(r"\s+([,.;:)\]])", r"\1", re.sub(r"\s*⚠\s*", " ", en[i])).replace("  ", " ").strip()  # no "478 ,"
        for x in by_seg.get(i + 1, []):
            k += 1
            out_notes[str(k)] = {"he": x["he"], "note": x["note"]}
            en[i] += f" ⚠{k}"
    # write English with the Hebrew paragraph breaks
    blocks = (DATA / f"imrei-binah-{n:02d}.he.txt").read_text(encoding="utf-8").strip().split("\n\n")
    lines, j = [], 0
    for b in blocks:
        cnt = len([l for l in b.split("\n") if l.strip()])
        lines.append("\n".join(en[j:j + cnt]))
        j += cnt
    (DATA / f"imrei-binah-{n:02d}.en.txt").write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    (DATA / f"imrei-binah-{n:02d}.notes.json").write_text(json.dumps(out_notes, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"chapter {n}: {len(en)} segments, {k} notes, ${res['cost']:.3f}")


def tr_prompt(n: int) -> tuple[str, int]:
    he = [l.strip() for l in (DATA / f"imrei-binah-{n:02d}.he.txt").read_text(encoding="utf-8").split("\n") if l.strip()]
    meta = chapter_meta(n)
    return TR_PROMPT.format(n=n, title_he=meta["title_he"], count=len(he),
                            segs="\n".join(f"{i + 1}. {s}" for i, s in enumerate(he))), len(he)


def cmd_translate_batch(chapters: list[int]):
    """Translate several chapters in one Opus batch (half price); the raw answers are cached in
    data/translate/ exactly as the direct calls, so `translate N` then builds the files."""
    import time
    os.environ.setdefault("OPENROUTER_KEY_FILE", str(ME.KEY))
    import orbatch
    todo = [n for n in chapters if not (DATA / "translate" / f"translate_{n:02d}.json").exists()]
    if not todo:
        print("all chapters translated already")
    else:
        model, _, effort = TR_MODEL.partition("@")
        bodies = {}
        for n in todo:
            prompt, count = tr_prompt(n)
            b = {"max_tokens": min(64000, 4000 + 150 * count), "temperature": 0, "usage": {"include": True},
                 "response_format": {"type": "json_object"}, "messages": [{"role": "user", "content": prompt}]}
            if effort:
                b["reasoning"] = {"effort": effort}
            bodies[f"ch{n}"] = b
        t = time.monotonic()
        res = orbatch.run_batch(model, bodies, log_name=f"translate_{todo[0]}-{todo[-1]}_{time.strftime('%Y-%m-%d_%H%M')}")
        for n in todo:
            r = batch_result(res.get(f"ch{n}", {"error": "no result"}), time.monotonic() - t)
            if "error" in r:
                print(f"chapter {n}: FAILED {r['error']}", flush=True)
                continue
            (DATA / "translate").mkdir(exist_ok=True)
            (DATA / "translate" / f"translate_{n:02d}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    for n in chapters:
        if (DATA / "translate" / f"translate_{n:02d}.json").exists():
            try:
                cmd_translate(n)
            except SystemExit as e:
                print(f"chapter {n}: {e}", flush=True)


def cmd_build(n: int):
    meta = chapter_meta(n)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_page.py"), str(n)], check=True)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "ocr":
        specs = [args[args.index("--model") + 1]] if "--model" in args else [MAIN, SECOND]
        cmd_ocr(int(args[0]), int(args[1]), specs)
    elif cmd == "ocr-batch":  # ocr-batch 361 505 80 226: all three readers, as batches
        nums = [int(x) for x in args]
        cmd_ocr_batch(list(zip(nums[::2], nums[1::2])), [MAIN, SECOND, THIRD])
    elif cmd == "translate-batch":  # translate-batch 40 41 42 ...
        cmd_translate_batch([int(x) for x in args])
    elif cmd == "chapters":
        cmd_chapters()
    else:
        {"vote": cmd_vote, "assemble": cmd_assemble, "translate": cmd_translate, "build": cmd_build}[cmd](int(args[0]))
