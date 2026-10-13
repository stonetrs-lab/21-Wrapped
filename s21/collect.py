"""Pulls everything the Wrapped needs into one raw JSON-able dict."""

import datetime as dt
import sys

from .api import ApiError


def _optional(label, fetch):
    """Runs one fetch; a failing endpoint costs a slide, not the whole run."""
    print(f"  {label}", file=sys.stderr)
    try:
        return fetch()
    except ApiError as err:
        print(f"    skipped ({err})", file=sys.stderr)
        return None


def _finished_weeks(previous):
    """Weeks from an earlier run that had already ended when it ran.
    Those can't change any more, so they never need fetching again."""
    if not previous or not previous.get("logtime"):
        return {}
    fetched = dt.date.fromisoformat(previous["fetchedAt"][:10])
    return {w["week"]: w["hours"] for w in previous["logtime"]
            if dt.date.fromisoformat(w["week"]) + dt.timedelta(days=7) <= fetched}


def _logtime_weeks(client, login, weeks, today, previous):
    """The API only gives a weekly average for the week containing `date`,
    so we sample one date per week to rebuild the history."""
    monday = today - dt.timedelta(days=today.weekday())
    known = _finished_weeks(previous)
    history = []
    for back in range(weeks - 1, -1, -1):
        week = (monday - dt.timedelta(weeks=back)).isoformat()
        hours = known.get(week)
        if hours is None:
            hours = client.get(f"/participants/{login}/logtime", date=week)
        history.append({"week": week, "hours": hours})
        print(f"\r  logtime {weeks - back}/{weeks} "
              f"({len(known)} weeks from cache)", end="", file=sys.stderr)
    print(file=sys.stderr)
    return history


def collect(client, login, weeks=52, previous=None):
    base = f"/participants/{login}"
    raw = {"login": login, "fetchedAt": dt.datetime.now().isoformat()}
    print(f"fetching {login}", file=sys.stderr)
    raw["participant"] = client.get(base)
    raw["projects"] = _optional("projects", lambda: client.get_all(
        f"{base}/projects", "projects"))
    raw["courses"] = _optional("courses", lambda: client.get_all(
        f"{base}/courses", "courses"))
    raw["skills"] = _optional("skills", lambda: client.get(
        f"{base}/skills")["skills"])
    raw["badges"] = _optional("badges", lambda: client.get(
        f"{base}/badges")["badges"])
    raw["points"] = _optional("points", lambda: client.get(f"{base}/points"))
    raw["feedback"] = _optional("feedback", lambda: client.get(
        f"{base}/feedback"))
    raw["coalition"] = _optional("coalition", lambda: client.get(
        f"{base}/coalition"))
    # /graph is the map of whoever owns the token. For a peer it is still
    # a good layout: their own projects decide which cells light up.
    raw["graph"] = _optional("graph", lambda: client.get("/graph"))
    raw["logtime"] = _optional("logtime", lambda: _logtime_weeks(
        client, login, weeks, dt.date.today(), previous))
    return raw
