"""
Image fetcher for 4 Pics 1 Word.

Source priority (all free, no API key):
  1. Wikipedia article pageimages — each Wikipedia article has a hand-picked
     lead image that *always* accurately represents the topic.  Searching
     "pasta" returns the Pasta article image, the Spaghetti article image,
     the Fettuccine article image, etc. — never unrelated photos.
  2. Wikimedia Commons file search — broader pool, falls back to this when
     Wikipedia doesn't return enough distinct thumbnails.
  3. Loremflickr — last resort for obscure keywords.

Images are cached locally so the game works offline on repeat plays.
"""

import os
import re
import time
import requests


class ImageAPIHandler:
    """Fetches and caches 4 images per word. No API key required."""

    _WIKIPEDIA  = "https://en.wikipedia.org/w/api.php"
    _WIKIMEDIA  = "https://commons.wikimedia.org/w/api.php"
    _FLICKR     = "https://loremflickr.com"
    _W, _H      = 400, 400
    _HEADERS    = {"User-Agent": "4Pics1Word/1.0 (educational game)"}

    def __init__(self, cache_dir: str, api_key: str = ""):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    # ── cache helpers ─────────────────────────────────────────────────────────

    def _cache_path(self, word: str, idx: int) -> str:
        safe = word.lower().replace(" ", "_").replace("/", "_")
        return os.path.join(self.cache_dir, f"{safe}_{idx}.jpg")

    def _is_fully_cached(self, word: str) -> bool:
        return all(
            os.path.exists(self._cache_path(word, i))
            and os.path.getsize(self._cache_path(word, i)) > 2048
            for i in range(4)
        )

    # ── network helpers ───────────────────────────────────────────────────────

    def _download(self, url: str, path: str) -> None:
        """Stream-download *url* to *path*.  Raises immediately on any error,
        including HTTP 429, so the caller can skip to the next candidate URL."""
        resp = requests.get(
            url, timeout=20, stream=True,
            headers=self._HEADERS, allow_redirects=True,
        )
        resp.raise_for_status()   # raises HTTPError (incl. 429) instantly
        with open(path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)

    # Keywords found in Wikipedia short descriptions of people OR groups
    # that appear as photos of people (bands, music groups, etc.)
    _PERSON_DESC_WORDS = frozenset({
        # Individual people
        "born", "actor", "actress", "singer", "musician", "politician",
        "player", "footballer", "swimmer", "rapper", "composer",
        "poet", "painter", "sculptor", "athlete",
        "businessman", "businesswoman", "entrepreneur",
        "scientist", "professor", "researcher",
        "coach", "manager", "ceo", "founder",
        "director", "producer", "presenter", "journalist",
        "murderer", "criminal", "convict",
        # Music groups / bands (their article thumbnails show people)
        "rock band", "pop band", "jazz band", "punk band", "metal band",
        "folk band", "indie band", "country band", "reggae band",
        "hip hop group", "pop group", "music group", "musical group",
        "boy band", "girl group", "supergroup", "boy group",
        "music duo", "comedy duo", "musical duo",
        "formed in",       # "Canadian band, formed in 1966"
    })
    # Deceased persons use "(YYYY–YYYY)" or "(YYYY-YYYY)" instead of "born"
    _YEAR_RANGE_RE = re.compile(r'\(\d{4}[\u2013\u2014-]\d{4}\)')

    def _is_person_desc(self, desc: str) -> bool:
        """Return True if *desc* looks like a Wikipedia biography description."""
        d = desc.lower()
        return (
            any(kw in d for kw in self._PERSON_DESC_WORDS)
            or bool(self._YEAR_RANGE_RE.search(desc))
        )

    def _wikipedia_urls(self, word: str, want: int = 8) -> list:
        """
        Search Wikipedia articles for *word* and return their lead thumbnail
        image URLs.  Articles are filtered by:
          1. Title must contain *word* as a whole word (no false compounds).
          2. Short description must not indicate a person's biography.
        """
        params = {
            "action":       "query",
            "generator":    "search",
            "gsrsearch":    word,
            "gsrnamespace": "0",
            "prop":         "pageimages|pageprops",  # pageprops gives short desc
            "piprop":       "thumbnail",
            "pithumbsize":  str(self._W),
            "ppprop":       "wikibase-shortdesc",    # e.g. "American actor (born 1975)"
            "format":       "json",
            "gsrlimit":     "50",
        }
        try:
            resp = requests.get(
                self._WIKIPEDIA, params=params,
                timeout=15, headers=self._HEADERS,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
        except Exception as exc:
            print(f"[Wikipedia] {exc}")
            return []

        wl   = word.lower()
        urls = []
        for page in sorted(pages.values(), key=lambda p: p.get("index", 9999)):
            title = page.get("title", "").lower()
            # Filter 1: word must appear as a standalone word in the title
            if not (title == wl
                    or title.startswith(wl + " ")
                    or (" " + wl + " ") in title
                    or title.endswith(" " + wl)):
                continue

            # Filter 2: skip biography / person articles
            desc = page.get("pageprops", {}).get("wikibase-shortdesc", "")
            if desc and self._is_person_desc(desc):
                continue

            thumb = page.get("thumbnail", {}).get("source")
            if thumb:
                urls.append(thumb)
            if len(urls) >= want:
                break
        return urls

    def _wikimedia_urls(self, word: str, want: int = 8) -> list:
        """
        Search Wikimedia Commons for JPEG/PNG photos matching *word*.
        Returns up to *want* thumbnail URLs, ranked by search relevance.
        """
        params = {
            "action":       "query",
            "generator":    "search",
            "gsrsearch":    word,
            "gsrnamespace": "6",          # File namespace only
            "prop":         "imageinfo",
            "iiprop":       "url|mime|size",
            "iiurlwidth":   str(self._W),
            "format":       "json",
            "gsrlimit":     "50",
        }
        try:
            resp = requests.get(
                self._WIKIMEDIA, params=params,
                timeout=15, headers=self._HEADERS,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
        except Exception as exc:
            print(f"[Wikimedia] request failed: {exc}")
            return []

        urls = []
        # Sort by search-rank index so the most relevant images come first
        for page in sorted(pages.values(), key=lambda p: p.get("index", 9999)):
            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]
            if info.get("mime") not in ("image/jpeg", "image/png"):
                continue
            thumb = info.get("thumburl")
            if thumb:
                urls.append(thumb)
            if len(urls) >= want:
                break
        return urls

    # URL substrings that indicate non-photo formats (TIFF conversions,
    # SVG renders, scanned docs) — skip these to avoid slow/bad images.
    _BAD_URL_MARKERS = (".tif", "lossy-page", "-page1-", ".svg", ".djvu")

    def _is_bad_url(self, url: str) -> bool:
        u = url.lower()
        return any(m in u for m in self._BAD_URL_MARKERS)

    def _flickr_url(self, word: str, seed: int) -> str:
        kw = word.lower().replace(" ", "+")
        return f"{self._FLICKR}/{self._W}/{self._H}/{kw}?lock={seed}"

    # ── public API ────────────────────────────────────────────────────────────

    def get_images_sync(self, word: str) -> list:
        """
        Return 4 local image paths for *word*.
        Priority: Wikipedia article thumbnails → Wikimedia Commons → Loremflickr.
        """
        if self._is_fully_cached(word):
            return [self._cache_path(word, i) for i in range(4)]

        # 1. Wikipedia lead images (most accurate)
        candidates = self._wikipedia_urls(word, want=8)

        # 2. Wikimedia Commons (broader pool)
        if len(candidates) < 4:
            candidates += self._wikimedia_urls(word, want=8)

        # 3. Loremflickr — guaranteed fallback, no rate limits
        for seed in [1, 11, 22, 33, 44, 55, 66, 77]:
            candidates.append(self._flickr_url(word, seed))

        # Remove TIFF conversions, SVGs and other non-photo formats
        candidates = [u for u in candidates if not self._is_bad_url(u)]

        # Download until we have 4 good images.
        # On 429 or any error: skip that URL immediately (don't retry) and
        # move to the next candidate.  Loremflickr URLs at the end of the
        # list have no rate limits and guarantee we always end up with 4.
        paths = []
        for url in candidates:
            if len(paths) >= 4:
                break
            path = self._cache_path(word, len(paths))
            try:
                self._download(url, path)
                if os.path.getsize(path) > 2048:
                    paths.append(path)
                    if len(paths) < 4:
                        time.sleep(1.2)   # polite gap; keeps us under rate limit
                else:
                    os.remove(path)
            except Exception as exc:
                err = str(exc)
                if "429" in err:
                    time.sleep(2)   # brief pause then try NEXT url, not same one
                # always continue to next candidate

        if len(paths) < 4:
            raise ValueError(f"Only fetched {len(paths)}/4 images for '{word}'.")
        return paths

    def clear_cache(self) -> None:
        """Delete all cached images."""
        import shutil
        if os.path.isdir(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)

    def cache_size_mb(self) -> float:
        """Return total cache size in megabytes."""
        total = sum(
            os.path.getsize(os.path.join(self.cache_dir, f))
            for f in os.listdir(self.cache_dir)
            if os.path.isfile(os.path.join(self.cache_dir, f))
        )
        return round(total / 1_048_576, 2)


