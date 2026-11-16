"""Download scan leaves A..B to source/pages/ in parallel (archive.org needs 10-20 s a page).

  py -3.13 scripts/fetch_pages.py 80 226 361 505
"""
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P  # noqa: E402

args = [int(x) for x in sys.argv[1:]]
leaves = [l for a, b in zip(args[::2], args[1::2]) for l in range(a, b + 1)]
todo = [l for l in leaves if not (P.PAGES / f"{l}.jpg").exists()]
print(f"{len(todo)} of {len(leaves)} pages to download", flush=True)


def one(leaf):
    for attempt in range(3):
        try:
            P.image_file(leaf)
            return
        except Exception as e:  # noqa: BLE001
            print(f"{leaf}: {e} (try {attempt + 1})", flush=True)
    print(f"{leaf}: FAILED", flush=True)


done = 0
with ThreadPoolExecutor(6) as ex:
    for _ in ex.map(one, todo):
        done += 1
        if done % 20 == 0:
            print(f"{done}/{len(todo)}", flush=True)
print("done", flush=True)
