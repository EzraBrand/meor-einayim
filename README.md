# Azariah de' Rossi, *Me'or Einayim*: Hebrew and English

Site: <https://ezrabrand.github.io/meor-einayim/>

Azariah de' Rossi (about 1511 to 1578) printed *Me'or Einayim* in Mantua in 1573–75. This repository holds a segment-aligned Hebrew and English text of one chapter, and the script that builds the side-by-side page.

## Status

| Chapter | Status |
|---|---|
| Imrei Binah 16 (The gnat that entered the nostril of Titus) | Translated 13-Nov-2026; Hebrew checked against the scan by hand, 14-Nov-2026. 119 segments. References not verified. 13 uncertain renderings. |
| Imrei Binah 17 (The saying that the early generations had children at the age of eight) | Draft, 14-Nov-2026, by models; not reviewed. 151 segments. References not verified. 12 uncertain renderings. |
| Imrei Binah 18 (The saying: Cyrus is Darius is Artaxerxes) | Draft, 14-Nov-2026, by models; not reviewed. 143 segments. References not verified. 6 uncertain renderings. |
| Imrei Binah 19 (A note on the ancient Seder Olam: later additions, and other books that were tampered with) | Draft, 14-Nov-2026, by models; not reviewed. 124 segments. References not verified. 7 uncertain renderings. |
| Imrei Binah 20 (The number of high priests in the Second Temple; the views of Rabbenu Tam and R. Isaac on the First Temple rejected) | Draft, 14-Nov-2026, by models; not reviewed. 114 segments. References not verified. 5 uncertain renderings. |
| Imrei Binah 21 (Differences between the sages and Christian writers: the altar on Mount Gerizim, the image of the dove, and how many King Yannais there were) | Draft, 14-Nov-2026, by models; not reviewed. 137 segments. References not verified. 10 uncertain renderings. |
| Imrei Binah 22 (Objections to Abraham ibn Daud and Don Isaac Abravanel on Simeon the Just, and whether there was more than one of that name) | Draft, 14-Nov-2026, by models; not reviewed. 99 segments. References not verified. 5 uncertain renderings. |
| Imrei Binah 23 (More objections, also to Saadia, Maimonides, Yesod Olam and Kaftor va-Ferah: the era of contracts began not with Alexander but after his empire was divided) | Draft, 14-Nov-2026, by models; not reviewed. 117 segments. References not verified. 4 uncertain renderings. |
| Imrei Binah 24 (From the start of Greek rule (the era of contracts) to our day, the sages of Israel and of the nations do not really disagree) | Draft, 14-Nov-2026, by models; not reviewed. 37 segments. References not verified. 8 uncertain renderings. |
| Imrei Binah 25 (The count of years from Creation came into general use among our people only after the close of the Babylonian Talmud) | Draft, 14-Nov-2026, by models; not reviewed. 142 segments. References not verified. 6 uncertain renderings. |
| Imrei Binah 26 (Difficulties in two sayings of R. Yose, and their solution) | Draft, 14-Nov-2026, by models; not reviewed. 108 segments. References not verified. 9 uncertain renderings. |
| Imrei Binah 27 (A defence of the sages, even granting that in some stories that do not touch the law they did not establish the truth) | Draft, 14-Nov-2026, by models; not reviewed. 141 segments. References not verified. 8 uncertain renderings. |
| Imrei Binah 28 (Beyond three kinds of teaching, the foundations of the Oral Torah, the sages let later scholars disagree with them; their errors in worldly matters do not imply errors in Torah) | Draft, 14-Nov-2026, by models; not reviewed. 157 segments. References not verified. 9 uncertain renderings. |
| Imrei Binah 29 (Yemei Olam, the third section: is the count of years from Creation to be lengthened or shortened?) | Draft, 14-Nov-2026, by models; not reviewed. 97 segments. References not verified. 6 uncertain renderings. |
| Imrei Binah 30 (What Xenophon the Greek says about the two Cyruses, kings of Persia) | Draft, 14-Nov-2026, by models; not reviewed. 36 segments. References not verified. 9 uncertain renderings. |
| Imrei Binah 31 (The words of Metasthenes the Persian in his book on the order of the times) | Draft, 14-Nov-2026, by models; not reviewed. 54 segments. References not verified. 7 uncertain renderings. |
| Imrei Binah 32 (The Book of Times of Philo (Yedidyah) of Alexandria, translated from Greek into Latin and now into Hebrew) | Draft, 14-Nov-2026, by models; not reviewed. 97 segments. References not verified. 8 uncertain renderings. |
| All other chapters | Not started |

## Sources

- **Hebrew text:** the Vilna 1863–66 printing in the series Kiryat Sefer, begun by Isaac Benjacob (d. 1863), "printed after the Mantua edition, with all the first and second versions in their places in the text" (title page): [archive.org scan](https://archive.org/details/sefermeorenayim00ross). Chapter 16 is on printed pages 203–209 (scan images 227–233). The text starts from the archive.org OCR (`_djvu.txt`) and is corrected against the page images.
- **First edition:** Mantua 1573–75, [National Library of Israel scan](https://www.nli.org.il/he/books/NNL_ALEPH001072949/NLI). Not yet compared.
- **Not included:** the notes in Rashi type. By the title page they are "many additions by the author and some later scholars", until then in manuscript in the margin of a copy of the book owned by Leopold Zunz. This edition does not yet separate the author's notes from the later ones. The OCR of Rashi type is not usable yet.
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

One chapter, in order (`scripts/pipeline.py` has the details):

```
py -3.13 scripts/pipeline.py ocr 233 262                                     # Opus + Flash OCR of scan leaves 233-262
py -3.13 scripts/pipeline.py ocr 233 262 --model google/gemini-3.1-pro-preview@low   # third reader
py -3.13 scripts/pipeline.py chapters                                        # chapter headings found
py -3.13 scripts/pipeline.py vote 17       # data/votes/17.json; read logs/crops/17/ and decide the 'check' items
py -3.13 scripts/pipeline.py assemble 17   # data/imrei-binah-17.he.txt
py -3.13 scripts/pipeline.py translate 17  # .en.txt + .notes.json (Opus 5.5); English fixes in data/en_fixes.json
py -3.13 scripts/build_page.py 17          # docs/imrei-binah-17.html and the index
```

Chapter titles, pages and status: `data/chapters.json`. The OCR of every reader is in `data/ocr/`.
Cost of chapters 17-21 (26 pages, 14-Nov-2026): OCR $2.20, translation $1.10. Chapters 22-32 (43 pages): OCR $2.77, translation $1.93.

`build_page.py` stops if the Hebrew and English segment counts do not agree, or if the ⚠ marks and the notes do not agree.

## English file format

- One line of English for each Hebrew segment. A blank line ends a paragraph. The division is the translator's; the print has no paragraph breaks in this chapter.
- Text in `[square brackets]` is added by the translator: references such as `[b. Gittin 56b]` and supplied words.
- `⚠3` points to note 3.

## Credits

The English draft is by Claude (Anthropic), directed and reviewed by Ezra Brand.

## License

MIT (see `LICENSE`): the code, the Hebrew transcription and the English translation in this repository.
