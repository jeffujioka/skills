"""Tests for resolve-places.py — all HTTP mocked, no network calls."""

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import patch

import responses


def _load_module():
    """Load resolve-places.py as a Python module."""
    script_path = Path(__file__).resolve().parent.parent / "resolve-places.py"
    spec = importlib.util.spec_from_file_location("resolve_places", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Short URL resolution
# ---------------------------------------------------------------------------


@responses.activate
def test_resolve_short_url_follows_redirect():
    """Short URL (maps.app.goo.gl) resolved via HEAD with redirects."""
    mod = _load_module()
    short_url = "https://maps.app.goo.gl/abc123"
    final_url = (
        "https://www.google.com/maps/place/Kaufpark+Eich/"
        "@52.5366048,13.5732627,17z/data=!3m1!4b1!4m6"
    )

    responses.add(
        responses.HEAD,
        short_url,
        status=302,
        headers={"Location": final_url},
    )
    responses.add(responses.HEAD, final_url, status=200)

    result = mod.resolve_short_url(short_url)
    assert result == final_url


@responses.activate
def test_resolve_short_url_returns_none_on_failure():
    """Network error during short URL resolution returns None."""
    mod = _load_module()
    short_url = "https://maps.app.goo.gl/broken"
    responses.add(
        responses.HEAD,
        short_url,
        body=ConnectionError("Network error"),
    )

    result = mod.resolve_short_url(short_url)
    assert result is None


def test_non_short_url_passes_through():
    """Non-short URLs returned unchanged (no HTTP call)."""
    mod = _load_module()
    url = "https://www.google.com/maps/place/Foo/@1.0,2.0,17z"
    assert mod.resolve_short_url(url) == url


# ---------------------------------------------------------------------------
# /place/ URL extraction
# ---------------------------------------------------------------------------


def test_extract_place_url_with_3d4d_coords():
    """Extracts name + coords from !3d...!4d... pattern."""
    mod = _load_module()
    url = (
        "https://www.google.com/maps/place/Kaufpark+Eich/"
        "@52.5366048,13.5732627,17z/data=!3m1!4b1!4m6!3m5!1s0x0"
        "!3d52.5366048!4d13.5732627"
    )
    assert mod.extract_place_url(url) == ("Kaufpark Eich", "52.5366048,13.5732627")


def test_extract_place_url_with_at_coords():
    """Extracts name + coords from @lat,lng pattern."""
    mod = _load_module()
    url = "https://www.google.com/maps/place/B%C3%A4ckerei+M%C3%BCller/@48.1351253,11.5819806,17z"
    assert mod.extract_place_url(url) == ("Bäckerei Müller", "48.1351253,11.5819806")


def test_extract_place_url_no_coords_returns_none():
    """No coordinates in /place/ URL => None."""
    mod = _load_module()
    url = "https://www.google.com/maps/place/SomePlace/"
    assert mod.extract_place_url(url) is None


# ---------------------------------------------------------------------------
# Geocoding API
# ---------------------------------------------------------------------------


@responses.activate
def test_geocode_returns_coords():
    """Successful geocoding returns 'lat,lng' string."""
    mod = _load_module()

    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={
            "status": "OK",
            "results": [
                {"geometry": {"location": {"lat": 52.5219184, "lng": 13.4132147}}}
            ],
        },
        status=200,
    )

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "test-key-123"}):
        result = mod.geocode("Alexanderplatz Berlin")

    assert result == "52.5219184,13.4132147"


@responses.activate
def test_geocode_returns_none_on_zero_results():
    """ZERO_RESULTS status from API => None."""
    mod = _load_module()

    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={"status": "ZERO_RESULTS", "results": []},
        status=200,
    )

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "test-key-123"}):
        result = mod.geocode("nonexistent place xyz")

    assert result is None


def test_geocode_returns_none_when_no_api_key(tmp_path):
    """No API key configured => None."""
    mod = _load_module()

    env_copy = os.environ.copy()
    env_copy.pop("GOOGLE_GEOCODING_API_KEY", None)
    with patch.dict("os.environ", env_copy, clear=True):
        with patch.object(Path, "home", return_value=tmp_path):
            result = mod.geocode("anything")

    assert result is None


