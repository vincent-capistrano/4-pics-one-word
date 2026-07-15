# 4 Pics 1 Word

A cross-platform **4 Pics 1 Word** game built with Python + Kivy.  
Images are fetched **automatically from Wikipedia** — no manual updates ever needed.  
Runs on **Windows, macOS, Linux, and Android**.

---

## Screenshots

| Main Menu | Game Screen | Loading |
|-----------|-------------|---------|
| Dark navy theme with score & level | 2×2 image grid + letter tiles | Animated loader while images download |

---

## Features

- **Auto-updating images** — Wikipedia article thumbnails fetched live for every word  
- **203 words** across Easy / Medium / Hard difficulty  
- **Smart image filtering** — person names, music bands, and year-range bios are automatically excluded so only relevant photos appear  
- **Local image cache** — once fetched, images load instantly offline  
- **Point-based hint system** — earn points by solving words, spend them on hints  
- **User progress saved** — score, level, completed words and high score persist across sessions  
- **No API key required** — all image sources are freely accessible  
- **Runs on Android** — build with buildozer (see below)

---

## Getting Started (Desktop)

### 1. Clone the repo
```bash
git clone https://github.com/vincent-capistrano/4-pics-one-word.git
cd "4-pics-one-word"
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run
```bash
python main.py
```

---

## Build for Android (APK)

### Option A — GitHub Actions (recommended, no Linux needed)

Every push to `main` automatically builds a debug APK via the included  
[`.github/workflows/build_android.yml`](.github/workflows/build_android.yml).  
Download the APK from the **Actions → Artifacts** tab of your repository.

### Option B — Build locally (requires Linux or WSL)

```bash
pip install buildozer
buildozer android debug
# APK appears in  bin/fourpicsoneword-1.0.0-arm64-v8a-debug.apk
```

> Buildozer requires Linux. On Windows, use WSL 2 with Ubuntu.

---

## Project Structure

```
├── main.py           # Kivy app — all screens and UI logic
├── api_handler.py    # Image fetching (Wikipedia → Wikimedia → Loremflickr)
├── user_data.py      # JSON-based save/load for player progress
├── word_list.py      # 203 words with hints and difficulty ratings
├── icon.png          # App icon (512×512, generated with Pillow)
├── requirements.txt  # Python dependencies
└── buildozer.spec    # Android build configuration
```

---

## Image Source Pipeline

Images are fetched in priority order — all free, no API key:

| Priority | Source | Why |
|----------|--------|-----|
| 1 | **Wikipedia article thumbnails** | Hand-picked lead images; always accurate |
| 2 | **Wikimedia Commons search** | Broader pool for less common words |
| 3 | **Loremflickr** | Rate-limit fallback; no request limits |

Filtering applied to Wikipedia results:
- Title must contain the search word as a **whole word** (blocks "Nimbus" for "bus")
- Short description must not match **person / biography** indicators (`born`, year ranges, professions)
- Short description must not match **music group** indicators (`rock band`, `formed in`, etc.)
- TIFF, SVG, and DjVu URLs are skipped

---

## Hint Economy

| Action | Points |
|--------|--------|
| Solve a word (Level 1) | +100 pts |
| Solve a word (Level N) | +100 × N pts |
| Use a hint | −100 pts |

Level increases every 5 completed words.

---

## Requirements

- Python 3.10+
- kivy >= 2.2.0
- requests >= 2.28.0
- Pillow >= 9.0.0

---

## License

MIT
