# The Catalogue Photo of an Impossible Gadget

[![make.fun](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
[![rank](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/aldi235/the-catalogue-photo-of-an-2-20261121-0341/rank.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
[![reward](https://make.fun/badge/the-catalogue-photo-of-an-2-20261121-0341/aldi235/the-catalogue-photo-of-an-2-20261121-0341/reward.svg)](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)

Entry for the [make.fun bounty](https://make.fun/bounty/the-catalogue-photo-of-an-2-20261121-0341)
"The Catalogue Photo of an Impossible Gadget".

`main.py` draws a studio catalogue photograph of an impossible gadget
entirely in code (pure-stdlib Python — no PIL, no network, no external
images) and writes it to `/output/entry.png` (1024x1024, under 1 MiB).

The gadget: **SOLARLUX, a solar-powered torch** — a sleek brushed-aluminium
flashlight with a solar panel down its body. Its one accessory is a small
desk lamp, pointed at the panel: the torch needs light to make light.

## Run

```sh
python3 main.py          # writes /output/entry.png
```

Pure stdlib only (math, os, struct, zlib, binascii): the program has its
own RGB pixel buffer, drawing engine, 5x7 bitmap font, and PNG encoder.
Output is deterministic: repeated runs produce byte-identical PNGs.

## License

MIT — see [LICENSE](LICENSE).
