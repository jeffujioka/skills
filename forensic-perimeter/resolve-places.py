#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests"]
# ///
"""Resolve Google Maps links to place name + coordinates."""

import argparse
import getpass
import os
import re
import sys
import tomllib
import urllib.parse
from pathlib import Path

import requests

def _config_path() -> Path:
    return Path.home() / ".config" / "forensic-perimeter" / "config.toml"


def _get_api_key() -> str | None:
    """Get Google Geocoding API key.

    Precedence: GOOGLE_GEOCODING_API_KEY env var > config.toml > None.
    """
    key = os.environ.get("GOOGLE_GEOCODING_API_KEY")
    if key:
        return key

    config_path = _config_path()
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        key = config.get("google", {}).get("api_key")
        if key:
            return key

    print(
        "ERROR: No Google Geocoding API key found.\n"
        "Set GOOGLE_GEOCODING_API_KEY env var or run:\n"
        "  resolve-places.py --setup",
        file=sys.stderr,
    )
    return None


def resolve_short_url(url: str) -> str | None:
    """Follow redirects for short URLs (maps.app.goo.gl, goo.gl/maps).

    Returns the final URL after redirects, or None on error.
    Non-short URLs are returned unchanged.
    """
    if "maps.app.goo.gl" not in url and "goo.gl/maps" not in url:
        return url

    try:
        resp = requests.head(url, allow_redirects=True, timeout=5)
        resp.raise_for_status()
        return resp.url
    except (requests.RequestException, ConnectionError):
        print(f"ERROR: could not resolve short URL: {url}", file=sys.stderr)
        return None


def extract_place_url(url: str) -> tuple[str, str] | None:
    """Extract (name, coords) from a /place/ URL.

    Returns (name, "lat,lng") or None if extraction fails.
    """
    match = re.search(r"/place/([^/]+)", url)
    if not match:
        return None

    name = urllib.parse.unquote_plus(match.group(1))

    coords_match = re.findall(r"!3d(-?[\d.]+)!4d(-?[\d.]+)", url)
    if coords_match:
        lat, lng = coords_match[-1]
        return (name, f"{lat},{lng}")

    at_match = re.search(r"@(-?[\d.]+),(-?[\d.]+)", url)
    if at_match:
        return (name, f"{at_match.group(1)},{at_match.group(2)}")

    return None


def geocode(query: str) -> str | None:
    """Geocode a text query via Google Geocoding API.

    Returns "lat,lng" string or None on error.
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    try:
        resp = requests.get(
            "https://maps.googleapis.com/maps/api/geocode/json",
            params={"address": query, "key": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"ERROR: geocoding request failed: {e}", file=sys.stderr)
        return None

    if data.get("status") != "OK" or not data.get("results"):
        status = data.get("status", "UNKNOWN")
        print(f"ERROR: geocoding failed for '{query}': {status}", file=sys.stderr)
        return None

    location = data["results"][0]["geometry"]["location"]
    return f"{location['lat']},{location['lng']}"


def resolve_url(url: str) -> tuple[str, str] | None:
    """Resolve any Google Maps URL to (name, "lat,lng").

    Routes:
      - Short URL → follow redirect → resolve final URL
      - /place/ URL → local extraction (no API)
      - /maps/search/ URL → name from query param + Geocoding API
    """
    if "maps.app.goo.gl" in url or "goo.gl/maps" in url:
        resolved = resolve_short_url(url)
        if not resolved:
            return None
        url = resolved

    if "/place/" in url:
        result = extract_place_url(url)
        if result:
            return result
        print(f"ERROR: could not extract coords from place URL: {url}", file=sys.stderr)
        return None

    if "/maps/search/" in url or "/maps?" in url:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        query = params.get("query", params.get("q", [None]))[0]
        if not query:
            print(f"ERROR: no query parameter in search URL: {url}", file=sys.stderr)
            return None
        name = urllib.parse.unquote_plus(query)
        coords = geocode(query)
        if not coords:
            return None
        return (name, coords)

    print(f"ERROR: unrecognized Google Maps URL format: {url}", file=sys.stderr)
    return None


def setup_api_key():
    """Interactive setup: prompt for API key and save to config.toml."""
    config_path = _config_path()

    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        existing = config.get("google", {}).get("api_key")
        if existing:
            masked = f"****{existing[-4:]}"
            confirm = input(f"API key already set ({masked}). Overwrite? [y/N]: ")
            if confirm.lower() != "y":
                print("Aborted.")
                return

    key = getpass.getpass("Google Geocoding API key: ")
    if not key.strip():
        print("ERROR: empty key, aborted.", file=sys.stderr)
        return

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        f.write("[google]\n")
        f.write(f'api_key = "{key.strip()}"\n')

    print(f"Saved to {config_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Resolve Google Maps links to place name + coordinates.",
        epilog="Output: TSV lines with name and coordinates (lat,lng).",
    )
    parser.add_argument(
        "urls",
        nargs="*",
        metavar="URL",
        help="Google Maps URL(s) to resolve",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Configure Google Geocoding API key interactively",
    )

    args = parser.parse_args()

    if args.setup:
        setup_api_key()
        return

    if not args.urls:
        parser.error("at least one URL is required (or use --setup)")

    for url in args.urls:
        result = resolve_url(url)
        if result:
            name, coords = result
            print(f"{name}\t{coords}")


if __name__ == "__main__":
    main()
