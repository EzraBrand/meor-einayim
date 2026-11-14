# Azariah de' Rossi, *Me'or Einayim*: an English translation, pilot

Site: <https://ezrabrand.github.io/meor-einayim/>

Azariah de' Rossi (about 1511 to 1578) printed *Me'or Einayim* in Mantua in 1573–75. This repository holds a segment-aligned Hebrew and English text of one chapter, and the script that builds the side-by-side page.

## Status

| Chapter | Status |
|---|---|
| Imrei Binah 16 (the gnat that entered the nostril of Titus) | Pilot, 13-Nov-2026. 119 segments. References not verified. 13 uncertain renderings. |
| All other chapters | Not started |

## Sources

- **Hebrew text:** the Vilna 1863–66 printing, edited by David Cassel: [archive.org scan](https://archive.org/details/sefermeorenayim00ross). Chapter 16 is on printed pages 203–209 (scan images 227–233). The text starts from the archive.org OCR (`_djvu.txt`) and is corrected against the page images.
- **First edition:** Mantua 1573–75, [National Library of Israel scan](https://www.nli.org.il/he/books/NNL_ALEPH001072949/NLI). Not yet compared.
- **Not included:** the author's notes, which the Vilna printing sets in Rashi type. The OCR of that type is not usable.
- No open, clean digital Hebrew text was found (Sefaria, Hebrew Wikisource and Project Ben-Yehuda do not have the book).

## Translations that exist

- Complete: Joanna Weinberg, *The Light of the Eyes* (Yale Judaica Series 31, 2001). In copyright; not used for this draft.
- Chapter 16: Latin in Bochart's *Hierozoicon*; English by Raphall, *Hebrew Review* vol. 2 (as listed in the Jewish Encyclopedia). Not yet compared.

## Model test, 14-Nov-2026

`scripts/model_eval.py` compares OpenRouter models on chapter 16 (results in `eval/`, not in the repository).

| Task | Model | Cost | Result |
|---|---|---|---|
| OCR of the main text (7 pages) | Opus 5.5 @low | $0.047/page | 0.8% word error |
| | Gemini 3.1 Pro | $0.019/page | 1.0% |
| | Gemini 3.8 Flash | $0.004/page | 1.5% |
| | Sonnet 5.5 | $0.024/page | 2.4% |
| Translation (119 segments) | Opus 5.5 @low | $0.23/chapter | best: names, references, uncertain places |
| | Sonnet 5.5, Gemini 3.1 Pro | $0.07-0.08 | accurate but plainer; Gemini Pro changed a printed number |
| | Gemini Flash, DeepSeek V4 Pro, GPT-5.6 Terra, Haiku 5.5 | | invented identifications or broke the alignment |

Choice: Opus OCR with Gemini Flash as a second reader (disagreements checked on the scan), and Opus translation.
The test also found 10 errors in the chapter 16 Hebrew; they are corrected against the scan.

## Layout

| Path | Contents |
|---|---|
| `data/imrei-binah-NN.he.txt` | Hebrew, one segment on each line, a blank line between paragraphs |
| `data/imrei-binah-NN.en.txt` | English, one segment for each Hebrew segment |
| `data/imrei-binah-NN.notes.json` | Notes for the uncertain renderings (⚠) |
| `scripts/build_page.py` | Checks the alignment and writes `docs/imrei-binah-NN.html` |
| `docs/` | The site |
| `source/` | Local copies of the scan PDF and OCR text (not in the repository) |

## Build

```
py -3.13 scripts/build_page.py 16 "Imrei Binah, chapter 16" "The gnat that entered the nostril of Titus"
```

`build_page.py` stops if the Hebrew and English segment counts do not agree, or if the ⚠ marks and the notes do not agree.

## English file format

- One line of English for each Hebrew segment. A blank line ends a paragraph. The division is the translator's; the print has no paragraph breaks in this chapter.
- Text in `[square brackets]` is added by the translator: references such as `[b. Gittin 56b]` and supplied words.
- `⚠3` points to note 3.

## Credits

The English draft is by Claude (Anthropic), directed and reviewed by Ezra Brand.
