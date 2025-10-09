
# structure

```
bootloader_art_engine/
├─ run_bootloader_engine.py
├─ engine/
│  ├─ __init__.py
│  ├─ core.py          # Project interface, context, config merge
│  ├─ io.py            # filesystem helpers, image loading, layers stack
│  ├─ rle.py           # quantize/trim → runs model; hex/base36 utils
│  ├─ payload.py       # pack_blob(model) → payload text
│  ├─ template.py      # BOOTLOADER_TEMPLATE (ES5, bootloader-safe)
│  └─ minify.py        # whitespace-only minifier
├─ projects/
│  └─ sample/
│     ├─ __init__.py
│     ├─ project.py    # project-level config + input resolver
│     └─ input/
│        ├─ base.png   # or
│        └─ layers/    # 00.png, 01.png, ...
└─ out/                # created on run: out/<project>/*
```