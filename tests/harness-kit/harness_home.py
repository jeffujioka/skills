"""Temporary HOME folders for the harness-kit tests.

Every harness run of these tests happens in a throwaway HOME: nothing writes
under the developer's ~/.claude, ~/.omp, ~/.config/opencode or ~/.local.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

MODELS = {
    harness: os.environ.get(f"HARNESS_KIT_E2E_MODEL_{harness.upper()}", model)
    for harness, model in {
        "claude": "haiku",
        "omp": "github-copilot/claude-haiku-5.5",
        "opencode": "github-copilot/claude-haiku-5.5",
    }.items()
}

_SYSTEM_BIN_DIRS = ("/usr/local/bin", "/usr/bin", "/bin")
_TOOLS = ("sqlite3", "jq", "python3", "bun")
_PASSED_VARIABLES = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "SSL_CERT_FILE",
    "NODE_EXTRA_CA_CERTS",
)


def make_home(test, harnesses=(), without=(), user="dev"):
    """Make /tmp/<tmp>/home/<user> with .local/bin, test-bin of linked tools and a tmp/ for TMPDIR.

    The folder lives under /tmp, never under the developer's TMPDIR, which may be in ~/.local.
    """
    tmp = Path(tempfile.mkdtemp(prefix="harness-kit-", dir="/tmp"))
    test.addCleanup(shutil.rmtree, tmp, True)
    (tmp / "tmp").mkdir()
    home = tmp / "home" / user
    (home / ".local" / "bin").mkdir(parents=True)
    test_bin = home / "test-bin"
    test_bin.mkdir()
    for folder in _SYSTEM_BIN_DIRS:
        if not os.path.isdir(folder):
            continue
        for entry in os.scandir(folder):
            link = test_bin / entry.name
            if entry.name in without or link.is_symlink():
                continue
            if entry.is_file() and os.access(entry.path, os.X_OK):
                link.symlink_to(entry.path)
    for name in (*_TOOLS, *harnesses):
        found = shutil.which(name)
        if name in without or found is None:
            continue
        link = test_bin / name
        link.unlink(missing_ok=True)
        link.symlink_to(found)
    return home


def env_for(home, extra=None, local_bin_on_path=True):
    """An environment for home that inherits no harness variable."""
    home = Path(home)
    path = f"{home / 'test-bin'}"
    if local_bin_on_path:
        path = f"{home / '.local' / 'bin'}:{path}"
    env = {
        "HOME": str(home),
        "USER": home.name,
        "LOGNAME": home.name,
        "PATH": path,
        "LANG": "C.UTF-8",
        "TMPDIR": str(home.parent.parent / "tmp"),
    }
    env.update({name: os.environ[name] for name in _PASSED_VARIABLES if name in os.environ})
    env.update(extra or {})
    return env


def copy_credentials(home, harness):
    """Copy the developer's credentials for harness into home only."""
    home = Path(home)
    real = Path.home()
    if harness == "claude":
        settings = json.loads((real / ".claude" / "settings.json").read_text())
        target = home / ".claude"
        target.mkdir(parents=True, exist_ok=True)
        (target / "settings.json").write_text(json.dumps({"env": settings.get("env", {})}))
        credentials = real / ".claude" / ".credentials.json"
        if credentials.is_file():
            shutil.copy2(credentials, target / ".credentials.json")
    elif harness == "omp":
        omp = shutil.which("omp")
        exported = subprocess.run(
            [omp, "auth", "export"], capture_output=True, check=True
        ).stdout
        subprocess.run(
            [omp, "auth", "import", "-"],
            input=exported,
            capture_output=True,
            check=True,
            env=env_for(home),
        )
    elif harness == "opencode":
        target = home / ".local" / "share" / "opencode"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(real / ".local" / "share" / "opencode" / "auth.json", target / "auth.json")
    else:
        raise ValueError(f"unknown harness: {harness}")


def install_agent_env(home):
    """Copy harness-kit/bin/agent-env to <home>/.local/bin/agent-env, mode 755."""
    target = Path(home) / ".local" / "bin" / "agent-env"
    shutil.copyfile(REPO / "harness-kit" / "bin" / "agent-env", target)
    target.chmod(0o755)
    return target


def install_skill(home, name):
    """Copy <repo>/<name>/ to <home>/.agents/skills/<name>/."""
    target = Path(home) / ".agents" / "skills" / name
    shutil.copytree(REPO / name, target)
    return target


def write_filler(path):
    """Write 3000 numbered lines of 60 characters, about 45000 tokens."""
    words = "amber basil cedar delta ember fjord grove harbor indigo juniper kelp lumen "
    stream = words * 2
    lines = []
    for number in range(1, 3001):
        start = (number * 7) % len(words)
        lines.append(f"{number:04d} {stream[start:start + 55]}")
    path = Path(path)
    path.write_text("\n".join(lines) + "\n")
    return path
