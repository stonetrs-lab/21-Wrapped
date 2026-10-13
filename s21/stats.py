"""Turns raw API data into the story the page tells. Pure functions only."""

import collections
import datetime as dt
import statistics

DONE = "ACCEPTED"
ACTIVE = {"REGISTERED", "IN_PROGRESS", "IN_REVIEWS"}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def parse_time(value, tz=None):
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return stamp.astimezone(tz)


def _done(projects):
    return [p for p in projects if p["status"] == DONE]


def _dated(projects, tz):
    """Accepted projects that have a completion time, oldest first."""
    rows = [(parse_time(p["completionDateTime"], tz), p)
            for p in _done(projects) if p.get("completionDateTime")]
    return sorted(rows, key=lambda row: row[0])


def project_counts(projects):
    by_type = collections.Counter(p["type"] for p in _done(projects))
    return {
        "done": len(_done(projects)),
        "failed": sum(p["status"] == "FAILED" for p in projects),
        "active": sum(p["status"] in ACTIVE for p in projects),
        "byType": dict(by_type.most_common()),
        "activeTitles": [p["title"] for p in projects
                         if p["status"] in ACTIVE],
        "failedTitles": [p["title"] for p in projects
                         if p["status"] == "FAILED"],
    }


def grades(projects):
    scored = [p for p in _done(projects) if p.get("finalPercentage") is not None]
    if not scored:
        return None
    best = max(scored, key=lambda p: p["finalPercentage"])
    worst = min(scored, key=lambda p: p["finalPercentage"])
    return {
        "average": round(statistics.mean(p["finalPercentage"] for p in scored)),
        "best": {"title": best["title"], "score": best["finalPercentage"]},
        "closest": {"title": worst["title"], "score": worst["finalPercentage"]},
        "over100": sum(p["finalPercentage"] > 100 for p in scored),
        "exactly100": sum(p["finalPercentage"] == 100 for p in scored),
        "max": max(125, best["finalPercentage"]),
        "scores": sorted(p["finalPercentage"] for p in scored),
    }


def _month_range(first, last):
    year, month = first.year, first.month
    while (year, month) <= (last.year, last.month):
        yield f"{year:04d}-{month:02d}"
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def _biggest_week(times):
    """Most completions inside any 7-day window."""
    best = (0, None)
    start = 0
    for end, stamp in enumerate(times):
        while stamp - times[start] > dt.timedelta(days=7):
            start += 1
        if end - start + 1 > best[0]:
            best = (end - start + 1, times[start])
    return best


def timeline(projects, tz=None):
    rows = _dated(projects, tz)
    if not rows:
        return None
    times = [stamp for stamp, _ in rows]
    per_month = collections.Counter(stamp.strftime("%Y-%m") for stamp in times)
    months = [{"month": m, "count": per_month.get(m, 0)}
              for m in _month_range(times[0], times[-1])]
    gaps = [(b - a, a, rows[i + 1][1]["title"])
            for i, (a, b) in enumerate(zip(times, times[1:]))]
    drought = max(gaps, key=lambda gap: gap[0]) if gaps else None
    rush_count, rush_start = _biggest_week(times)
    peak = max(months, key=lambda m: m["count"])
    return {
        "first": {"title": rows[0][1]["title"], "date": times[0].date().isoformat()},
        "latest": {"title": rows[-1][1]["title"],
                   "date": times[-1].date().isoformat()},
        "months": months,
        "peakMonth": peak,
        "drought": drought and {
            "days": drought[0].days,
            "from": drought[1].date().isoformat(),
            "brokenBy": drought[2],
        },
        "rushWeek": {"count": rush_count,
                     "from": rush_start.date().isoformat()},
    }


def _clock_persona(hours):
    total = sum(hours)
    night = sum(hours[h] for h in (22, 23, 0, 1, 2, 3, 4)) / total
    morning = sum(hours[h] for h in range(5, 11)) / total
    if night >= 0.3:
        return "night"
    if morning >= 0.35:
        return "morning"
    return "day"


