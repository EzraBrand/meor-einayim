"""Cost and quality test of OpenRouter models on Imrei Binah chapter 16 (14-Nov-2026).

Two tasks, each checked against the corrected chapter 16 in data/:
  ocr        page image (Vilna pp. 203-209 = scan leaves 227-233) -> Hebrew main text
  translate  the corrected Hebrew segments -> English, one line for each segment

Usage:
  py -3.13 scripts/model_eval.py ocr google/gemini-3.8-flash anthropic/claude-opus-5.5 ...
  py -3.13 scripts/model_eval.py translate anthropic/claude-sonnet-5.5 ...
  py -3.13 scripts/model_eval.py score
Results: eval/<task>/<model>/<item>.json (a finished item is not sent again).
The key file is OPENROUTER_KEY_FILE (default: the Bochart key).
"""
import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "eval"
KEY = Path(os.environ.get("OPENROUTER_KEY_FILE", ROOT.parent / "bochart-hierozoicon.txt"))
LEAVES = range(227, 234)  # printed pages 203-209
IMG = "https://iiif.archive.org/iiif/sefermeorenayim00ross${leaf}/full/1600,/0/default.jpg"

OCR_PROMPT = """\
This is one page of Azariah de' Rossi, Me'or Einayim (Vilna 1863-66 printing), in Hebrew. The page has \
a running head, the main text in square Hebrew type, and notes in a smaller Rashi-type column.

Transcribe ONLY the main text in square type, in reading order, exactly as printed: keep the spelling, \
abbreviations with their gershayim ("), punctuation, brackets, and chapter headings (for example \
"פרק טז"). Join words that are hyphenated across lines. Do not transcribe the running head, the page \
number, catchwords at the foot of the page, or the Rashi-type notes. Do not correct, modernize, or add \
vowel points. Output plain text only, one printed paragraph per line, nothing else."""

TR_PROMPT = """\
Below is chapter 16 of Imrei Binah, the third part of Azariah de' Rossi's Me'or Einayim (Mantua 1573-75): \
a critical study of the rabbinic story of the gnat that entered the nostril of Titus. The Hebrew is given \
as numbered segments.

Translate it into English for scholars of Jewish history and rabbinic literature.
Rules:
- Return a JSON object {"en": [...]} with exactly one English string for each Hebrew segment, in the same \
order ({n} segments). Do not merge or split segments.
- Accurate, clear scholarly English; not archaic, not a paraphrase. Keep the author's hedges and irony.
- Rabbinic and biblical quotations are translated, inside quotation marks.
- Names of works in their usual English scholarly form (Bereshit Rabbah, Pirkei de-Rabbi Eliezer, b. Gittin).
- Words you add for sense, and references you supply, go in [square brackets].
- European names written in Hebrew letters: give the usual English or Latin form if you know it; else \
transliterate.
- Where the reading or sense is uncertain, add "⚠" at the end of the segment.

Segments:
{segs}"""


def call(model: str, messages: list, effort: str | None, json_mode: bool = False) -> dict:
    body = {"model": model, "messages": messages, "usage": {"include": True}, "temperature": 0}
    if effort:
        body["reasoning"] = {"effort": effort}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    t = time.monotonic()
    for attempt in range(3):
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers={"Authorization": "Bearer " + KEY.read_text(encoding="utf-8").strip()},
                          json=body, timeout=900)
        d = r.json()
        if r.ok and "choices" in d:
            break
        print(f"  {model}: HTTP {r.status_code} {str(d)[:300]}", flush=True)
        if r.status_code in (400, 401, 402, 403) and "fetching image" not in str(d):  # IIIF is slow on a cold image
            return {"error": str(d)}
        time.sleep(10)
    else:
        return {"error": str(d)}
    u = d.get("usage", {})
    return {"text": d["choices"][0]["message"].get("content") or "", "provider": d.get("provider"),
            "in": u.get("prompt_tokens"), "out": u.get("completion_tokens"),
            "reasoning": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "cost": u.get("cost", 0), "seconds": round(time.monotonic() - t, 1)}


def model_spec(spec: str):
    """'anthropic/claude-opus-5.5@low' -> (model, effort, dir name)."""
    model, _, effort = spec.partition("@")
    return model, effort or None, spec.replace("/", "_")


def image(leaf: int) -> str:
    """The page as a data URL; cached in source/pages/ (IIIF renders some pages too slowly for the providers)."""
    import base64
    f = ROOT / "source" / "pages" / f"{leaf}.jpg"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(IMG.format(leaf=leaf), timeout=300)
        r.raise_for_status()
        f.write_bytes(r.content)
    return "data:image/jpeg;base64," + base64.b64encode(f.read_bytes()).decode()


