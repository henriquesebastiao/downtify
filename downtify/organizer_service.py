"""Downtify Organizer Service.

Background-Thread der innerhalb des Downtify-Containers läuft.
Übernimmt:
- Auto-Organisation neu heruntergeladener Songs aus /downloads
- Scanner-Ordner: importiert extern beschaffte Songs (mit AudD-Erkennung)
- Multi-Source Genre-Lookup (Spotify → Deezer → Last.fm → MusicBrainz → Sprache)
- Single Source of Truth: eigene SQLite (/data/organizer.db)
- Best-of-Logik mit automatischer Album-Migration

Konfiguration ausschließlich via Umgebungsvariablen.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import sqlite3
import threading
import time
import unicodedata
from pathlib import Path
from typing import Optional

import requests
from mutagen import File as MutagenFile

# ── Konfiguration ─────────────────────────────────────────────────────────────

DOWNLOAD_DIR  = Path(os.getenv("DOWNLOAD_DIR",  "/downloads"))
MUSIK_DIR     = Path(os.getenv("MUSIK_DIR",     "/musik"))
SCANNER_DIR   = Path(os.getenv("SCANNER_DIR",   "/scanner"))
DATA_DIR      = Path(os.getenv("DATA_DIR",      "/data"))
DB_PATH       = DATA_DIR / "organizer.db"

POLL_INTERVAL = int(os.getenv("ORGANIZER_POLL_INTERVAL", "60"))
FILE_COOLDOWN = int(os.getenv("ORGANIZER_FILE_COOLDOWN", "30"))

SPOTIFY_CLIENT_ID     = os.getenv("CLIENT_ID",            "")
SPOTIFY_CLIENT_SECRET = os.getenv("CLIENT_SECRET",        "")
LASTFM_API_KEY        = os.getenv("LASTFM_API_KEY",       "")
AUDD_API_TOKEN        = os.getenv("AUDD_API_TOKEN",       "")

ENABLE_DOWNLOAD_WATCHER = os.getenv("ENABLE_DOWNLOAD_WATCHER", "true").lower() == "true"
ENABLE_SCANNER          = os.getenv("ENABLE_SCANNER",          "true").lower() == "true"

DEFAULT_FOLDER = "Sonstiges"
BESTOF_MIN     = 2

AUDIO_EXT = {".mp3", ".m4a", ".flac", ".ogg", ".wav", ".aac", ".opus"}

MB_HEADERS = {"User-Agent": "DowntifyOrganizer/1.0 (self-hosted-nas)"}

log = logging.getLogger("downtify.organizer")

# ── Genre/Region Mapping ──────────────────────────────────────────────────────

# Reihenfolge zählt: spezifischere/sprachliche Patterns zuerst.
GENRE_RULES = [
    # Sprache/Region (höchste Priorität)
    ("manele",              "Rumänisch"),
    ("romanian",            "Rumänisch"),
    ("albanian",            "Albanisch"),
    ("shqip",               "Albanisch"),
    ("kosovan",             "Albanisch"),
    ("tallava",             "Albanisch"),
    ("turkish",             "Türkisch"),
    ("turk pop",            "Türkisch"),
    ("arabesk",             "Türkisch"),
    ("arabic",              "Arabisch"),
    ("arab pop",            "Arabisch"),
    ("rai",                 "Arabisch"),
    ("khaleeji",            "Arabisch"),
    ("levantine",           "Arabisch"),
    ("russian",             "Russia"),
    ("ukrainian",           "Russia"),
    ("greek",               "Griechisch"),
    ("balkan",              "Serbisch"),
    ("serbian",             "Serbisch"),
    ("croatian",            "Serbisch"),
    ("bosnian",             "Serbisch"),
    ("k-pop",               "K-Pop"),
    ("kpop",                "K-Pop"),
    ("j-pop",               "Japanisch"),
    ("jpop",                "Japanisch"),

    # Latin Familie
    ("reggaeton",           "Latin"),
    ("trap latino",         "Latin"),
    ("latin pop",           "Latin"),
    ("cumbia",              "Latin"),
    ("salsa",               "Latin"),
    ("bachata",             "Latin"),
    ("merengue",            "Latin"),
    ("dembow",              "Latin"),
    ("latin",               "Latin"),

    # Stil-Genres
    ("phonk",               "Phonk"),
    ("goa",                 "Goa"),
    ("psytrance",           "Goa"),
    ("psy trance",          "Goa"),
    ("psychedelic trance",  "Goa"),

    # Heavy/Drop
    ("dubstep",             "Drop"),
    ("riddim",              "Drop"),
    ("bass house",          "Drop"),
    ("hardstyle",           "Drop"),
    ("rawstyle",            "Drop"),
    ("future bass",         "Drop"),
    ("brostep",             "Drop"),

    # House
    ("deep house",          "House"),
    ("tech house",          "House"),
    ("progressive house",   "House"),
    ("afro house",          "House"),
    ("future house",        "House"),
    ("house",               "House"),
    ("electro",             "House"),

    # Party/Dance
    ("eurodance",           "Party"),
    ("dance pop",           "Party"),
    ("club",                "Party"),
    ("party",               "Party"),

    # Rap vor HipHop (German Rap, French Rap etc. → Rap)
    ("deutschrap",          "Rap"),
    ("german rap",          "Rap"),
    ("french rap",          "Rap"),
    ("uk rap",              "Rap"),
    ("italian rap",         "Rap"),
    ("rap",                 "Rap"),

    # HipHop
    ("hip hop",             "HipHop"),
    ("hip-hop",             "HipHop"),
    ("hiphop",              "HipHop"),
    ("trap",                "HipHop"),
    ("drill",               "HipHop"),
    ("boom bap",            "HipHop"),

    # Rock/Metal
    ("rock",                "Rock"),
    ("metal",               "Rock"),
    ("punk",                "Rock"),
    ("grunge",              "Rock"),

    # Classic/Cinematic
    ("classical",           "Classic Oldies"),
    ("cinematic",           "Classic Oldies"),
    ("soundtrack",          "Classic Oldies"),
    ("film score",          "Classic Oldies"),
    ("oldies",              "Classic Oldies"),
    ("rock and roll",       "Classic Oldies"),

    # R&B/Soul
    ("r&b",                 "R&B"),
    ("rnb",                 "R&B"),
    ("soul",                "R&B"),
    ("funk",                "R&B"),

    # Pop (generisch, am Schluss)
    ("dance",               "Party"),
    ("edm",                 "House"),
    ("electronic",          "House"),
    ("pop",                 "Pop"),
]

COUNTRY_TO_FOLDER = {
    "RO": "Rumänisch",
    "AL": "Albanisch", "XK": "Albanisch", "MK": "Albanisch",
    "RU": "Russia", "UA": "Russia", "BY": "Russia",
    "SA": "Arabisch", "AE": "Arabisch", "EG": "Arabisch", "MA": "Arabisch",
    "LB": "Arabisch", "JO": "Arabisch", "SY": "Arabisch", "IQ": "Arabisch",
    "DZ": "Arabisch", "TN": "Arabisch", "LY": "Arabisch", "YE": "Arabisch",
    "PS": "Arabisch", "BH": "Arabisch", "KW": "Arabisch", "OM": "Arabisch",
    "QA": "Arabisch", "SD": "Arabisch",
    "TR": "Türkisch",
    "GR": "Griechisch",
    "RS": "Serbisch", "ME": "Serbisch", "BA": "Serbisch", "HR": "Serbisch",
    "BR": "Latin", "AR": "Latin", "MX": "Latin", "CO": "Latin", "CL": "Latin",
    "PE": "Latin", "PR": "Latin", "DO": "Latin", "VE": "Latin", "CU": "Latin",
    "ES": "Latin",
    "KR": "K-Pop", "JP": "Japanisch",
}

ETHNIC_FOLDERS = {
    "Rumänisch", "Albanisch", "Türkisch", "Arabisch",
    "Russia", "Griechisch", "Serbisch", "K-Pop", "Latin", "Japanisch",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _sanitize(name: str, fallback: str = "Sonstiges") -> str:
    if not name or not name.strip():
        return fallback
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    name = name.strip(". ")
    return name or fallback


def _primary_artist(raw: str) -> str:
    if not raw:
        return ""
    s = raw.strip()
    for sep in ["/", ";"]:
        if sep in s:
            return s.split(sep)[0].strip()
    for marker in [" feat. ", " ft. ", " feat ", " ft ", " featuring "]:
        low = s.lower()
        if marker in low:
            return s[: low.index(marker)].strip()
    for sep in [" & ", " x "]:
        if sep.lower() in s.lower():
            return s[: s.lower().index(sep.lower())].strip()
    if "," in s:
        return s.split(",")[0].strip()
    return s


def _is_stable(path: Path, cooldown: int) -> bool:
    """Datei nicht mehr verändert in den letzten ``cooldown`` Sekunden?"""
    try:
        return (time.time() - path.stat().st_mtime) >= cooldown
    except Exception:
        return False


def _read_tags(path: Path) -> dict:
    result = {"title": None, "artist": None, "album": None, "spotify_id": None}
    try:
        f = MutagenFile(str(path), easy=True)
        if f is None:
            return result
        result["title"]  = (f.get("title")  or [None])[0]
        result["artist"] = (f.get("artist") or [None])[0]
        result["album"]  = (f.get("album")  or [None])[0]
        # spotify_id steht häufig in TXXX:SPOTIFY_ID (id3) oder einem custom-tag
        for k in ("spotify_id", "spotifyid", "spotify"):
            v = f.get(k)
            if v:
                result["spotify_id"] = v[0]
                break
    except Exception as e:
        log.warning(f"Tags nicht lesbar für {path.name}: {e}")
    return result


def _match_genre_rules(genres: list) -> Optional[str]:
    if not genres:
        return None
    joined = " | ".join(g.lower() for g in genres)
    for keyword, folder in GENRE_RULES:
        if keyword in joined:
            return folder
    return None


def _detect_script(text: str) -> Optional[str]:
    """Erkennt Skript/Sprache anhand der Zeichen im Titel."""
    if not text:
        return None
    for ch in text:
        code = ord(ch)
        if 0x0400 <= code <= 0x04FF:  # Kyrillisch
            return "Russia"
        if 0x0600 <= code <= 0x06FF:  # Arabisch
            return "Arabisch"
        if 0x0370 <= code <= 0x03FF:  # Griechisch
            return "Griechisch"
        if 0xAC00 <= code <= 0xD7AF:  # Hangul (Koreanisch)
            return "K-Pop"
        if 0x3040 <= code <= 0x30FF:  # Hiragana/Katakana
            return "Japanisch"
    return None


# ── Datenbank ─────────────────────────────────────────────────────────────────

class OrganizerDB:
    def __init__(self, path: Path):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.lock:
            self.conn.executescript("""
                PRAGMA journal_mode=WAL;
                PRAGMA wal_autocheckpoint=200;

                CREATE TABLE IF NOT EXISTS processed (
                    file_id      TEXT PRIMARY KEY,    -- "filename:size:mtime" oder spotify_id
                    spotify_id   TEXT,
                    source       TEXT,                -- "download" / "scanner"
                    genre        TEXT,
                    artist       TEXT,
                    album        TEXT,
                    title        TEXT,
                    musik_path   TEXT,
                    processed_at INTEGER
                );
                CREATE INDEX IF NOT EXISTS idx_processed_spotify
                    ON processed(spotify_id);

                CREATE TABLE IF NOT EXISTS artist_genres_cache (
                    artist       TEXT PRIMARY KEY,
                    genres_csv   TEXT,
                    looked_up_at INTEGER
                );
                CREATE TABLE IF NOT EXISTS artist_country_cache (
                    artist       TEXT PRIMARY KEY,
                    country      TEXT,
                    looked_up_at INTEGER
                );
            """)
            self.conn.commit()

    def is_processed(self, file_id: str, spotify_id: Optional[str] = None) -> bool:
        with self.lock:
            row = self.conn.execute(
                "SELECT 1 FROM processed WHERE file_id = ? OR (spotify_id IS NOT NULL AND spotify_id = ?)",
                (file_id, spotify_id or ""),
            ).fetchone()
            return row is not None

    def mark_processed(self, file_id, spotify_id, source, genre, artist, album, title, musik_path) -> None:
        with self.lock:
            self.conn.execute(
                """INSERT OR REPLACE INTO processed
                   (file_id, spotify_id, source, genre, artist, album, title, musik_path, processed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (file_id, spotify_id, source, genre, artist, album, title,
                 musik_path, int(time.time())),
            )
            self.conn.commit()

    def get_cached_genres(self, artist: str) -> Optional[list]:
        with self.lock:
            row = self.conn.execute(
                "SELECT genres_csv FROM artist_genres_cache WHERE artist=?",
                (artist,)
            ).fetchone()
        if row is None:
            return None
        return [g for g in row[0].split("|") if g]

    def cache_genres(self, artist: str, genres: list) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO artist_genres_cache VALUES (?, ?, ?)",
                (artist, "|".join(genres or []), int(time.time())),
            )
            self.conn.commit()

    def get_cached_country(self, artist: str) -> Optional[str]:
        with self.lock:
            row = self.conn.execute(
                "SELECT country FROM artist_country_cache WHERE artist=?",
                (artist,)
            ).fetchone()
        return row[0] if row else None

    def cache_country(self, artist: str, country: str) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO artist_country_cache VALUES (?, ?, ?)",
                (artist, country or "", int(time.time())),
            )
            self.conn.commit()

    def shutdown(self) -> None:
        with self.lock:
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            self.conn.close()


