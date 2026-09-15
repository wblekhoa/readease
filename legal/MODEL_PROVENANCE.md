# Downloaded model provenance

Model weights are not committed to this repository or embedded in the app
bundle. ReadEase downloads only the exact revisions below into its private
Application Support directory during explicit first-run setup.

| Asset | Repository | Revision | Declared license | Model-card receipt |
| --- | --- | --- | --- | --- |
| VieNeu-TTS v3 Turbo backbone and preset voices | `pnnbao-ump/VieNeu-TTS-v3-Turbo` | `2da0efab622a1722125991736524f080b751ef5b` | Apache-2.0 | README SHA-256 `f8a7927b5a6f27d1ab54c63a22a3c010f8622b006c3239a691bcd014b108b2b7` |
| MOSS Audio Tokenizer Nano ONNX codec | `OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX` | `ceff0d0749bfb3fa2d61149794ec6feef0d1e1ae` | Apache-2.0 | README SHA-256 `3c7b9e9ef1c8c5e5c829a077a1d32c1f7aea1668f2bf17ead318ff04bf1e6fe4` |
| Kokoro-82M v1.0 ONNX (English voice; `onnx/model.onnx`, `tokenizer.json`, six `voices/*.bin`) | `onnx-community/Kokoro-82M-v1.0-ONNX` | `1939ad2a8e416c0acfeecc08a694d14ef25f2231` | Apache-2.0 | per-file SHA-256 pinned in `src/vieneu_reader/speech/kokoro.py` (`MODEL_FILES`); `model.onnx` `8fbea51ea711f2af382e88c833d9e288c6dc82ce5e98421ea61c058ce21a34cb` |
| misaki English lexicon (`us_gold.json`, `us_silver.json`) | `hexgrad/misaki` (GitHub, raw file download) | `fba1236595f2d2bf21d414ba6e57d25256afada3` | Apache-2.0 | SHA-256 `dc414872a49a28ae6c141463d502fd945f3b2fde040484fdc47d00cc4612686f`, `de8f67be911bb6c659187b4a65fd966b6a30e56350e0f790d763210b053ac475` |

The English voice is optional: nothing of it is fetched on first run. It is
downloaded when the reader asks for it under Settings › Reading models, every
file is checked against the hash pinned in code before the ready marker is
written, and it can be removed from the same place.

One small model ships **inside** the bundle rather than being downloaded: the
English G2P's out-of-lexicon reader, `PeterReid/graphemes_to_phonemes_en_us`
(BART, Apache-2.0 publisher declaration, revision
`a5631b285d18d59483c32c0c3379cb9fac924f4b`), exported to two ONNX graphs at
development time and carried as package data
(`src/vieneu_reader/speech/english/fallback_assets/`, 3 MB). It reads names
and terms the lexicon does not have; it never sees a whole sentence.

The upstream VieNeu model card states that its preset voices have commercial
usage permission and speaker consent. This is publisher-supplied provenance,
not an independent chain-of-title audit. Public binary release remains subject
to publisher review of those claims.
