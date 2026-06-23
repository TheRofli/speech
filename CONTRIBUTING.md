# Contributing

Thanks for improving Speech.

## Local Checks

Run Python tests:

```powershell
D:\Speech\.venv\Scripts\python.exe -m unittest discover -s D:\Speech\tests
```

Run Tauri checks:

```powershell
cd D:\Speech\tauri
npm install
npm run build
cd src-tauri
cargo check
```

## Do Not Commit

- model weights
- `.venv`
- `data`
- `cache`
- `tmp`
- `node_modules`
- Tauri `target` or `dist`

## Design Direction

Speech should feel soft, minimal, friendly, and practical: white, blush pink,
warm off-white, and soft charcoal. Avoid cyberpunk, neon dashboards, or loud
high-tech styling.