def clock(projects, tz=None):
    """When projects crossed the finish line. Skipped when the API only
    stores dates, since then every completion sits at midnight UTC."""
    utc = _dated(projects, dt.timezone.utc)
    if not utc or all(s.hour == 0 and s.minute == 0 for s, _ in utc):
        return None
    local = [stamp for stamp, _ in _dated(projects, tz)]
    hours = [0] * 24
    days = [0] * 7
    for stamp in local:
        hours[stamp.hour] += 1
        days[stamp.weekday()] += 1
    return {
        "hours": hours,
        "weekdays": [{"day": d, "count": c} for d, c in zip(WEEKDAYS, days)],
        "peakHour": hours.index(max(hours)),
        "persona": _clock_persona(hours),
    }


def squad(projects, login):
    mates = collections.Counter()
    led = 0
    group_count = 0
    for project in projects:
        members = project.get("teamMembers") or []
        others = [m["login"] for m in members if m["login"] != login]
        if not others:
            continue
        group_count += 1
        mates.update(others)
        led += any(m["login"] == login and m.get("isTeamlead") for m in members)
    if not mates:
        return None
    return {
        "groupProjects": group_count,
        "teamlead": led,
        "uniqueMates": len(mates),
        "mates": [{"login": who, "count": n} for who, n in mates.most_common()],
    }


def courses(course_list, projects):
    """Courses are the platform's project clusters. The course endpoint
    doesn't list its projects, so we rebuild them from each project's
    courseId."""
    if not course_list:
        return None
    inside = collections.defaultdict(list)
    for project in projects:
        if project.get("courseId") is not None:
            inside[project["courseId"]].append(project)
    rows = []
    for course in course_list:
        members = inside.get(course["id"], [])
        rows.append({
            "title": course["title"],
            "status": course["status"],
            "percent": course.get("finalPercentage"),
            "projectsDone": len(_done(members)),
            "projectsSeen": len(members),
            "projects": [p["title"] for p in members],
        })
    rows.sort(key=lambda r: (r["status"] != DONE, -r["projectsDone"]))
    return {
        "done": sum(r["status"] == DONE for r in rows),
        "total": len(rows),
        "list": rows,
    }


def _clean_label(label):
    """'SQL (QA)' -> 'SQL': the suffix only names the track."""
    label = label.strip()
    if label.endswith(")") and " (" in label:
        label = label[:label.rindex(" (")]
    return label


def _unique_branches(nodes):
    """The graph repeats the same projects under every track, e.g.
    'SQL (PM)', 'SQL (QA)', 'SQL - I' share ids. Keep one branch per set
    of ids and drop branches fully contained in a bigger one."""
    branches = []
    for node in nodes:
        keys = frozenset((i["entityType"], i["entityId"]) for i in node["items"])
        if keys:
            branches.append((node["label"], keys))
    # Bigger sets first; among equal sets prefer a label without "(track)".
    branches.sort(key=lambda b: (-len(b[1]), "(" in b[0]))
    kept = []
    for label, keys in branches:
        if not any(keys <= other for _, other in kept):
            kept.append((_clean_label(label), keys))
    return kept


def map_explored(graph, projects, course_list):
    if not graph or not graph.get("nodes"):
        return None
    done = {("PROJECT", p["id"]) for p in _done(projects)}
    done |= {("COURSE", c["id"]) for c in course_list or []
             if c["status"] == DONE}
    kept = _unique_branches(graph["nodes"])
    every = frozenset().union(*(keys for _, keys in kept)) if kept else set()
    branches = [{"label": label, "done": len(keys & done), "total": len(keys)}
                for label, keys in kept]
    cleared = len(every & done)
    return {
        "itemsDone": cleared,
        "itemsTotal": len(every),
        "percent": round(100 * cleared / len(every)) if every else 0,
        "branchesCleared": [b["label"] for b in branches
                            if b["done"] == b["total"]],
        "branches": sorted(branches,
                           key=lambda b: (-b["done"] / b["total"], -b["done"])),
    }


