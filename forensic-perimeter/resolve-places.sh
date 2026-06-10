#!/usr/bin/env bash
# Resolve Google Maps links to place name + coordinates.
# Usage: ./resolve-places.sh <url1> [url2] ...
# Output: TSV lines: name\tlat,lng

set -euo pipefail

resolve_url() {
    local url="$1"

    # If short URL, follow redirect to get full URL
    if [[ "$url" == *"maps.app.goo.gl"* ]] || [[ "$url" == *"goo.gl/maps"* ]]; then
        url=$(curl -sI "$url" | grep -i '^location:' | tr -d '\r' | cut -d' ' -f2-)
        if [[ -z "$url" ]]; then
            echo "ERROR: could not resolve short URL: $1" >&2
            return 1
        fi
    fi

    # Extract place name from /place/Name+Here/ pattern
    local name
    name=$(echo "$url" | grep -oE '/place/[^/]+' | head -1 | sed 's|/place/||')
    if [[ -z "$name" ]]; then
        echo "ERROR: no place name found in URL: $url" >&2
        return 1
    fi
    # URL-decode the name (+ to space, %XX to char)
    name=$(python3 -c "import sys, urllib.parse; print(urllib.parse.unquote_plus(sys.argv[1]))" "$name")

    # Extract coordinates from !3d<lat>!4d<lng>
    local coords
    coords=$(python3 -c "
import sys, re
url = sys.argv[1]
m = re.findall(r'!3d(-?[\d.]+)!4d(-?[\d.]+)', url)
if m:
    lat, lng = m[-1]
    print(f'{lat},{lng}')
else:
    # Fallback: try @lat,lng pattern
    m2 = re.search(r'@(-?[\d.]+),(-?[\d.]+)', url)
    if m2:
        print(f'{m2.group(1)},{m2.group(2)}')
" "$url")

    if [[ -z "$coords" ]]; then
        echo "ERROR: no coordinates found in URL: $url" >&2
        return 1
    fi

    printf '%s\t%s\n' "$name" "$coords"
}

if [[ $# -eq 0 ]]; then
    echo "Usage: $0 <google-maps-url> [url2] ..." >&2
    exit 1
fi

for url in "$@"; do
    resolve_url "$url"
done