# ---------------------------------------------------------------------------
# API key precedence
# ---------------------------------------------------------------------------


def test_get_api_key_prefers_env_var(tmp_path):
    """Env var GOOGLE_GEOCODING_API_KEY takes precedence over config."""
    mod = _load_module()

    config_dir = tmp_path / ".config" / "forensic-perimeter"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text('[google]\napi_key = "from-config"\n')

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "from-env"}):
        result = mod._get_api_key()

    assert result == "from-env"


def test_get_api_key_falls_back_to_config(tmp_path):
    """Without env var, key is read from config.toml."""
    mod = _load_module()

    config_dir = tmp_path / ".config" / "forensic-perimeter"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text('[google]\napi_key = "from-config"\n')

    env_copy = os.environ.copy()
    env_copy.pop("GOOGLE_GEOCODING_API_KEY", None)
    with patch.dict("os.environ", env_copy, clear=True):
        with patch.object(Path, "home", return_value=tmp_path):
            result = mod._get_api_key()

    assert result == "from-config"


def test_get_api_key_returns_none_when_nothing_configured(tmp_path):
    """No env var + no config file => None."""
    mod = _load_module()

    env_copy = os.environ.copy()
    env_copy.pop("GOOGLE_GEOCODING_API_KEY", None)
    with patch.dict("os.environ", env_copy, clear=True):
        with patch.object(Path, "home", return_value=tmp_path):
            result = mod._get_api_key()

    assert result is None


# ---------------------------------------------------------------------------
# /maps/search/ URL resolution
# ---------------------------------------------------------------------------


@responses.activate
def test_resolve_search_url_uses_geocoding_api():
    """Search URL extracts query param as name + geocodes for coords."""
    mod = _load_module()
    search_url = "https://www.google.com/maps/search/?api=1&query=Alexanderplatz+Berlin"

    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={
            "status": "OK",
            "results": [
                {"geometry": {"location": {"lat": 52.5219184, "lng": 13.4132147}}}
            ],
        },
        status=200,
    )

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "test-key-123"}):
        result = mod.resolve_url(search_url)

    assert result == ("Alexanderplatz Berlin", "52.5219184,13.4132147")


@responses.activate
def test_resolve_search_url_with_encoded_query():
    """URL-encoded query param is decoded for the place name."""
    mod = _load_module()
    search_url = "https://www.google.com/maps/search/?api=1&query=B%C3%A4ckerei+M%C3%BCller"

    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={
            "status": "OK",
            "results": [
                {"geometry": {"location": {"lat": 48.135, "lng": 11.582}}}
            ],
        },
        status=200,
    )

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "test-key-123"}):
        result = mod.resolve_url(search_url)

    assert result == ("Bäckerei Müller", "48.135,11.582")


# ---------------------------------------------------------------------------
# End-to-end resolve_url
# ---------------------------------------------------------------------------


@responses.activate
def test_resolve_url_short_url_to_place():
    """Full: short URL → redirect → /place/ URL → (name, coords)."""
    mod = _load_module()
    short_url = "https://maps.app.goo.gl/xyz123"
    final_url = (
        "https://www.google.com/maps/place/Skatepark+Liberty+2/"
        "@52.5377989,13.5954429,17z/data=!3d52.5377989!4d13.5954429"
    )

    responses.add(
        responses.HEAD,
        short_url,
        status=302,
        headers={"Location": final_url},
    )
    responses.add(responses.HEAD, final_url, status=200)

    result = mod.resolve_url(short_url)
    assert result == ("Skatepark Liberty 2", "52.5377989,13.5954429")


@responses.activate
def test_resolve_url_short_url_to_search():
    """Full: short URL → redirect → /maps/search/ → geocode."""
    mod = _load_module()
    short_url = "https://maps.app.goo.gl/search456"
    final_url = "https://www.google.com/maps/search/?api=1&query=Hauptbahnhof+Berlin"

    responses.add(
        responses.HEAD,
        short_url,
        status=302,
        headers={"Location": final_url},
    )
    responses.add(responses.HEAD, final_url, status=200)
    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={
            "status": "OK",
            "results": [
                {"geometry": {"location": {"lat": 52.525, "lng": 13.369}}}
            ],
        },
        status=200,
    )

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "test-key"}):
        result = mod.resolve_url(short_url)

    assert result == ("Hauptbahnhof Berlin", "52.525,13.369")