def run_ocr(specs):
    jobs = []
    for spec in specs:
        model, effort, name = model_spec(spec)
        for leaf in LEAVES:
            f = OUT / "ocr" / name / f"{leaf}.json"
            if not f.exists():
                jobs.append((model, effort, f, leaf))

    def one(job):
        model, effort, f, leaf = job
        msg = [{"role": "user", "content": [{"type": "text", "text": OCR_PROMPT},
                                            {"type": "image_url", "image_url": {"url": image(leaf)}}]}]
        res = call(model, msg, effort)
        if "error" not in res:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{f.parent.name} {leaf}: ${res.get('cost', 0):.4f} {res.get('seconds')}s {res.get('error', '')[:200]}", flush=True)

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, jobs))


def he_segments():
    return [l.strip() for l in (ROOT / "data" / "imrei-binah-16.he.txt").read_text(encoding="utf-8").split("\n") if l.strip()]


def run_translate(specs):
    segs = he_segments()
    prompt = TR_PROMPT.replace("{n}", str(len(segs))).replace(
        "{segs}", "\n".join(f"{i + 1}. {s}" for i, s in enumerate(segs)))

    def one(spec):
        model, effort, name = model_spec(spec)
        f = OUT / "translate" / f"{name}.json"
        if f.exists():
            return
        res = call(model, [{"role": "user", "content": prompt}], effort, json_mode=True)
        if "error" not in res:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{name}: ${res.get('cost', 0):.4f} {res.get('seconds')}s out={res.get('out')} "
              f"reasoning={res.get('reasoning')} {res.get('error', '')[:200]}", flush=True)

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(one, specs))


# ---------- scoring ----------
def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[֑-ׇ]", "", s)  # points
    s = s.replace("״", '"').replace("׳", "'").replace("”", '"').replace("“", '"').replace("’", "'")
    s = re.sub(r"[^א-ת\"'\[\]()0-9a-zA-Z]+", " ", s)  # keep letters, gershayim, brackets
    return re.sub(r"\s+", " ", s).strip()


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def window(text: str, start: str, end: str) -> str:
    """Cut the model text to the span of the gold text (the boundary pages hold other chapters)."""
    i = text.find(start)
    j = text.rfind(end)
    if i < 0 or j < 0:
        return text
    return text[i:j + len(end)]


def score():
    import difflib
    gold = norm(" ".join(he_segments()))
    gw = gold.split()
    start, end = " ".join(gw[:3]), " ".join(gw[-3:])
    rows = []
    for d in sorted((OUT / "ocr").glob("*")):
        files = sorted(d.glob("*.json"))
        if len(files) != len(LEAVES):
            continue
        res = [json.loads(f.read_text(encoding="utf-8")) for f in files]
        text = norm(" ".join(r["text"] for r in res))
        cut = window(text, start, end)
        cw = cut.split()
        sm = difflib.SequenceMatcher(None, gw, cw, autojunk=False)
        word_err = sum(max(i2 - i1, j2 - j1) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal")
        cer = lev(gold, cut) / len(gold)
        rows.append((d.name, sum(r["cost"] for r in res), cer, word_err / len(gw),
                     len(cw) - len(gw), sum(r["seconds"] for r in res) / len(res),
                     "cut ok" if cut != text else "NO CUT"))
    print(f"gold: {len(gold)} chars, {len(gw)} words")
    print(f"{'model':45} {'cost $':>7} {'per pg':>7} {'CER':>6} {'WER':>6} {'+words':>6} {'s/pg':>5}")
    for name, cost, cer, wer, extra, sec, note in sorted(rows, key=lambda r: r[2]):
        print(f"{name:45} {cost:7.3f} {cost / len(LEAVES):7.4f} {cer:6.2%} {wer:6.2%} {extra:6d} {sec:5.0f} {note}")
    for f in sorted((OUT / "translate").glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        try:
            en = json.loads(re.sub(r"^```(json)?|```$", "", r["text"].strip()))["en"]
            n = len(en)
        except Exception as e:
            n = f"bad JSON ({e})"
        print(f"translate {f.stem:45} ${r['cost']:.4f} {r['seconds']}s segments={n} out={r['out']} reasoning={r['reasoning']}")


def diffs(spec: str, limit: int = 60):
    """Word differences between the gold and one model's OCR."""
    import difflib
    name = spec.replace("/", "_")
    gold = norm(" ".join(he_segments())).split()
    text = norm(" ".join(json.loads(f.read_text(encoding="utf-8"))["text"]
                         for f in sorted((OUT / "ocr" / name).glob("*.json"))))
    cut = window(text, " ".join(gold[:3]), " ".join(gold[-3:])).split()
    sm = difflib.SequenceMatcher(None, gold, cut, autojunk=False)
    n = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            print(f"{op:8} gold: {' '.join(gold[i1:i2])[:80]:40} | model: {' '.join(cut[j1:j2])[:80]}")
            n += 1
            if n >= limit:
                break


if __name__ == "__main__":
    task, args = sys.argv[1], sys.argv[2:]
    {"ocr": run_ocr, "translate": run_translate}.get(task, lambda a: None)(args)
    if task == "score":
        score()
    if task == "diffs":
        diffs(args[0])
