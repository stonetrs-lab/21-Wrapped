#!/usr/bin/env python3
"""School 21 Wrapped: turns your platform data into a story-style page.

    python3 wrapped.py                 # wrap yourself
    python3 wrapped.py somepeer        # wrap a peer (no project map slide)
    python3 wrapped.py --offline       # re-render from cache/, no API calls
    python3 wrapped.py --demo          # fake data, no credentials needed

Login and password come from S21_LOGIN / S21_PASSWORD, then credentials.env,
then a prompt. The password only goes to the School 21 auth server. The token
it returns is kept in cache/token.json until it expires.
"""

import argparse
import getpass
import json
import os
import sys
import time
import webbrowser
from pathlib import Path

from s21 import api, collect, demo, render, stats

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
CREDENTIALS = HERE / "credentials.env"
TOKEN = CACHE / "token.json"


def parse_args():
    parser = argparse.ArgumentParser(description="School 21 Wrapped")
    parser.add_argument("login", nargs="?", help="whose Wrapped (default: you)")
    parser.add_argument("--demo", action="store_true", help="use fake data")
    parser.add_argument("--offline", action="store_true",
                        help="render from cache/<login>.json without the API")
    parser.add_argument("--weeks", type=int, default=52,
                        help="weeks of logtime history to sample (default 52)")
    parser.add_argument("-o", "--out", help="output HTML path")
    parser.add_argument("--open", action="store_true", help="open in browser")
    return parser.parse_args()


def read_env_file(path):
    """KEY=VALUE lines; blank lines, comments and empty values are skipped."""
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            value = value.strip().strip("'\"")
            if sep and not key.startswith("#") and value:
                values[key.strip()] = value
    return values


def setting(name, saved):
    return os.environ.get(name) or saved.get(name)


def write_private(path, text):
    path.parent.mkdir(exist_ok=True)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text(text, encoding="utf-8")


def cached_token(login):
    try:
        saved = json.loads(TOKEN.read_text())
    except (OSError, ValueError):
        return None
    fresh = saved.get("expiresAt", 0) > time.time() + 60
    return saved["accessToken"] if saved.get("login") == login and fresh else None


def new_token(login, saved):
    password = setting("S21_PASSWORD", saved) or getpass.getpass("Password: ")
    payload = api.get_token(login, password)
    write_private(TOKEN, json.dumps({
        "login": login,
        "accessToken": payload["access_token"],
        "expiresAt": time.time() + payload.get("expires_in", 300),
    }))
    return payload["access_token"]


def fetch(args):
    saved = read_env_file(CREDENTIALS)
    own = setting("S21_LOGIN", saved) or input("School 21 login: ").strip()
    login = args.login or own
    previous_path = CACHE / f"{login}.json"
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else None
    token = cached_token(own)
    try:
        client = api.Client(token or new_token(own, saved))
        raw = collect.collect(client, login, args.weeks, previous)
    except api.ApiError as err:
        if err.status != 401 or not token:
            raise
        print("saved token was rejected, logging in again", file=sys.stderr)
        client = api.Client(new_token(own, saved))
        raw = collect.collect(client, login, args.weeks, previous)
    previous_path.parent.mkdir(exist_ok=True)
    previous_path.write_text(json.dumps(raw, ensure_ascii=False, indent=1))
    print(f"raw data cached in {previous_path}", file=sys.stderr)
    return raw


def borrow_graph(raw):
    """Peer caches from before the map worked for peers have no graph.
    Any cached graph will do, since it is only the layout."""
    if raw.get("graph"):
        return raw
    for path in sorted(CACHE.glob("*.json")):
        if path.name != TOKEN.name:
            graph = json.loads(path.read_text()).get("graph")
            if graph:
                return {**raw, "graph": graph}
    return raw


def load_raw(args):
    if args.demo:
        return demo.raw_demo(args.login or "demo", args.weeks)
    if args.offline:
        login = args.login or setting("S21_LOGIN", read_env_file(CREDENTIALS))
        if not login:
            sys.exit("--offline needs a login, e.g. wrapped.py --offline mylogin")
        return json.loads((CACHE / f"{login}.json").read_text())
    return fetch(args)


def main():
    args = parse_args()
    try:
        raw = load_raw(args)
    except api.ApiError as err:
        sys.exit(f"error: {err}")
    except FileNotFoundError as err:
        sys.exit(f"error: no cached data ({err.filename}), run once without --offline")
    story = stats.build(borrow_graph(raw))
    out = Path(args.out) if args.out else HERE / "out" / f"{raw['login']}-wrapped.html"
    path = render.render(story, out)
    print(f"wrapped: {path}")
    if args.open:
        webbrowser.open(path.resolve().as_uri())


if __name__ == "__main__":
    main()
