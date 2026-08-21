#!/usr/bin/env python3
"""Elementor guard — refuse silent no-op writes to post_content.

A page with ``_elementor_edit_mode == 'builder'`` renders from the
``_elementor_data`` meta field. WordPress ``post_content`` is ignored entirely on
those pages, so a REST write to ``content`` returns HTTP 200 and changes nothing a
visitor or a crawler will ever see. That silent success is the defect: every
fact-check pass, SEO rewrite and internal-linking batch ever applied to a builder
page was thrown away without a single error.

Call this before writing ``content`` to any post.

CLI
    elementor_guard.py <post_id> [<post_id> ...]

    Exit 0  every id is safe to write via post_content
    Exit 3  at least one id is builder-backed — do NOT write post_content
    Exit 1  could not determine (credentials, network, REST error)

    Prints one ``<id> <verdict> <url>`` line per post; verdict is ``ok`` or
    ``BUILDER``. Machine-readable JSON with --json.

Library
    from elementor_guard import check_post, assert_writable
    assert_writable(post_id)   # raises ElementorGuardError on a builder page
"""

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = 'Mozilla/5.0 (elementor-guard)'
CRED_DEFAULT = os.path.expanduser('~/.claude/factcheck-flow/wp-credentials')


class ElementorGuardError(RuntimeError):
    """Raised when a post must not be written through post_content."""


def load_credentials():
    """Resolve WP credentials: env, then $WP_CREDENTIALS_FILE, then the default path.

    Accepts both the ``KEY=VALUE`` form and the labelled-document form
    (``Site URL:`` / ``Username:`` / ``Application Password:``).
    """
    base = os.environ.get('WP_BASE_URL')
    user = os.environ.get('WP_USER')
    pw = os.environ.get('WP_APP_PASSWORD')
    if base and user and pw:
        return base.rstrip('/'), user, pw

    path = os.environ.get('WP_CREDENTIALS_FILE') or CRED_DEFAULT
    try:
        with open(path, encoding='utf-8', errors='replace') as fh:
            text = fh.read()
    except OSError as exc:
        raise ElementorGuardError(f'no WP credentials: {exc}') from exc

    def grab(key, label):
        m = re.search(rf'^\s*{key}\s*=\s*(.+)$', text, re.M)
        if m:
            return m.group(1).strip().strip('"\'')
        m = re.search(rf'{label}\s*:\s*(.+)', text, re.I)
        return m.group(1).strip() if m else None

    base = base or grab('WP_BASE_URL', r'Site\s+URL')
    user = user or grab('WP_USER', r'Username')
    pw = pw or grab('WP_APP_PASSWORD', r'Application\s+Password')
    if not (base and user and pw):
        raise ElementorGuardError(f'incomplete WP credentials in {path}')
    return base.rstrip('/'), user, pw


def _get(url, auth):
    req = urllib.request.Request(url, headers={'Authorization': auth, 'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def check_post(post_id, creds=None):
    """Return {'id', 'url', 'edit_mode', 'builder', 'payload_bytes'} for one post."""
    base, user, pw = creds or load_credentials()
    auth = 'Basic ' + base64.b64encode(f'{user}:{pw}'.encode()).decode()
    fields = 'id,link,meta._elementor_edit_mode,meta._elementor_data'
    q = urllib.parse.urlencode({'context': 'edit', '_fields': fields})
    for kind in ('posts', 'pages'):
        try:
            data = _get(f'{base}/wp-json/wp/v2/{kind}/{post_id}?{q}', auth)
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 404) and kind == 'posts':
                continue
            raise ElementorGuardError(f'post {post_id}: HTTP {exc.code}') from exc
        meta = data.get('meta') or {}
        payload = meta.get('_elementor_data') or ''
        if not isinstance(payload, str):
            payload = json.dumps(payload)
        return {
            'id': data.get('id', post_id),
            'url': data.get('link'),
            'edit_mode': meta.get('_elementor_edit_mode'),
            'builder': meta.get('_elementor_edit_mode') == 'builder',
            'payload_bytes': len(payload),
        }
    raise ElementorGuardError(f'post {post_id}: not found as post or page')


def assert_writable(post_id, creds=None):
    """Raise unless ``post_content`` is what this post actually renders."""
    info = check_post(post_id, creds=creds)
    if info['builder']:
        raise ElementorGuardError(
            f"post {post_id} ({info['url']}) is Elementor-built "
            f"(_elementor_edit_mode=builder, payload {info['payload_bytes']} bytes). "
            'Writing post_content would return HTTP 200 and change nothing live. '
            'Use scripts/elementor_writer.py instead.'
        )
    return info


def main(argv):
    as_json = '--json' in argv
    ids = [a for a in argv if a.isdigit()]
    if not ids:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    try:
        creds = load_credentials()
    except ElementorGuardError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1

    results, failed, blocked = [], False, False
    for pid in ids:
        try:
            info = check_post(int(pid), creds=creds)
        except ElementorGuardError as exc:
            results.append({'id': int(pid), 'error': str(exc)})
            failed = True
            continue
        results.append(info)
        blocked = blocked or info['builder']

    if as_json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            if 'error' in r:
                print(f"{r['id']} ERROR {r['error']}")
            else:
                print(f"{r['id']} {'BUILDER' if r['builder'] else 'ok'} {r['url']}")
    if failed:
        return 1
    return 3 if blocked else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