def test_resolve_url_unrecognized_format():
    """Unrecognized URL format returns None."""
    mod = _load_module()
    result = mod.resolve_url("https://www.google.com/maps/dir/some+route")
    assert result is None


# ---------------------------------------------------------------------------
# --setup subcommand
# ---------------------------------------------------------------------------


def test_setup_creates_config_file(tmp_path):
    """--setup creates config.toml with the provided API key."""
    mod = _load_module()

    with patch.object(Path, "home", return_value=tmp_path):
        with patch("getpass.getpass", return_value="my-secret-key"):
            mod.setup_api_key()

    config_path = tmp_path / ".config" / "forensic-perimeter" / "config.toml"
    assert config_path.exists()
    content = config_path.read_text()
    assert 'api_key = "my-secret-key"' in content


def test_setup_asks_before_overwrite(tmp_path):
    """--setup with existing key asks confirmation; 'n' aborts."""
    mod = _load_module()

    config_dir = tmp_path / ".config" / "forensic-perimeter"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text('[google]\napi_key = "old-key-dZo0"\n')

    with patch.object(Path, "home", return_value=tmp_path):
        with patch("builtins.input", return_value="n"):
            mod.setup_api_key()

    content = (config_dir / "config.toml").read_text()
    assert "old-key-dZo0" in content


def test_setup_overwrites_when_confirmed(tmp_path):
    """--setup with existing key + 'y' confirmation overwrites."""
    mod = _load_module()

    config_dir = tmp_path / ".config" / "forensic-perimeter"
    config_dir.mkdir(parents=True)
    (config_dir / "config.toml").write_text('[google]\napi_key = "old-key-dZo0"\n')

    with patch.object(Path, "home", return_value=tmp_path):
        with patch("builtins.input", return_value="y"):
            with patch("getpass.getpass", return_value="new-key-abc"):
                mod.setup_api_key()

    content = (config_dir / "config.toml").read_text()
    assert 'api_key = "new-key-abc"' in content


# ---------------------------------------------------------------------------
# Plain name input (no URL)
# ---------------------------------------------------------------------------


@responses.activate
def test_resolve_input_plain_name_geocodes():
    """Plain text (no http) is geocoded directly."""
    mod = _load_module()

    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={
            "status": "OK",
            "results": [
                {"geometry": {"location": {"lat": 52.5204781, "lng": 13.4228483}}}
            ],
        },
        status=200,
    )

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "test-key"}):
        result = mod.resolve_input("Kino International Berlin")

    assert result == ("Kino International Berlin", "52.5204781,13.4228483")


@responses.activate
def test_resolve_input_url_delegates_to_resolve_url():
    """Input starting with http delegates to resolve_url."""
    mod = _load_module()
    url = (
        "https://www.google.com/maps/place/Kaufpark+Eich/"
        "@52.5366048,13.5732627,17z/data=!3d52.5366048!4d13.5732627"
    )
    result = mod.resolve_input(url)
    assert result == ("Kaufpark Eich", "52.5366048,13.5732627")


@responses.activate
def test_resolve_input_plain_name_returns_none_on_failure():
    """Plain name that fails geocoding returns None."""
    mod = _load_module()

    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={"status": "ZERO_RESULTS", "results": []},
        status=200,
    )

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "test-key"}):
        result = mod.resolve_input("xyznonexistent12345")

    assert result is None


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def test_format_results_tsv():
    """TSV format: name<tab>lat,lng — no header."""
    mod = _load_module()
    results = [
        {"name": "Place A", "lat": 52.52, "lng": 13.40, "error": None},
        {"name": "Place B", "lat": 48.13, "lng": 11.58, "error": None},
    ]
    output = mod.format_results(results, fmt="tsv", link=False)
    assert output == "Place A\t52.52,13.4\nPlace B\t48.13,11.58"


def test_format_results_csv():
    """CSV format: header + name,lat,lng rows."""
    mod = _load_module()
    results = [
        {"name": "Place A", "lat": 52.52, "lng": 13.40, "error": None},
    ]
    output = mod.format_results(results, fmt="csv", link=False)
    assert output == "name,lat,lng\nPlace A,52.52,13.4"


