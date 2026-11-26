#!/usr/bin/env python3
"""Serve a concept board for README directions and wait for the user's pick.

usage: concept_board.py OPTIONS_JSON [--timeout SECS] [--port N] [--no-open]

OPTIONS_JSON: {"project": str, "directions": [{id, name, tagline, pitch, tone,
palette: [#hex...], fonts: {heading, body}, hero, sections: [str], sketch: path}]}
`sketch` is a path relative to OPTIONS_JSON. The pick is written to choice.json
beside OPTIONS_JSON as {"id": <direction id or "none">, "notes": str}.

Exit codes: 0 pick written, 2 bad input, 3 timeout.
"""
import argparse
import html
import http.server
import json
import mimetypes
import re
import secrets
import sys
import threading
import webbrowser
from pathlib import Path

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
FONT = re.compile(r"^[A-Za-z0-9 ]{1,40}$")  # safe inside a CSS font-family string
ID = re.compile(r"^[A-Za-z0-9_-]{1,20}$")
MAX_BODY = 20_000  # a pick plus notes is far smaller; cap what a local POST may send


def fail(msg):
    print(f"concept_board: {msg}", file=sys.stderr)
    sys.exit(2)


def load(path):
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        fail(f"{path} not found")
    except json.JSONDecodeError as e:
        fail(f"{path} is not valid JSON: {e}")
    dirs = data.get("directions")
    if not isinstance(dirs, list) or not 2 <= len(dirs) <= 4:
        fail("`directions` must be a list of 2 to 4 entries")
    seen = set()
    for d in dirs:
        for key in ("id", "name", "tagline", "pitch", "palette", "sketch"):
            if not d.get(key):
                fail(f"direction {d.get('id', '?')}: missing `{key}`")
        if not ID.match(str(d["id"])) or d["id"] in seen or d["id"] == "none":
            fail(f"direction id {d['id']!r} is invalid, duplicate or reserved")
        seen.add(d["id"])
        if not all(HEX.match(str(c)) for c in d["palette"]):
            fail(f"direction {d['id']}: palette entries must look like #RRGGBB")
        sketch = (path.parent / d["sketch"]).resolve()
        if not sketch.is_file() or path.parent.resolve() not in sketch.parents:
            fail(f"direction {d['id']}: sketch {d['sketch']} must be a file beside OPTIONS_JSON")
    return data


def esc(value):
    return html.escape(str(value), quote=True)


def card(d):
    swatches = "".join(
        f'<span class="sw" style="background:{c}" title="{c}"></span>' for c in d["palette"]
    )
    fonts = d.get("fonts") or {}
    head = fonts.get("heading", "")
    font_style = f' style="font-family:\'{head}\',Georgia,serif"' if FONT.match(str(head)) else ""
    sections = "".join(f"<li>{esc(s)}</li>" for s in d.get("sections", []))
    return f"""<article class="card" id="c-{esc(d['id'])}">
<img src="/sketch/{esc(d['id'])}" alt="Sketch of the {esc(d['name'])} hero">
<div class="body">
<h2{font_style}>{esc(d['name'])}</h2>
<p class="tag"{font_style}>{esc(d['tagline'])}</p>
<p>{esc(d['pitch'])}</p>
<div class="swatches">{swatches}</div>
<dl>
<dt>Tone</dt><dd>{esc(d.get('tone', ''))}</dd>
<dt>Fonts</dt><dd>{esc(head)} / {esc(fonts.get('body', ''))}</dd>
<dt>Hero</dt><dd>{esc(d.get('hero', ''))}</dd>
</dl>
<details><summary>Page outline</summary><ol>{sections}</ol></details>
<button data-id="{esc(d['id'])}">Pick {esc(d['name'])}</button>
</div></article>"""


