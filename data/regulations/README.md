# Regulations Data

Place the FIA Formula 1 Technical Regulations PDF in this directory.

Expected usage:

```bash
python scripts/seed_regulations.py
```

If one or more PDF files exist here, the latest filename is used automatically.
If no PDF exists, the parser falls back to the curated static Week 4 dataset.