def test_format_results_json():
    """JSON format: array of objects with name, lat, lng."""
    import json
    mod = _load_module()
    results = [
        {"name": "Place A", "lat": 52.52, "lng": 13.40, "error": None},
    ]
    output = mod.format_results(results, fmt="json", link=False)
    parsed = json.loads(output)
    assert parsed == [{"name": "Place A", "lat": 52.52, "lng": 13.4}]


def test_format_results_json_includes_errors():
    """JSON format includes error field for failed entries."""
    import json
    mod = _load_module()
    results = [
        {"name": "Place A", "lat": 52.52, "lng": 13.40, "error": None},
        {"name": "Bad Place", "lat": None, "lng": None, "error": "ZERO_RESULTS"},
    ]
    output = mod.format_results(results, fmt="json", link=False)
    parsed = json.loads(output)
    assert parsed[0] == {"name": "Place A", "lat": 52.52, "lng": 13.4}
    assert parsed[1] == {"name": "Bad Place", "lat": None, "lng": None, "error": "ZERO_RESULTS"}


def test_format_results_tsv_skips_errors():
    """TSV format skips entries with errors."""
    mod = _load_module()
    results = [
        {"name": "Place A", "lat": 52.52, "lng": 13.40, "error": None},
        {"name": "Bad Place", "lat": None, "lng": None, "error": "ZERO_RESULTS"},
    ]
    output = mod.format_results(results, fmt="tsv", link=False)
    assert output == "Place A\t52.52,13.4"


def test_format_results_csv_skips_errors():
    """CSV format skips entries with errors."""
    mod = _load_module()
    results = [
        {"name": "Place A", "lat": 52.52, "lng": 13.40, "error": None},
        {"name": "Bad Place", "lat": None, "lng": None, "error": "ZERO_RESULTS"},
    ]
    output = mod.format_results(results, fmt="csv", link=False)
    assert output == "name,lat,lng\nPlace A,52.52,13.4"


# ---------------------------------------------------------------------------
# --link flag
# ---------------------------------------------------------------------------


def test_format_results_tsv_with_link():
    """TSV with --link appends maps URL as third column."""
    mod = _load_module()
    results = [
        {"name": "Kino International", "lat": 52.5204781, "lng": 13.4228483, "error": None},
    ]
    output = mod.format_results(results, fmt="tsv", link=True)
    assert output == (
        "Kino International\t52.5204781,13.4228483\t"
        "https://www.google.com/maps/place/Kino+International/@52.5204781,13.4228483,17z"
    )


def test_format_results_csv_with_link():
    """CSV with --link adds link column."""
    mod = _load_module()
    results = [
        {"name": "Kino International", "lat": 52.5204781, "lng": 13.4228483, "error": None},
    ]
    output = mod.format_results(results, fmt="csv", link=True)
    lines = output.split("\n")
    assert lines[0] == "name,lat,lng,link"
    assert "https://www.google.com/maps/place/Kino+International/@52.5204781,13.4228483,17z" in lines[1]


def test_format_results_json_with_link():
    """JSON with --link adds link field."""
    import json
    mod = _load_module()
    results = [
        {"name": "Kino International", "lat": 52.5204781, "lng": 13.4228483, "error": None},
    ]
    output = mod.format_results(results, fmt="json", link=True)
    parsed = json.loads(output)
    assert parsed[0]["link"] == (
        "https://www.google.com/maps/place/Kino+International/@52.5204781,13.4228483,17z"
    )


# ---------------------------------------------------------------------------
# Exit code on errors
# ---------------------------------------------------------------------------


@responses.activate
def test_main_exits_nonzero_on_failure(capsys):
    """main() exits with code 1 if any input fails to resolve."""
    import pytest
    mod = _load_module()

    responses.add(
        responses.GET,
        "https://maps.googleapis.com/maps/api/geocode/json",
        json={"status": "ZERO_RESULTS", "results": []},
        status=200,
    )

    with patch.dict("os.environ", {"GOOGLE_GEOCODING_API_KEY": "test-key"}):
        with patch("sys.argv", ["resolve-places.py", "nonexistent_place_xyz"]):
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 1
