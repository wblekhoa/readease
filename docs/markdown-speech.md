# Markdown bold in speech

Session checkpoint: 2026-10-04, `campaign/reading-states`, base `64cb319`.

The reported selection contained `**Câu chuyện.**`. Speech shaping removed
the opening stars as bullets but retained the closing stars. Those closing
stars also prevented the sentence splitter from seeing the full stop.

`domain/markdown.py` now removes paired `**words**` and `__words__` around
prose. Escaped markers, inline/fenced backtick code, preformatted segments,
incomplete pairs and literal powers retain their bold delimiters. This is
a conservative strong-emphasis rule, not a complete Markdown renderer.
Nested emphasis, headings, links and other Markdown constructs are outside
this fix's scope.

Transient reading resolves pairs across all original parts before speech
shaping, then keeps each part's source text and id. The headless read,
display-parts reply and estimate share this builder. The playback
coordinator applies the same rule. Changed speech strings naturally get
new audio-cache keys; source documents are untouched.

Verification: regression tests failed before their fixes. The final
`scripts/verify.sh` exited 0: 888 Python tests (7 skipped), native selection
bridge PASS, 32 Rust tests passed, compileall and diff check passed.
The Python suite emitted unclosed SQLite connection ResourceWarnings.
The protocol integration test checks engine input, source text, sentence
boundaries and estimate character count. Long-span and code-span tests
check chunk boundaries. No real model listening, installed-app replacement,
commit, push or release was performed during the initial fix.

## Local installation, 2026-10-04

The owner subsequently requested completion and installation. Re-ran
`scripts/verify.sh`: 888 Python tests (7 skipped), native bridge PASS and
32 Rust tests passed. Built through `scripts/build-release-app.sh` with
`READEASE_SKIP_NOTARY=1`, using Developer ID for local installation only.
The build passed 216 frontend tests, UI/mock audits, the seven bundle
contract tests, macOS floor 15.0 and the public-source/bundle audit.

Installed `0.1.19+64cb319-dirty` at
`~/Applications/ReadEase.app` through `install-local-app.sh`.
The previous `0.1.16+3bcfc76` app was moved to Trash. The app was reopened
and its process observed. Installed signature verification passed; its
engine SHA-256 matches the built bundle:
`0ba075d20379c370c5051093b88810d597a81eaf15d080d774285ceeb9ec327c`.

Both the built and installed frozen engines passed an isolated-data-root
protocol probe: original `text.parts` source retained, `estimate` character
count excludes the four bold markers. No real-model listening was performed.
The local build was not notarized, committed, pushed or published.

## Powers in one selection, 2026-10-06

Two powers in one selection paired up as bold: `Tính 2**10 rồi 3**4.`
was spoken "Tính 210 rồi 34.", contradicting the literal-powers rule above.
A `**` delimiter may no longer touch a letter or digit on its outer side, so
intraword `**` stays literal; bold around digits only (`**2026**`) is now
read. Regression cases failed first, then passed. Re-ran `scripts/verify.sh`:
888 Python tests (7 skipped), native bridge PASS, 32 Rust tests. `pnpm build`
216 tests; render audit `--only reading_` 56 cells PASS. The installed app
was not rebuilt.

## Everyday Markdown in pasted and scanned text, 2026-10-06

The owner asked for every case to be handled. `markdown_speech_parts`
(`domain/markdown.py`) now reads pasted and scanned text the way it was
meant, with the splitter's joints telling it where authored lines open:

- Inline: `*`/`_` emphasis at every strength (`*x*`, `**x**`, `***x***`) and
  nested (`**a *b* c**`, `_**x**_`), `~~strike~~`, links and images (their
  words, never the address), reference links, footnote references (dropped),
  autolinks (address kept for `speak_links`), and an allowlist of inline HTML
  tags (`<br>`, `<p>`, `<div>` leave a space). Code spans and fences lose
  their backticks and info word; their content stays literal. Escapes lose
  the backslash and keep the character; a hard-break backslash is dropped.
- Line openings: `#` headings (closing hashes too) and setext underlines
  become a sentence with a full stop; rules, table separator rows and link
  reference definitions are silent; `>` quotes, `-`/`+`/`*` bullets and
  `[ ]`/`[x]` task boxes lose their markers; a table row reads "An, 7";
  a footnote definition reads its text. Ordered `1.` markers stay.
- Literal stays literal: a delimiter touching a letter or digit on its outer
  side (`5*3`, `2**10`, `snake_case`), spaced operators (`a * b`), unpaired
  marks, and `a < b > c`.
- Decision: a `- ` opening a pasted line is dropped even when it is fiction
  dialogue; the line break already carries the pause and the Vietnamese voice
  never said the dash.
- Decision: books keep `strip_strong` only. Book audio is cached by its spoken
  text, so a wider rule would re-synthesise, and on a paid voice re-bill,
  every changed paragraph; fiction also opens dialogue with `- `.
- The splitter no longer folds a lowercase line into a heading, a fence
  opener or a rule above it. A setext underline only promotes a plain line;
  `---` under a list item, quote or table row is a rule.
- Not handled: intraword emphasis (`un*frigging*believable`), `~sub~`/`^sup^`,
  and a lone unpaired backtick, which stays in the text.

Tests: `tests/domain/test_markdown.py` (22 tests) failed first; each rule
was switched off in turn and at least one test failed every time. Four
defects found on the way: a rule line swallowed the lowercase line
below it ("--- thân bài"); `---` under a list item turned the item into
a heading; a one-matcher-per-pass loop ran out of passes
before reaching `_` emphasis in a sentence holding every kind, and a link
body that could contain `[` made 90,000 `[` take 27 s (now 0.06 s; a
hostile-input test bounds it). A 99,000-character paste takes 0.13 s.
Re-ran `scripts/verify.sh`: 910 Python tests (7 skipped), native bridge
PASS, 32 Rust tests. The installed app was not rebuilt.
