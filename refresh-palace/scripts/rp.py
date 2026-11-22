#!/usr/bin/env python3
"""Deterministic half of refresh-palace: profiles, session audit, transcripts, drawer checks, payloads.

Usage: rp.py <cmd> <profile> [options]
  init     create a profile            --wing W --root R [--root R2] [--glob G] [--description D]
                                       [--skip-marker S] [--known-docs G ...] [--remote URL]
  show     print a profile
  audit    classify sessions newer than the watermark by cwd; exit 3 while anything needs a decision
  confirm  accept cwds into the project   CWD...
  ignore   exclude cwds for good          CWD...
  prepare  audit, then write transcripts, batch lists and contract.md (exit 3 if audit is pending)
  check    validate out-N.jsonl, scan for secrets, list unknown rooms, write a spot-check sample
  rooms    rooms add ROOM... | rooms map OLD NEW   (approve a new room, or rewrite drawers to another)
  build    write ck-N.json payloads (exit 4 while unknown rooms remain)
  done     move the watermark to the newest session of the last prepare

Output is counts, paths and cwds only: never transcript text.
"""
import argparse, fnmatch, glob, json, os, random, re, subprocess, sys, time

CONF = os.path.expanduser('~/.config/mempalace/refresh')
SESSIONS = os.environ.get('OMP_SESSIONS', os.path.expanduser('~/.omp/agent/sessions'))
FIXED_ROOMS = ['tooling', 'architecture', 'workflow', 'testing', 'security', 'config', 'process']
KINDS = ('decision', 'discovery', 'troubleshooting', 'preference')
CONF_LEVELS = ('high', 'med', 'low')
KEYS = {'room', 'kind', 'title', 'body', 'session', 'date', 'worktree', 'confidence'}
SECRETS = {
    'bearer': r'Bearer\s+[A-Za-z0-9._~+/=-]{10,}',
    'gitlab-token': r'glpat-[A-Za-z0-9_-]{10,}',
    'github-token': r'gh[pousr]_[A-Za-z0-9]{20,}',
    'aws-key': r'AKIA[0-9A-Z]{16}',
    'slack-token': r'xox[baprs]-[A-Za-z0-9-]{10,}',
    'api-key': r'sk-[A-Za-z0-9]{20,}',
    'url-credentials': r'://[^/\s:@]+:[^/\s@]+@',
    'private-key': r'-----BEGIN [A-Z ]*PRIVATE KEY',
    'long-token': r'(?<![A-Za-z0-9/_.-])[A-Za-z0-9_-]{40,}(?![A-Za-z0-9/_.-])',
}
STALE = ('batch-*.list', 'out-*.jsonl', 'ck-*.json', 'run.json', 'sample.txt', 'contract.md', '*.txt')
CWD_COL = 12  # how many cwds one audit section lists before collapsing


def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


# ---- profile and state -----------------------------------------------------------------------

def ppath(name):
    return os.path.join(CONF, name + '.json')


def spath(name):
    return os.path.join(CONF, name + '.state.json')


def load(name):
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]*', name):
        die(f'profile name {name!r}: use lowercase letters, digits, . _ - only (no slash; the wing name is separate)')
    if not os.path.exists(ppath(name)):
        die(f'no profile {ppath(name)}: create it with `rp.py init {name} --wing W --root R`')
    return json.load(open(ppath(name)))


def save(p):
    os.makedirs(CONF, exist_ok=True)
    json.dump(p, open(ppath(p['name']), 'w'), indent=2)
    open(ppath(p['name']), 'a').write('\n')


def work(name):
    return os.path.join(os.environ.get('TMPDIR') or '/tmp', 'refresh-' + name)


def watermark(name, since=None):
    if since:
        return since
    if os.path.exists(spath(name)):
        return json.load(open(spath(name)))['last_session_ts']
    return ''  # first run: every session


# ---- git and path helpers --------------------------------------------------------------------

