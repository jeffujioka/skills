#!/usr/bin/env python3
"""Resolve Google Maps links to place name + coordinates."""

import argparse
import re
import subprocess
import sys
import urllib.parse


def resolve_short_url(url: str) -> str:
    """Follow redirect for short URLs (maps.app.goo.gl, goo.gl/maps)."""
    if "maps.app.goo.gl" not in url and "goo.gl/maps" not in url:
        return url

    try:
        result = subprocess.run(
            ["curl", "-sI", url],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.split("\n"):
            if line.lower().startswith("location:"):
                return line.split(" ", 1)[1].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        pass

    print(f"ERROR: could not resolve short URL: {url}", file=sys.stderr)
    return None


def resolve_url(url: str) -> tuple[str, str] | None:
    """
    Resolve Google Maps URL to (name, coordinates).
    Returns tuple (name, "lat,lng") or None on error.
    """
    # Follow redirects for short URLs
    if "maps.app.goo.gl" in url or "goo.gl/maps" in url:
        resolved = resolve_short_url(url)
        if not resolved:
            return None
        url = resolved

    # Extract place name from /place/Name+Here/ pattern
    match = re.search(r"/place/([^/]+)", url)
    if not match:
        print(f"ERROR: no place name found in URL: {url}", file=sys.stderr)
        return None

    name = match.group(1)
    # URL-decode the name (+ to space, %XX to char)
    name = urllib.parse.unquote_plus(name)

    # Extract coordinates from !3d<lat>!4d<lng>
    coords_match = re.findall(r"!3d(-?[\d.]+)!4d(-?[\d.]+)", url)
    if coords_match:
        lat, lng = coords_match[-1]
        coords = f"{lat},{lng}"
    else:
        # Fallback: try @lat,lng pattern
        coords_match = re.search(r"@(-?[\d.]+),(-?[\d.]+)", url)
        if coords_match:
            coords = f"{coords_match.group(1)},{coords_match.group(2)}"
        else:
            print(f"ERROR: no coordinates found in URL: {url}", file=sys.stderr)
            return None

    return (name, coords)


def main():
    parser = argparse.ArgumentParser(
        description="Resolve Google Maps links to place name + coordinates.",
        epilog="Output: TSV lines with name and coordinates (lat,lng).",
    )
    parser.add_argument(
        "urls",
        nargs="+",
        metavar="URL",
        help="Google Maps URL(s) to resolve",
    )

    args = parser.parse_args()

    for url in args.urls:
        result = resolve_url(url)
        if result:
            name, coords = result
            print(f"{name}\t{coords}")


if __name__ == "__main__":
    main()
