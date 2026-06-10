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
        "  resolve-places.py setup",
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


REVERSE_RADII = [10, 20, 50, 100, 150]


def reverse_geocode(lat: float, lng: float) -> tuple[str, str] | None:
    """Reverse geocode coordinates via Google Places Nearby Search API.

    Tries escalating radii (10m, 20m, 50m, 100m, 150m) until a result is found.
    Returns (place_name, "lat,lng") or None if no place found at any radius.
    """
    api_key = _get_api_key()
    if not api_key:
        return None

    for radius in REVERSE_RADII:
        try:
            resp = requests.post(
                "https://places.googleapis.com/v1/places:searchNearby",
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": api_key,
                    "X-Goog-FieldMask": "places.displayName,places.location,places.types",
                },
                json={
                    "locationRestriction": {
                        "circle": {
                            "center": {"latitude": lat, "longitude": lng},
                            "radius": float(radius),
                        }
                    },
                    "maxResultCount": 1,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"ERROR: reverse geocoding request failed: {e}", file=sys.stderr)
            return None

        places = data.get("places", [])
        if places:
            name = places[0]["displayName"]["text"]
            location = places[0]["location"]
            return (name, f"{location['latitude']},{location['longitude']}")

    print(f"ERROR: no place found near {lat},{lng} (max radius {REVERSE_RADII[-1]}m)", file=sys.stderr)
    return None


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


_COORD_PATTERN = re.compile(r"^-?\d+\.?\d*,-?\d+\.?\d*$")


def resolve_input(arg: str, reverse: bool = False) -> tuple[str, str] | None:
    """Resolve any input (URL or plain name) to (name, "lat,lng").

    If reverse=True and arg matches "lat,lng", does reverse geocoding.
    If arg starts with http, delegates to resolve_url().
    Otherwise, treats arg as a place name and geocodes it.
    """
    if reverse and _COORD_PATTERN.match(arg.strip()):
        lat, lng = arg.strip().split(",")
        return reverse_geocode(float(lat), float(lng))

    if arg.startswith("http"):
        return resolve_url(arg)

    coords = geocode(arg)
    if not coords:
        return None
    return (arg, coords)


def format_results(results: list[dict], fmt: str = "tsv", gen_link: bool = False) -> str:
    """Format a list of result dicts into the specified output format.

    Each result dict has: name, lat, lng, error (None if success).
    """
    import csv
    import io
    import json

    if fmt == "json":
        entries = []
        for r in results:
            entry = {"name": r["name"], "lat": r["lat"], "lng": r["lng"]}
            if r["error"]:
                entry["error"] = r["error"]
            if gen_link and r["lat"] is not None:
                name_encoded = urllib.parse.quote_plus(r["name"])
                entry["link"] = f"https://www.google.com/maps/place/{name_encoded}/@{r['lat']},{r['lng']},17z"
            entries.append(entry)
        return json.dumps(entries, ensure_ascii=False, indent=2)

    # TSV and CSV: skip errors
    ok_results = [r for r in results if r["error"] is None]

    if fmt == "csv":
        buf = io.StringIO(newline="")
        headers = ["name", "lat", "lng"]
        if gen_link:
            headers.append("link")
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(headers)
        for r in ok_results:
            row = [r["name"], r["lat"], r["lng"]]
            if gen_link:
                name_encoded = urllib.parse.quote_plus(r["name"])
                row.append(f"https://www.google.com/maps/place/{name_encoded}/@{r['lat']},{r['lng']},17z")
            writer.writerow(row)
        return buf.getvalue().rstrip("\n")

    # TSV (default)
    lines = []
    for r in ok_results:
        parts = [r["name"], f"{r['lat']},{r['lng']}"]
        if gen_link:
            name_encoded = urllib.parse.quote_plus(r["name"])
            parts.append(f"https://www.google.com/maps/place/{name_encoded}/@{r['lat']},{r['lng']},17z")
        lines.append("\t".join(str(p) for p in parts))
    return "\n".join(lines)


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


def resolve_format(explicit_fmt: str | None, output_path: str | None) -> str:
    """Determine output format: explicit_fmt > extension inference > tsv."""
    if explicit_fmt:
        return explicit_fmt
    if output_path:
        ext = Path(output_path).suffix.lower()
        if ext == ".json":
            return "json"
        if ext == ".csv":
            return "csv"
    return "tsv"


def read_inputs(positional: list[str], input_file: str | None) -> list[str]:
    """Combine positional args and --input file/stdin into a flat list."""
    lines = list(positional)
    if input_file == "-":
        lines.extend(line.rstrip("\n") for line in sys.stdin if line.strip())
    elif input_file:
        with open(input_file) as f:
            lines.extend(line.rstrip("\n") for line in f if line.strip())
    return lines


def write_output(content: str, output_path: str | None) -> None:
    """Write content to file or stdout."""
    if not output_path:
        if content:
            print(content)
        return
    Path(output_path).write_text(content + "\n" if content else "", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Resolve Google Maps links or place names to coordinates.",
        epilog="Output: TSV lines with name and coordinates (lat,lng) by default.",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        metavar="INPUT",
        help="Google Maps URL(s) or place name(s) to resolve",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Configure Google Geocoding API key interactively",
    )
    parser.add_argument(
        "--format",
        choices=["tsv", "csv", "json"],
        default="tsv",
        dest="fmt",
        help="Output format (default: tsv)",
    )
    parser.add_argument(
        "--link",
        action="store_true",
        help="Include Google Maps link in output",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Reverse geocode: resolve coordinates to place names (via Places Nearby Search)",
    )

    args = parser.parse_args()

    if args.setup:
        setup_api_key()
        return

    if not args.inputs:
        parser.error("at least one URL or place name is required (or use --setup)")

    results = []
    for arg in args.inputs:
        result = resolve_input(arg, reverse=args.reverse)
        if result:
            name, coords = result
            lat, lng = coords.split(",")
            results.append({"name": name, "lat": float(lat), "lng": float(lng), "error": None})
        else:
            results.append({"name": arg, "lat": None, "lng": None, "error": "FAILED"})

    output = format_results(results, fmt=args.fmt, gen_link=args.link)
    if output:
        print(output)

    if any(r["error"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