def logtime(history):
    """Relative stats only. The API's unit is a weekly average, so we
    compare weeks with each other instead of claiming total hours."""
    if not history:
        return None
    first_active = next((i for i, w in enumerate(history) if w["hours"]), None)
    if first_active is None:
        return None
    weeks = history[first_active:]
    active = [w for w in weeks if w["hours"] > 0]
    typical = statistics.median(w["hours"] for w in active)
    peak = max(weeks, key=lambda w: w["hours"])
    longest_off = run = 0
    for week in weeks:
        run = run + 1 if week["hours"] == 0 else 0
        longest_off = max(longest_off, run)
    return {
        "weeks": weeks,
        "typical": round(typical, 1),
        "peak": peak,
        "peakRatio": round(peak["hours"] / typical, 1) if typical else None,
        "activeWeeks": len(active),
        "totalWeeks": len(weeks),
        "longestBreak": longest_off,
    }


FEEDBACK_TITLES = {
    "averageVerifierPunctuality": ("Punctuality", "Clockwork"),
    "averageVerifierInterest": ("Interest", "The Curious One"),
    "averageVerifierThoroughness": ("Thoroughness", "The Inspector"),
    "averageVerifierFriendliness": ("Friendliness", "Everyone's Favourite"),
}


def feedback(raw):
    if not raw:
        return None
    rows = [{"key": key, "label": FEEDBACK_TITLES[key][0], "value": raw[key]}
            for key in FEEDBACK_TITLES if raw.get(key) is not None]
    if not rows:
        return None
    top = max(rows, key=lambda r: r["value"])
    return {
        "rows": rows,
        "title": FEEDBACK_TITLES[top["key"]][1],
        "scale": max(4, max(r["value"] for r in rows)),
    }


def skills(raw):
    if not raw:
        return None
    ranked = sorted(raw, key=lambda s: -s["points"])
    return {"top": ranked[:6], "count": len(ranked)}


def badges(raw):
    if not raw:
        return None
    dated = sorted(raw, key=lambda b: b.get("receiptDateTime") or "")
    return {
        "count": len(raw),
        "list": [{"name": b["name"], "icon": b.get("iconUrl"),
                  "date": b.get("receiptDateTime", "")[:10]} for b in dated],
    }


def persona(story):
    """A silly two-part title built from the other slides."""
    clock_word = {"night": "Night Shift", "morning": "Early Bird",
                  "day": "Daylight"}
    adjective = clock_word.get((story.get("clock") or {}).get("persona"),
                               "Steady")
    g = story.get("grades") or {}
    counts = story["projects"]
    if g.get("over100", 0) >= max(3, counts["done"] // 3):
        noun = "Overachiever"
    elif (story.get("squad") or {}).get("uniqueMates", 0) >= 8:
        noun = "Social Butterfly"
    elif counts["failed"] >= 3:
        noun = "Comeback Kid"
    elif counts["done"] >= 20:
        noun = "Project Machine"
    else:
        noun = "Rising Peer"
    return f"{adjective} {noun}"


def build(raw, tz=None):
    projects = raw.get("projects") or []
    login = raw["login"]
    story = {
        "login": login,
        "participant": raw["participant"],
        "fetchedAt": raw.get("fetchedAt"),
        "projects": project_counts(projects),
        "grades": grades(projects),
        "timeline": timeline(projects, tz),
        "clock": clock(projects, tz),
        "squad": squad(projects, login),
        "courses": courses(raw.get("courses"), projects),
        "map": map_explored(raw.get("graph"), projects, raw.get("courses")),
        "logtime": logtime(raw.get("logtime")),
        "feedback": feedback(raw.get("feedback")),
        "skills": skills(raw.get("skills")),
        "badges": badges(raw.get("badges")),
        "points": raw.get("points"),
        "coalition": raw.get("coalition"),
    }
    story["persona"] = persona(story)
    return story