# ── Spotify API ──────────────────────────────────────────────────────────────

class SpotifyClient:
    def __init__(self):
        self.token: Optional[str] = None
        self.expiry: float = 0.0

    def get_token(self) -> Optional[str]:
        if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
            return None
        if self.token and time.time() < self.expiry - 60:
            return self.token
        try:
            r = requests.post(
                "https://accounts.spotify.com/api/token",
                data={"grant_type": "client_credentials"},
                auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
                timeout=10,
            )
            if r.status_code == 200:
                d = r.json()
                self.token  = d["access_token"]
                self.expiry = time.time() + d.get("expires_in", 3600)
                return self.token
        except Exception as e:
            log.warning(f"Spotify Token Fehler: {e}")
        return None

    def lookup_genres(self, artist: str, title: str) -> list:
        token = self.get_token()
        if not token:
            return []
        h = {"Authorization": f"Bearer {token}"}
        try:
            # Strategie 1: direkt Artist suchen
            r = requests.get(
                "https://api.spotify.com/v1/search",
                params={"q": artist, "type": "artist", "limit": 1},
                headers=h, timeout=10,
            )
            if r.status_code == 200:
                items = r.json().get("artists", {}).get("items", [])
                if items and items[0].get("genres"):
                    return items[0]["genres"]
            # Strategie 2: über Track
            for q in [f"track:{title} artist:{artist}", f"{artist} {title}"]:
                r = requests.get(
                    "https://api.spotify.com/v1/search",
                    params={"q": q, "type": "track", "limit": 1},
                    headers=h, timeout=10,
                )
                if r.status_code != 200:
                    continue
                tracks = r.json().get("tracks", {}).get("items", [])
                if not tracks:
                    continue
                artist_id = tracks[0]["artists"][0]["id"]
                r2 = requests.get(
                    f"https://api.spotify.com/v1/artists/{artist_id}",
                    headers=h, timeout=10,
                )
                if r2.status_code == 200:
                    return r2.json().get("genres", []) or []
        except Exception as e:
            log.warning(f"  Spotify-Fehler: {e}")
        return []


