# Initial Translation Audit — 2026-09-17

Status: preliminary source-level audit, not passage-complete certification.

## 1. Linear B / DĀMOS

Finding: current Mycenaean interpretation is explicitly non-binary. DĀMOS supports multiple simultaneous analyses for a linguistic unit, ranked by probability, because the script's phonetic limitations and fragmentary texts often make meaning/grammar uncertain. Its current online interface also exposes changes caused by new joins and new readings.

Audit implication:
- do not treat one published Linear B translation as uniquely certain when DĀMOS records alternatives;
- translations predating a material join/new reading require re-audit.

Risk classes: T2_LEXICAL, T3_GRAMMATICAL, T6_SUPERSEDED where edition history warrants.

Sources:
- https://damos.hf.uio.no/about/database/
- https://damos.hf.uio.no/about/online/
- https://damos.hf.uio.no/about/texts/

## 2. Ancient Egyptian / TLA

Finding: TLA is a living, versioned corpus. It distinguishes transliteration, lemma analysis, modern-language translation and editorial state. Corpus edition 20 / web app 2.5.2 is dated 20 Aug 2026; lemma records can be filtered by verification state.

Audit implication:
- an English translation alone is not enough; compare against current transliteration/lemma state;
- records with verification pending should not be treated as equivalent to verified records;
- older translations should be checked against current lemma analyses.

Risk classes: T2_LEXICAL, T3_GRAMMATICAL, T6_SUPERSEDED where current corpus differs.

Sources:
- https://tla.digital/
- https://tla.digital/info/text-corpus
- https://tla.digital/help/search-page

## 3. Cuneiform / ORACC

Finding: ORACC's translation format explicitly distinguishes supplied wording, literal-but-contextually-inadequate renderings, uncertain translation, untranslatable passages, broken text and restored text.

Audit implication:
- flattening ORACC markup into smooth English destroys epistemically important distinctions;
- supplied/restored words must remain marked in ATIP.

Risk classes: T5_RESTORATION, T7_INTERPOLATION if supplied material is presented as witnessed text, T8_UNRESOLVED.

Source:
- https://oracc.museum.upenn.edu/doc/help/editinginatf/translations/index.html

## 4. Greek/Latin papyri / Papyri.info

Finding: Papyri.info preserves editorial history and apparatus showing corrected readings, including corrections made from images and subsequent scholarly review.

Audit implication:
- translations based on earlier readings may become stale;
- every canonical translation should link to the exact DDbDP/HGV/APIS edition state.

Risk classes: T4_WITNESS, T6_SUPERSEDED.

Examples:
- https://papyri.info/editions/p.benaki/4
- https://papyri.info/ddbdp/p.tebt%3B2%3B408

## 5. Gāndhārī corpus

Finding: the Gāndhārī corpus reports thousands of documented corrections/improvements to published texts and is progressively integrating accepted text with the history of earlier readings and interpretations.

Audit implication:
- old print translations cannot automatically be considered current where the accepted underlying reading has changed;
- reading-history should be first-class provenance.

Risk classes: T4_WITNESS, T6_SUPERSEDED.

Source:
- https://gandhari.org/main/plugins/corpus/

## 6. 1 Enoch

Finding: "1 Enoch" is not one homogeneous witness. Ethiopic, Greek and Qumran Aramaic evidence must be distinguished. Current critical translation work such as Nickelsburg/VanderKam explicitly incorporates Ethiopic, Greek and Dead Sea Aramaic evidence unavailable to older translations such as R. H. Charles (1912).

Audit implication:
- Charles remains historically important but should not serve as the default current critical translation without comparison to post-Qumran scholarship;
- passages where Aramaic/Greek/Ethiopic witnesses differ are witness-dependent rather than reducible to one English wording;
- absence of Parables (chs. 37–71) from the extant Aramaic fragments must not be silently interpreted as proof the section never existed in antiquity.

Risk classes: T4_WITNESS, T6_SUPERSEDED for older witness-limited renderings, T8_UNRESOLVED in materially divergent passages.

Sources:
- https://www.jstor.org/stable/j.ctt22nm5vn
- https://www.cambridge.org/core/journals/new-testament-studies/article/abs/snts-pseudepigrapha-seminars-at-tubingen-and-paris-on-the-books-of-enoch/E54FD88E7D00000A2CD8ACEC3FCED07B
- https://cart.sbl-site.org/books/0603120P

## 7. Maya

Finding: Maya decipherment remains an ongoing process; the Harvard CMHI exists in part to provide increasingly precise photographs, drawings and scans that allow epigraphers to revise readings.

Audit implication:
- older published glyph readings are candidates for re-audit against modern documentation;
- unresolved glyphs must remain unresolved rather than being forced into fluent narrative.

Risk classes: T2_LEXICAL, T4_WITNESS/documentation, T6_SUPERSEDED when later epigraphy changes a reading.

Sources:
- https://peabody.harvard.edu/about-corpus-maya-hieroglyphic-inscriptions
- https://peabody.harvard.edu/publications/corpus-maya-hieroglyphic-inscriptions-volume-3-part-4-yaxchilan

## Preliminary conclusion

The first scan already shows that the principal risk is not that "all current translations are wrong." It is that users often consume a single smooth translation without seeing:
- witness variants,
- damaged/restored text,
- uncertain morphology,
- later editorial corrections,
- or evidence discovered after an older translation was published.

ATIP should therefore audit **translation lineage**, not merely compare English sentences.