def git(cwd, *args):
    try:
        r = subprocess.run(['git', '-C', cwd, *args], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def norm_remote(u):
    u = u.strip().lower()
    if '://' in u:
        host, _, rest = u.split('://', 1)[1].partition('/')
        u = host.rsplit('@', 1)[-1] + '/' + rest
    elif re.match(r'^[^/]+:[^/]', u):  # scp-like git@host:path
        host, _, rest = u.partition(':')
        u = host.rsplit('@', 1)[-1] + '/' + rest
    return re.sub(r'\.git$', '', u).rstrip('/')


def under(cwd, root):
    c, r = cwd.rstrip('/'), root.rstrip('/')
    return c == r or c.startswith(r + '/')


def header_cwd(path):
    with open(path, errors='ignore') as fh:
        for i, line in enumerate(fh):
            if i > 4:  # the session header is in the first lines
                break
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get('type') == 'session':
                return d.get('cwd') or ''
    return ''


# ---- audit -----------------------------------------------------------------------------------

def collect(since, min_age):
    """cwd -> [session files] newer than the watermark; second value: files skipped as running."""
    by, running, now = {}, 0, time.time()
    for f in sorted(glob.glob(os.path.join(SESSIONS, '*', '20[2-9][0-9]-*.jsonl'))):
        if os.path.basename(f)[:19] <= since:
            continue
        if now - os.path.getmtime(f) < min_age * 60:
            running += 1
            continue
        cwd = header_cwd(f)
        if cwd:
            by.setdefault(cwd, []).append(f)
    return by, running


def classify(p, by):
    """Return {cwd: (status, why)}. status: member|pending-new|pending-mismatch|pending-suspect|weak|ignored|other."""
    roots = p['roots']
    remote = norm_remote(p['remote']) if p.get('remote') else ''
    wt = set()
    for r in roots:
        for line in git(r, 'worktree', 'list', '--porcelain').splitlines():
            if line.startswith('worktree '):
                wt.add(line[9:])
    needles = roots + ([remote.split('/', 1)[1]] if '/' in remote else [])
    res = {}
    for cwd, files in by.items():
        if cwd in p['ignored_cwds']:
            res[cwd] = ('ignored', '')
            continue
        trusted = any(under(cwd, r) for r in roots)
        globbed = any(fnmatch.fnmatch(cwd, g) for g in p['worktree_globs'])
        if cwd in p['confirmed_cwds']:
            res[cwd] = ('member', 'confirmed')
            continue
        if trusted or globbed:
            got = norm_remote(git(cwd, 'remote', 'get-url', 'origin')) if remote and os.path.isdir(cwd) else ''
            if got and got != remote:
                res[cwd] = ('pending-mismatch', f'remote {got} != {remote}')
            elif trusted:
                res[cwd] = ('member', 'root')
            else:
                res[cwd] = ('pending-new', 'glob')
            continue
        why = []
        if cwd in wt:
            why.append('git-worktree-list')
        if os.path.isdir(cwd):
            common = git(cwd, 'rev-parse', '--path-format=absolute', '--git-common-dir')
            if common and any(common == os.path.join(r, '.git') for r in roots):
                why.append('git-common-dir')
            elif remote and norm_remote(git(cwd, 'remote', 'get-url', 'origin')) == remote:
                why.append('git-remote')
        base, parent = os.path.basename(cwd), os.path.dirname(cwd)
        for r in roots:
            rb = os.path.basename(r.rstrip('/'))
            if parent == os.path.dirname(r.rstrip('/')) and re.match(re.escape(rb) + r'[-_.]', base):
                why.append('name')
        if why:
            res[cwd] = ('pending-suspect', ','.join(sorted(set(why))))
            continue
        hits = 0
        for f in files[-5:]:
            head = open(f, errors='ignore').read(200_000)
            hits += any(n in head for n in needles)
        res[cwd] = ('weak', f'content {hits}/{len(files[-5:])}') if hits else ('other', '')
    return res


def audit(p, since, min_age, quiet=False):
    by, running = collect(since, min_age)
    res = classify(p, by)
    groups = {}
    for cwd, (st, why) in res.items():
        groups.setdefault(st, []).append((cwd, why, len(by[cwd])))
    total = sum(len(v) for v in by.values())
    out = [f'profile {p["name"]}  wing={p["wing"]}  watermark={since or "(none: all sessions)"}',
           f'{total} sessions in {len(by)} cwds newer than the watermark; {running} skipped as still running']
    members = sorted(groups.get('member', []))
    out.append(f'member: {sum(n for _, _, n in members)} sessions in {len(members)} cwds')
    for cwd, why, n in members[:CWD_COL]:
        out.append(f'  {n:4d}  {cwd}  [{why}]')
    pending = 0
    for st in ('pending-new', 'pending-mismatch', 'pending-suspect'):
        items = sorted(groups.get(st, []))
        pending += len(items)
        for cwd, why, n in items:
            out.append(f'{st.upper():17s} {n:4d}  {cwd}  [{why}]')
    weak = sorted(groups.get('weak', []), key=lambda x: -x[2])
    if weak:
        out.append(f'weak signal (info only, not blocking): {len(weak)} cwds mention the project')
        for cwd, why, n in weak[:5]:
            out.append(f'  {n:4d}  {cwd}  [{why}]')
    ign = groups.get('ignored', [])
    other = groups.get('other', [])
    out.append(f'ignored: {sum(n for _, _, n in ign)} sessions in {len(ign)} cwds; unrelated: {sum(n for _, _, n in other)} sessions in {len(other)} cwds')
    if pending:
        out.append(f'{pending} cwd(s) need a decision: `rp.py confirm {p["name"]} CWD...` or `rp.py ignore {p["name"]} CWD...`')
    if not quiet or pending:
        print('\n'.join(out))
    return by, res, pending


# ---- commands --------------------------------------------------------------------------------

def cmd_init(a):
    if os.path.exists(ppath(a.profile)):
        die(f'{ppath(a.profile)} exists: edit it by hand or delete it')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', a.wing):
        die(f'wing {a.wing!r}: the palace rejects "/" and other path characters; use letters, digits, . _ -')
    roots = [os.path.abspath(os.path.expanduser(r)).rstrip('/') for r in a.root]
    for r in roots:
        if not os.path.isdir(r):
            die(f'root {r} is not a directory')
    remote = a.remote or git(roots[0], 'remote', 'get-url', 'origin')
    p = {'name': a.profile, 'wing': a.wing, 'description': a.description or '',
         'roots': roots, 'worktree_globs': a.glob or [], 'remote': remote, 'skip_markers': a.skip_marker or [],
         'known_docs': a.known_docs or [], 'rooms': [], 'confirmed_cwds': [], 'ignored_cwds': []}
    save(p)
    print('wrote', ppath(a.profile))
    print('remote:', remote or '(none: identity check off)')
    wts = [l[9:] for r in roots for l in git(r, 'worktree', 'list', '--porcelain').splitlines() if l.startswith('worktree ') and l[9:] not in roots]
    print(f'git worktrees of the roots: {len(wts)}')
    for w in wts[:10]:
        print('  ', w)
    cands = set()
    for r in roots:
        for dp, dn, _ in os.walk(r):
            dn[:] = [d for d in dn if d not in ('.git', 'node_modules', '.venv', 'target', 'build', 'dist')]
            if dp[len(r):].count('/') > 4:
                dn[:] = []
            for d in dn:
                if d.lower() in ('adr', 'adrs', 'decisions', 'troubleshooting'):
                    cands.add(os.path.relpath(os.path.join(dp, d), r) + '/**/*.md')
    print('known_docs candidates (set with --known-docs, or edit the profile):', sorted(cands) or 'none found')


def cmd_show(a):
    print(json.dumps(load(a.profile), indent=2))


def cmd_audit(a):
    p = load(a.profile)
    _, _, pending = audit(p, watermark(a.profile, a.since), a.min_age_min)
    sys.exit(3 if pending else 0)


def _mark(a, key, other):
    p = load(a.profile)
    for c in a.cwd:
        c = c.rstrip('/')
        if c not in p[key]:
            p[key].append(c)
        if c in p[other]:
            p[other].remove(c)
    save(p)
    print(f'{key}: {len(p[key])} cwds in {a.profile}')


def text_of(c):
    if isinstance(c, str):
        return c
    return '\n'.join(b.get('text', '') for b in c or [] if isinstance(b, dict) and b.get('type') == 'text')


def convert(src, dst, cwd, markers):
    out = []
    for line in open(src, errors='ignore'):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        m = d.get('message')
        if not m or m.get('role') not in ('user', 'assistant'):
            continue
        t = text_of(m.get('content')).strip()
        if not t or t.startswith('<system-notice>') or any(k in t[:200] for k in markers):
            continue
        out.append('> ' + t.replace('\n', '\n> ') + '\n' if m['role'] == 'user' else t + '\n')
    if len(out) < 2:  # no exchange: nothing to distil
        return False
    with open(dst, 'w') as fh:
        fh.write(f'# session {os.path.basename(src)} cwd={cwd}\n\n' + '\n'.join(out))
    return True


def rooms_of(p):
    return FIXED_ROOMS + [r for r in p['rooms'] if r not in FIXED_ROOMS]


def cmd_prepare(a):
    p = load(a.profile)
    since = watermark(a.profile, a.since)
    by, res, pending = audit(p, since, a.min_age_min)
    if pending:
        sys.exit(3)
    out = work(a.profile)
    os.makedirs(out, exist_ok=True)
    for pat in STALE:
        for old in glob.glob(os.path.join(out, pat)):
            os.remove(old)
    picked, empty = [], 0
    for cwd, (st, _) in sorted(res.items()):
        if st != 'member':
            continue
        for f in by[cwd]:
            base = os.path.basename(f)
            dst = os.path.join(out, f'{os.path.basename(cwd.rstrip("/")) or "root"}__{base[:-6]}.txt')
            if convert(f, dst, cwd, p['skip_markers']):
                picked.append(dst)
            else:
                empty += 1
    if not picked:
        print(f'nothing new since {since or "(start)"}' + (f' ({empty} sessions had no exchange)' if empty else ''))
        return
    limit = a.batch_kb * 1024
    batches, size = [[]], 0
    for f in sorted(picked, key=lambda x: os.path.basename(x).split('__')[1]):
        sz = os.path.getsize(f)
        # 1.15: let a batch overshoot 15% rather than leave a tiny last batch.
        if size + sz > limit * 1.15 and batches[-1]:
            batches.append([])
            size = 0
        batches[-1].append(f)
        size += sz
    for i, b in enumerate(batches, 1):
        open(os.path.join(out, f'batch-{i}.list'), 'w').write('\n'.join(b) + '\n')
        print(f'batch-{i}: {len(b)} sessions, {sum(os.path.getsize(x) for x in b) // 1024} KB')
    last = max(os.path.basename(x).split('__')[1][:19] for x in picked)
    print(f'{len(picked)} sessions ({empty} without an exchange dropped); newest {last}; work dir {out}')
    json.dump({'newest_in_this_run': last, 'profile': a.profile}, open(os.path.join(out, 'run.json'), 'w'))
    tpl = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'contract.md')).read()
    docs = ', '.join(f'`{g}`' for g in p['known_docs']) or 'none configured'
    sub = {'project': p['name'], 'description': p['description'] or 'a software project', 'known_docs': docs,
           'rooms': ', '.join(f'`{r}`' for r in rooms_of(p)), 'work': out,
           'main_worktree': os.path.basename(p['roots'][0].rstrip('/'))}
    for k, v in sub.items():
        tpl = tpl.replace('@@' + k + '@@', v)
    open(os.path.join(out, 'contract.md'), 'w').write(tpl)
    print('contract:', os.path.join(out, 'contract.md'))