PAGE = """<!doctype html><meta charset="utf-8"><title>README directions: {project}</title>
<style>
:root{{color-scheme:light dark;font-family:system-ui,sans-serif}}
body{{margin:0;padding:32px;background:Canvas;color:CanvasText}}
h1{{margin:0 0 4px}} .sub{{opacity:.7;margin:0 0 24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px}}
.card{{border:1px solid #8884;border-radius:16px;overflow:hidden;display:flex;flex-direction:column}}
.card img{{width:100%;display:block;background:#8881}}
.body{{padding:16px 20px 20px;display:flex;flex-direction:column;gap:8px;flex:1}}
.body h2{{margin:0}} .tag{{font-size:1.1rem;margin:0;opacity:.85}}
.swatches{{display:flex;gap:6px}} .sw{{width:28px;height:28px;border-radius:50%;border:1px solid #8886}}
dl{{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;margin:0;font-size:.9rem}}
dt{{opacity:.6}} dd{{margin:0}}
button{{margin-top:auto;padding:10px 14px;font:inherit;font-weight:600;border-radius:10px;border:0;background:#1f6feb;color:#fff;cursor:pointer}}
button.none{{background:#8886}}
.foot{{margin-top:28px;display:flex;flex-direction:column;gap:10px;max-width:640px}}
textarea{{font:inherit;padding:10px;border-radius:10px;border:1px solid #8886;min-height:70px}}
#done{{display:none;font-size:1.2rem}}
</style>
<h1>README directions for {project}</h1>
<p class="sub">Pick one. Add notes below to steer the build, or ask for a new round.</p>
<div class="grid">{cards}</div>
<div class="foot" id="foot">
<label for="notes">Notes (optional)</label>
<textarea id="notes" placeholder="Mix the palette of one with the tone of another, change the tagline, ..."></textarea>
<button class="none" data-id="none">None fits: propose a new round using my notes</button>
</div>
<p id="done"></p>
<script>
const token={token};
document.querySelectorAll("button[data-id]").forEach(b=>b.onclick=async()=>{{
  const r=await fetch("/choose",{{method:"POST",headers:{{"Content-Type":"application/json"}},
    body:JSON.stringify({{token,id:b.dataset.id,notes:document.getElementById("notes").value}})}});
  if(r.ok){{document.querySelector(".grid").remove();document.getElementById("foot").remove();
    const d=document.getElementById("done");d.style.display="block";
    d.textContent="Saved. Go back to your agent.";}}
  else alert("Could not save the pick: "+await r.text());
}});
</script>"""


def make_handler(base, data, token, state):
    sketches = {d["id"]: (base / d["sketch"]).resolve() for d in data["directions"]}
    valid = set(sketches) | {"none"}
    page = PAGE.format(
        project=esc(data.get("project", "")),
        cards="".join(card(d) for d in data["directions"]),
        token=json.dumps(token),
    ).encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the agent's output to the URL and the pick
            pass

        def send(self, code, body, ctype="text/plain; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                return self.send(200, page, "text/html; charset=utf-8")
            if self.path.startswith("/sketch/") and self.path[8:] in sketches:
                f = sketches[self.path[8:]]
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                return self.send(200, f.read_bytes(), ctype)
            self.send(404, b"not found")

        def do_POST(self):
            if self.path != "/choose":
                return self.send(404, b"not found")
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > MAX_BODY:
                    return self.send(413, b"body too large")
                body = json.loads(self.rfile.read(length))
            except (ValueError, json.JSONDecodeError):
                return self.send(400, b"bad JSON")
            if body.get("token") != token or body.get("id") not in valid:
                return self.send(403, b"bad token or unknown direction")
            choice = {"id": body["id"], "notes": str(body.get("notes", ""))[:5000]}
            out = base / "choice.json"
            tmp = out.with_suffix(".tmp")
            tmp.write_text(json.dumps(choice, indent=2))
            tmp.replace(out)  # atomic: the agent never reads a half-written file
            state["choice"] = choice
            self.send(200, b"ok")
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("options", type=Path)
    ap.add_argument("--timeout", type=int, default=1800, help="seconds to wait for a pick (default 1800)")
    ap.add_argument("--port", type=int, default=0, help="port on 127.0.0.1 (default: any free port)")
    ap.add_argument("--no-open", action="store_true", help="print the URL and open no browser")
    args = ap.parse_args()

    path = args.options.resolve()
    data = load(path)
    token = secrets.token_urlsafe(16)  # a local page must not accept a pick from another site
    state = {}
    try:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(path.parent, data, token, state))
    except OSError as e:
        fail(f"cannot listen on 127.0.0.1:{args.port}: {e}")
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"board: {url}", flush=True)
    if not args.no_open:
        webbrowser.open(url)

    timer = threading.Timer(args.timeout, server.shutdown)
    timer.daemon = True
    timer.start()
    server.serve_forever()
    timer.cancel()
    server.server_close()
    if "choice" not in state:
        print(f"concept_board: no pick after {args.timeout}s", file=sys.stderr)
        sys.exit(3)
    print(json.dumps(state["choice"]))


if __name__ == "__main__":
    main()
