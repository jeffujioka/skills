"""Shared helpers for the dublagem scripts: VoiceStudio HTTP client and ffmpeg audio checks.

Python 3 stdlib only. Needs `ffmpeg` on PATH.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
import uuid
from difflib import SequenceMatcher
from pathlib import Path

# Default VoiceStudio desktop backend address; override with VOICESTUDIO_URL.
BASE_URL = os.environ.get("VOICESTUDIO_URL", "http://127.0.0.1:3900").rstrip("/")

# int16 magnitude counted as clipped: about -0.2 dBFS, where WhatsApp-style
# recordings flatten. Clipped references transfer distortion to the clone.
CLIP_LEVEL = 32000

# Generation can queue behind other jobs and the first call loads a model (a
# cold VoxCPM2 load took about 140 s); one hour bounds a stuck request.
GENERATE_TIMEOUT_S = 3600
# Transcription of a short clip takes seconds; 300 s matches the backend's own
# default ASR timeout.
TRANSCRIBE_TIMEOUT_S = 300


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        die("ffmpeg not found on PATH; install it (macOS: brew install ffmpeg)")


def _request(method: str, path: str, body: bytes | None = None, ctype: str | None = None, timeout: float = 30):
    headers = {"Content-Type": ctype} if ctype else {}
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, method=method, headers=headers)
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:800]
        die(f"{method} {path} returned HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        die(f"VoiceStudio backend not reachable at {BASE_URL} ({exc.reason}); open the VoiceStudio app or set VOICESTUDIO_URL")


def get_json(path: str):
    with _request("GET", path) as resp:
        return json.load(resp)


def multipart(fields: dict[str, str], files: dict[str, Path] | None = None) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    chunks = []
    for name, value in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, path in (files or {}).items():
        chunks.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{path.name}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n".encode()
        )
        chunks.append(path.read_bytes() + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def post_form(path: str, fields: dict[str, str], files: dict[str, Path] | None = None, timeout: float = 60) -> bytes:
    body, ctype = multipart(fields, files)
    with _request("POST", path, body, ctype, timeout) as resp:
        return resp.read()


def transcribe(audio: Path, language: str) -> str:
    raw = post_form("/transcribe", {"language": language}, {"audio": audio}, TRANSCRIBE_TIMEOUT_S)
    return json.loads(raw).get("text", "").strip()


def ffmpeg(*args: str) -> str:
    """Run ffmpeg, return stderr (where filters such as astats report)."""
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        die(f"ffmpeg failed: {proc.stderr.strip()[-800:]}")
    return proc.stderr


def to_wav(src: Path, dest: Path, start: float | None = None, end: float | None = None) -> None:
    """Decode any ffmpeg-readable audio to 48 kHz mono 16-bit WAV, optionally trimmed."""
    trim = []
    if start is not None:
        trim += ["-ss", f"{start:.3f}"]
    if end is not None:
        trim += ["-to", f"{end:.3f}"]
    ffmpeg("-v", "error", "-y", "-i", str(src), *trim, "-ac", "1", "-ar", "48000", "-sample_fmt", "s16", str(dest))


def noise_floor_db(path: Path) -> float:
    out = ffmpeg("-v", "info", "-i", str(path), "-af",
                 "astats=measure_overall=Noise_floor:measure_perchannel=none", "-f", "null", "-")
    match = re.search(r"Noise floor dB:\s*(-?inf|-?[\d.]+)", out)
    if not match:
        die(f"could not measure noise floor of {path}")
    value = match.group(1)
    # Digital silence between words reports -inf; treat it as the cleanest value.
    return -200.0 if "inf" in value else float(value)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\[[^\]]*\]", " ", text)  # bracket tags are never transcribed
    return re.sub(r"[^a-z0-9]+", "", text)


def similarity(expected: str, heard: str) -> float:
    """Character-level match of the line against its transcript, ignoring case,
    accents, spacing and punctuation ("ElevenLabs" vs "Eleven Labs" is 1.0)."""
    return SequenceMatcher(None, _norm(expected), _norm(heard)).ratio()