# ── Deezer API (kein Auth nötig) ─────────────────────────────────────────────

def lookup_deezer(artist: str, title: str) -> list:
    """Deezer Track suchen → Album-Genre auflösen. Kein API-Key nötig."""
    try:
        r = requests.get(
            "https://api.deezer.com/search",
            params={"q": f'artist:"{artist}" track:"{title}"', "limit": 1},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        items = r.json().get("data", [])
        if not items:
            return []
        album_id = items[0].get("album", {}).get("id")
        if not album_id:
            return []
        r2 = requests.get(f"https://api.deezer.com/album/{album_id}", timeout=10)
        if r2.status_code != 200:
            return []
        album = r2.json()
        genres = album.get("genres", {}).get("data", [])
        return [g["name"] for g in genres if g.get("name")]
    except Exception as e:
        log.warning(f"  Deezer-Fehler: {e}")
    return []


# ── Last.fm API ──────────────────────────────────────────────────────────────

def lookup_lastfm(artist: str) -> list:
    if not LASTFM_API_KEY:
        return []
    try:
        r = requests.get(
            "https://ws.audioscrobbler.com/2.0/",
            params={
                "method":  "artist.getTopTags",
                "artist":  artist,
                "api_key": LASTFM_API_KEY,
                "format":  "json",
                "autocorrect": 1,
            },
            timeout=10,
        )
        if r.status_code != 200:
            return []
        tags = r.json().get("toptags", {}).get("tag", [])
        return [t["name"] for t in tags if t.get("name")][:10]
    except Exception as e:
        log.warning(f"  Last.fm-Fehler: {e}")
    return []


# ── MusicBrainz ──────────────────────────────────────────────────────────────

def lookup_musicbrainz_artist(artist: str) -> tuple[Optional[str], list]:
    """Gibt (country, tags) zurück."""
    try:
        r = requests.get(
            "https://musicbrainz.org/ws/2/artist/",
            params={"query": f'artist:"{artist}"', "fmt": "json", "limit": 1},
            headers=MB_HEADERS, timeout=12,
        )
        time.sleep(1.1)  # Rate-Limit MB: 1 req/sec
        if r.status_code != 200:
            return None, []
        items = r.json().get("artists", [])
        if not items:
            return None, []
        a = items[0]
        country = a.get("country")
        tags    = [t["name"] for t in a.get("tags", []) if t.get("name")]
        genres  = [g["name"] for g in a.get("genres", []) if g.get("name")]
        return country, tags + genres
    except Exception as e:
        log.warning(f"  MusicBrainz-Fehler: {e}")
    return None, []


# ── AudD Fingerprinting (für Scanner) ────────────────────────────────────────

def audd_identify(path: Path) -> Optional[dict]:
    """Identifiziert eine Datei via AudD. Gibt {artist, title, album} zurück."""
    if not AUDD_API_TOKEN:
        return None
    try:
        with open(path, "rb") as f:
            r = requests.post(
                "https://api.audd.io/",
                data={"api_token": AUDD_API_TOKEN, "return": "spotify"},
                files={"file": f},
                timeout=30,
            )
        if r.status_code != 200:
            return None
        result = r.json().get("result")
        if not result:
            return None
        return {
            "artist":     result.get("artist"),
            "title":      result.get("title"),
            "album":      result.get("album"),
            "spotify_id": (result.get("spotify") or {}).get("id"),
        }
    except Exception as e:
        log.warning(f"  AudD-Fehler: {e}")
    return None


# ── Genre-Ermittlung mit voller Kette ────────────────────────────────────────

class GenreResolver:
    def __init__(self, db: OrganizerDB, spotify: SpotifyClient):
        self.db = db
        self.spotify = spotify

    def resolve(self, artist: str, title: str) -> str:
        if not artist:
            return DEFAULT_FOLDER

        # Cache prüfen
        cached = self.db.get_cached_genres(artist)
        if cached is not None:
            log.info(f"  Genres (cached): {cached or '—'}")
            spotify_genres = cached
        else:
            # Spotify
            spotify_genres = self.spotify.lookup_genres(artist, title)
            log.info(f"  Spotify Genres: {spotify_genres or '—'}")
            if not spotify_genres:
                # Deezer
                deezer_genres = lookup_deezer(artist, title)
                if deezer_genres:
                    log.info(f"  Deezer Genres: {deezer_genres}")
                    spotify_genres = deezer_genres
            if not spotify_genres:
                # Last.fm
                lastfm_genres = lookup_lastfm(artist)
                if lastfm_genres:
                    log.info(f"  Last.fm Tags: {lastfm_genres[:5]}")
                    spotify_genres = lastfm_genres
            self.db.cache_genres(artist, spotify_genres)

        # Ethnische Genres haben absolute Priorität
        f = _match_genre_rules(spotify_genres)
        if f in ETHNIC_FOLDERS:
            return f

        # MusicBrainz Country (mit Cache)
        country = self.db.get_cached_country(artist)
        if country is None:
            country, mb_tags = lookup_musicbrainz_artist(artist)
            self.db.cache_country(artist, country or "")
        else:
            mb_tags = []
        if country and country in COUNTRY_TO_FOLDER:
            log.info(f"  Artist Country: {country}")
            return COUNTRY_TO_FOLDER[country]

        # Stil-basierte Spotify-Rules
        if f:
            return f

        # MusicBrainz Tags
        if mb_tags:
            log.info(f"  MusicBrainz Tags: {mb_tags[:5]}")
            f = _match_genre_rules(mb_tags)
            if f:
                return f

        # Zeichensatz-Detection
        script = _detect_script(title)
        if script:
            log.info(f"  Script-Detection: {script}")
            return script

        return DEFAULT_FOLDER


# ── Path Building & bestof-Migration ─────────────────────────────────────────

def _bestof_folder(artist: str) -> str:
    return f"Best of {artist}"


def _count_album_in_musik(artist: str, album: str) -> tuple[int, list]:
    """Zählt wieviele Songs vom (Artist, Album) bereits in /musik liegen."""
    matches = []
    if not MUSIK_DIR.exists():
        return 0, []
    for genre_dir in MUSIK_DIR.iterdir():
        if not genre_dir.is_dir():
            continue
        artist_dir = genre_dir / artist
        if not artist_dir.is_dir():
            continue
        for sub in artist_dir.iterdir():
            if not sub.is_dir():
                continue
            for f in sub.iterdir():
                if not f.is_file() or f.suffix.lower() not in AUDIO_EXT:
                    continue
                tags = _read_tags(f)
                if _sanitize(tags.get("album") or "", "Unbekannt") == album:
                    matches.append(f)
    return len(matches), matches


def _migrate_to_album(genre: str, artist: str, album: str, existing_files: list) -> None:
    """Verschiebt alle bisher in 'Best of' liegenden Songs ins Album-Verzeichnis."""
    album_dir = MUSIK_DIR / genre / artist / album
    album_dir.mkdir(parents=True, exist_ok=True)
    bestof_dir = MUSIK_DIR / genre / artist / _bestof_folder(artist)

    for src in existing_files:
        if src.parent == album_dir:
            continue
        dst = album_dir / src.name
        ctr = 1
        while dst.exists():
            dst = album_dir / f"{src.stem}_{ctr}{src.suffix}"
            ctr += 1
        try:
            shutil.move(str(src), str(dst))
            log.info(f"  Best of → Album: {src.name}")
        except Exception as e:
            log.warning(f"  Migration fehlgeschlagen {src.name}: {e}")

    # Leeren Best-of-Ordner aufräumen
    try:
        if bestof_dir.exists() and not any(bestof_dir.iterdir()):
            bestof_dir.rmdir()
    except Exception:
        pass


def determine_target_path(genre: str, artist: str, album: str, title: str, ext: str) -> Path:
    """Berechnet Zielpfad inkl. Best-of-Logik + ggf. Migration."""
    existing_count, existing_files = _count_album_in_musik(artist, album)

    # +1 weil der aktuelle Song noch nicht im Filesystem ist
    if existing_count + 1 >= BESTOF_MIN:
        # Album-Ordner: ggf. vorhandene Best-of-Einträge migrieren
        _migrate_to_album(genre, artist, album, existing_files)
        folder = MUSIK_DIR / genre / artist / album
    else:
        folder = MUSIK_DIR / genre / artist / _bestof_folder(artist)

    folder.mkdir(parents=True, exist_ok=True)
    target = folder / (title + ext)
    ctr = 1
    while target.exists():
        target = folder / f"{title}_{ctr}{ext}"
        ctr += 1
    return target


# ── Downtify Monitor DB: filename nullifizieren ───────────────────────────────

def _nullify_monitor_filename(original_path: Path) -> None:
    """
    Setzt filename=NULL in Downtifys downloaded_tracks Tabelle.

    Warum: monitor.py re-downloaded einen Song wenn:
        stored is not None AND not (download_dir / stored).exists()

    Wenn filename=NULL ist, greift stored is not None NICHT → kein Re-Download.
    Der Song bleibt als "erledigt" in der DB – wird nie mehr neu heruntergeladen.
    """
    monitor_db = DATA_DIR / "downtify_monitor.db"
    if not monitor_db.exists():
        return
    try:
        # Relativer Pfad wie er in downloaded_tracks.filename gespeichert ist
        rel = original_path.relative_to(DOWNLOAD_DIR).as_posix()
        conn = sqlite3.connect(str(monitor_db), timeout=10)
        cur = conn.execute(
            "UPDATE downloaded_tracks SET filename = NULL WHERE filename = ?",
            (rel,),
        )
        conn.commit()
        conn.close()
        if cur.rowcount > 0:
            log.info(f"  ✓ Monitor DB: filename nullified ({rel})")
        else:
            log.debug(f"  Monitor DB: kein Eintrag für {rel} gefunden")
    except Exception as e:
        log.warning(f"  Monitor DB Update fehlgeschlagen: {e}")


# ── Datei-Verarbeitung ───────────────────────────────────────────────────────

def _file_id(path: Path, tags: dict) -> str:
    """Eindeutige ID für die Datei (Spotify-ID wenn vorhanden, sonst path+stat)."""
    if tags.get("spotify_id"):
        return f"spotify:{tags['spotify_id']}"
    try:
        st = path.stat()
        return f"file:{path.name}:{st.st_size}"
    except Exception:
        return f"file:{path.name}"


def process_file(
    path: Path,
    source: str,
    db: OrganizerDB,
    resolver: GenreResolver,
    *,
    delete_after_move: bool = False,
) -> bool:
    """
    Verarbeitet eine einzelne Audio-Datei.
    Returns True bei Erfolg, False bei Skip/Error.
    """
    log.info(f"[{source}] Verarbeite: {path.name}")

    tags = _read_tags(path)

    # Scanner: bei fehlenden Tags → AudD Fingerprinting
    if source == "scanner" and (not tags.get("title") or not tags.get("artist")):
        log.info(f"  Tags fehlen, versuche AudD-Erkennung...")
        ident = audd_identify(path)
        if ident:
            log.info(f"  AudD: {ident.get('artist')} – {ident.get('title')}")
            tags["title"]      = tags.get("title")      or ident.get("title")
            tags["artist"]     = tags.get("artist")     or ident.get("artist")
            tags["album"]      = tags.get("album")      or ident.get("album")
            tags["spotify_id"] = tags.get("spotify_id") or ident.get("spotify_id")
        else:
            log.warning(f"  AudD konnte den Song nicht identifizieren")

    file_id = _file_id(path, tags)
    if db.is_processed(file_id, tags.get("spotify_id")):
        log.info(f"  Bereits verarbeitet → skip")
        if delete_after_move:
            try: path.unlink()
            except Exception: pass
        return False

    raw_artist = tags.get("artist") or "Sonstiges"
    artist_p   = _primary_artist(raw_artist)
    title      = _sanitize(tags.get("title")  or path.stem)
    artist     = _sanitize(artist_p, "Sonstiges")
    album      = _sanitize(tags.get("album")  or "Unbekannt", "Unbekannt")

    genre = resolver.resolve(artist_p, tags.get("title") or "")
    genre = _sanitize(genre, DEFAULT_FOLDER)

    log.info(f"  → {genre} / {artist} / {album} / {title}")

    target = determine_target_path(genre, artist, album, title, path.suffix)

    try:
        shutil.move(str(path), str(target))
        log.info(f"  ✓ {target.relative_to(MUSIK_DIR)}")
    except Exception as e:
        log.error(f"  ✗ Move fehlgeschlagen: {e}")
        return False

    # Downtify Monitor DB updaten → verhindert Re-Download
    if source == "download":
        _nullify_monitor_filename(path)

    db.mark_processed(
        file_id, tags.get("spotify_id"), source,
        genre, artist, album, title, str(target),
    )
    return True


# ── Watcher-Threads ──────────────────────────────────────────────────────────

def _scan_dir(directory: Path, db: OrganizerDB, resolver: GenreResolver,
              source: str, delete_after_move: bool) -> int:
    if not directory.exists():
        return 0
    files = [
        p for p in directory.rglob("*")
        if p.is_file()
        and p.suffix.lower() in AUDIO_EXT
        and _is_stable(p, FILE_COOLDOWN)
        and "@eaDir" not in p.parts
    ]
    if not files:
        return 0

    log.info(f"[{source}] Gefunden: {len(files)} Datei(en)")
    success = 0
    for f in files:
        try:
            if process_file(f, source, db, resolver, delete_after_move=delete_after_move):
                success += 1
        except Exception as e:
            log.error(f"Fehler bei {f.name}: {e}")
    return success


def _download_watcher_loop(db: OrganizerDB, resolver: GenreResolver, stop: threading.Event) -> None:
    log.info(f"Download-Watcher: {DOWNLOAD_DIR} → {MUSIK_DIR}")
    while not stop.is_set():
        try:
            _scan_dir(DOWNLOAD_DIR, db, resolver, "download", delete_after_move=False)
        except Exception as e:
            log.error(f"Download-Scan Fehler: {e}")
        stop.wait(POLL_INTERVAL)


def _scanner_loop(db: OrganizerDB, resolver: GenreResolver, stop: threading.Event) -> None:
    log.info(f"Scanner-Watcher: {SCANNER_DIR} → {MUSIK_DIR}")
    while not stop.is_set():
        try:
            _scan_dir(SCANNER_DIR, db, resolver, "scanner", delete_after_move=True)
        except Exception as e:
            log.error(f"Scanner Fehler: {e}")
        stop.wait(POLL_INTERVAL)


# ── Public API ───────────────────────────────────────────────────────────────

class OrganizerService:
    def __init__(self):
        MUSIK_DIR.mkdir(parents=True, exist_ok=True)
        SCANNER_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.db = OrganizerDB(DB_PATH)
        self.spotify = SpotifyClient()
        self.resolver = GenreResolver(self.db, self.spotify)
        self.stop = threading.Event()
        self.threads: list[threading.Thread] = []

    def start(self) -> None:
        log.info("=" * 60)
        log.info("Downtify Organizer Service startet")
        log.info(f"Download-Watcher: {'aktiv' if ENABLE_DOWNLOAD_WATCHER else 'deaktiviert'}")
        log.info(f"Scanner:          {'aktiv' if ENABLE_SCANNER          else 'deaktiviert'}")
        log.info(f"Spotify:          {'verbunden' if SPOTIFY_CLIENT_ID else 'fehlt (CLIENT_ID nicht gesetzt)'}")
        log.info(f"Last.fm:          {'verbunden' if LASTFM_API_KEY    else 'fehlt'}")
        log.info(f"AudD:             {'verbunden' if AUDD_API_TOKEN    else 'fehlt'}")
        log.info(f"Polling:          {POLL_INTERVAL}s | Cooldown: {FILE_COOLDOWN}s")
        log.info("=" * 60)

        if ENABLE_DOWNLOAD_WATCHER:
            t = threading.Thread(
                target=_download_watcher_loop,
                args=(self.db, self.resolver, self.stop),
                name="organizer-downloads",
                daemon=True,
            )
            t.start()
            self.threads.append(t)

        if ENABLE_SCANNER:
            t = threading.Thread(
                target=_scanner_loop,
                args=(self.db, self.resolver, self.stop),
                name="organizer-scanner",
                daemon=True,
            )
            t.start()
            self.threads.append(t)

    def shutdown(self) -> None:
        log.info("Organizer Shutdown...")
        self.stop.set()
        self.db.shutdown()


_singleton: Optional[OrganizerService] = None


def start_organizer() -> OrganizerService:
    """Wird aus main.py beim Startup aufgerufen."""
    global _singleton
    if _singleton is not None:
        return _singleton
    _singleton = OrganizerService()
    _singleton.start()
    return _singleton


def stop_organizer() -> None:
    """Wird aus main.py beim Shutdown aufgerufen."""
    global _singleton
    if _singleton is not None:
        _singleton.shutdown()
        _singleton = None