def out_files(out):
    return sorted(glob.glob(os.path.join(out, 'out-*.jsonl')), key=lambda x: int(re.findall(r'\d+', os.path.basename(x))[0]))


def cmd_check(a):
    p = load(a.profile)
    out = work(a.profile)
    files = out_files(out)
    if not files:
        die(f'no out-*.jsonl in {out}: run the distil step first')
    known = set(rooms_of(p))
    good, bad, flagged, unknown, med_low = 0, [], [], {}, []
    secrets = {k: re.compile(v) for k, v in SECRETS.items()}
    for f in files:
        keep = []
        for n, line in enumerate(open(f), 1):
            if not line.strip():
                continue
            tag = f'{os.path.basename(f)}:{n}'
            try:
                d = json.loads(line)
            except ValueError:
                bad.append(f'{tag} not JSON')
                continue
            why = [f'missing {sorted(KEYS - set(d))}'] if KEYS - set(d) else []
            if d.get('kind') not in KINDS:
                why.append(f'kind {d.get("kind")!r} not in {KINDS}')
            if d.get('confidence') not in CONF_LEVELS:
                why.append(f'confidence {d.get("confidence")!r} not in {CONF_LEVELS}')
            if len(str(d.get('title', ''))) >= 90:
                why.append(f'title is {len(str(d["title"]))} chars, limit 89')
            if why:
                bad.append(f'{tag} schema: ' + '; '.join(why))
                continue
            hit = [k for k, rx in secrets.items() if rx.search(d['title'] + '\n' + d['body'])]
            if hit:
                flagged.append(f'{tag} secret pattern: {",".join(hit)}')
                continue
            keep.append(line)
            good += 1
            if d['room'] not in known:
                unknown.setdefault(d['room'], []).append(d['title'])
            if d['confidence'] != 'high':
                med_low.append((tag, d['title'], d['session']))
        if a.drop_flagged:
            open(f, 'w').write(''.join(keep if keep and keep[-1].endswith('\n') else [k + '\n' for k in keep]))
    # spot-check sample: 5 per 50 drawers, med/low confidence first
    rng = random.Random(0)
    allrows = []
    for f in files:
        for n, line in enumerate(open(f), 1):
            if line.strip():
                try:
                    d = json.loads(line)
                    allrows.append((d['confidence'] == 'high', f'{os.path.basename(f)}:{n}', d['title'], d['session']))
                except (ValueError, KeyError):
                    pass
    k = max(1, (len(allrows) * 5 + 49) // 50) if allrows else 0
    rng.shuffle(allrows)
    sample = sorted(allrows, key=lambda x: x[0])[:k]
    tr = {os.path.basename(t).split('__')[1][:-4].split('_', 1)[-1]: t for t in glob.glob(os.path.join(out, '*__*.txt'))}
    with open(os.path.join(out, 'sample.txt'), 'w') as fh:
        for _, tag, title, sid in sample:
            fh.write(f'{tag} | {title} | {tr.get(sid, "(transcript not found)")}\n')
    print(f'{good} valid drawers in {len(files)} files; {len(bad)} schema errors; {len(flagged)} secret hits; {len(unknown)} unknown rooms')
    for line in bad[:20] + flagged[:20]:
        print('  ' + line)
    if flagged and not a.drop_flagged:
        print('  rerun with --drop-flagged to delete the flagged drawers, or edit the files')
    for room, titles in sorted(unknown.items(), key=lambda x: -len(x[1])):
        print(f'NEW ROOM {room!r}: {len(titles)} drawers, e.g. {titles[0]!r}' + (f', {titles[1]!r}' if len(titles) > 1 else ''))
    if unknown:
        print(f'approve: `rp.py rooms {a.profile} add ROOM`; or fold: `rp.py rooms {a.profile} map OLD NEW`')
    print(f'spot-check sample ({len(sample)} drawers): {os.path.join(out, "sample.txt")}')
    sys.exit(0 if not (bad or flagged or unknown) else 4)


def cmd_rooms(a):
    p = load(a.profile)
    if a.action == 'add':
        for r in a.args:
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', r):
                die(f'room {r!r}: lowercase letters, digits and - only')
            if r not in rooms_of(p):
                p['rooms'].append(r)
        save(p)
        print('rooms:', ', '.join(rooms_of(p)))
        return
    if len(a.args) != 2:
        die('rooms map OLD NEW')
    old, new = a.args
    if new not in rooms_of(p):
        die(f'{new!r} is not a known room: `rp.py rooms {a.profile} add {new}` first')
    n = 0
    for f in out_files(work(a.profile)):
        lines = []
        for line in open(f):
            if line.strip():
                d = json.loads(line)
                if d.get('room') == old:
                    d['room'] = new
                    n += 1
                line = json.dumps(d, ensure_ascii=False) + '\n'
            lines.append(line)
        open(f, 'w').writelines(lines)
    print(f'{n} drawers moved {old} -> {new}')


def cmd_build(a):
    p = load(a.profile)
    out = work(a.profile)
    known = set(rooms_of(p))
    main = os.path.basename(p['roots'][0].rstrip('/'))
    items, unknown = [], set()
    for f in out_files(out):
        for line in open(f):
            if not line.strip():
                continue
            r = json.loads(line)
            if r['room'] not in known:
                unknown.add(r['room'])
            wt = r.get('worktree') or main
            content = (f"[{r['kind']}] {r['title']}\n\n{r['body']}\n\n"
                       f"Source sessions: omp_{r['session'][:13]} | date {r['date']} | confidence {r['confidence']}"
                       + ('' if wt == main else f' | worktree {wt}'))
            items.append({'wing': p['wing'], 'room': r['room'], 'content': content})
    if unknown:
        die(f'unknown rooms {sorted(unknown)}: run `rp.py check {a.profile}` and decide each', 4)
    if not items:
        die(f'no drawers in {out}/out-*.jsonl: run the distil step first')
    per = 40  # one checkpoint call stays small enough to finish
    for n, i in enumerate(range(0, len(items), per)):
        json.dump({'action': 'checkpoint', 'items': items[i:i + per]}, open(os.path.join(out, f'ck-{n}.json'), 'w'))
    print(f'{len(items)} drawers for wing {p["wing"]} in {(len(items) + per - 1) // per} payloads')


def cmd_done(a):
    run = os.path.join(work(a.profile), 'run.json')
    if not os.path.exists(run):
        die(f'{run} missing: run prepare first; the watermark did not move')
    load(a.profile)
    newest = json.load(open(run))['newest_in_this_run']
    os.makedirs(CONF, exist_ok=True)
    json.dump({'last_session_ts': newest}, open(spath(a.profile), 'w'))
    print('watermark ->', newest)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['init', 'show', 'audit', 'confirm', 'ignore', 'prepare', 'check', 'rooms', 'build', 'done'])
    ap.add_argument('profile')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--wing')
    ap.add_argument('--root', action='append')
    ap.add_argument('--glob', action='append')
    ap.add_argument('--description')
    ap.add_argument('--skip-marker', action='append')
    ap.add_argument('--known-docs', action='append')
    ap.add_argument('--remote')
    ap.add_argument('--since', help='filename timestamp such as 2026-11-22T10-19-59')
    ap.add_argument('--batch-kb', type=int, default=400)  # 400 KB of transcript is about 100k tokens
    ap.add_argument('--min-age-min', type=int, default=30)  # a session written in that window is the one running this refresh
    ap.add_argument('--drop-flagged', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'init':
        if not a.wing or not a.root:
            die('init needs --wing and at least one --root')
        return cmd_init(a)
    if a.cmd in ('confirm', 'ignore'):
        a.cwd = a.args
        if not a.cwd:
            die(f'{a.cmd} needs one or more cwds')
        return _mark(a, 'confirmed_cwds' if a.cmd == 'confirm' else 'ignored_cwds', 'ignored_cwds' if a.cmd == 'confirm' else 'confirmed_cwds')
    if a.cmd == 'rooms':
        if not a.args or a.args[0] not in ('add', 'map'):
            die('rooms add ROOM... | rooms map OLD NEW')
        a.action, a.args = a.args[0], a.args[1:]
        return cmd_rooms(a)
    {'show': cmd_show, 'audit': cmd_audit, 'prepare': cmd_prepare, 'check': cmd_check, 'build': cmd_build, 'done': cmd_done}[a.cmd](a)


if __name__ == '__main__':
    main()
