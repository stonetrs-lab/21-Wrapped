"""Fake but plausible raw data, for trying the page without credentials."""

import datetime as dt
import random

COURSES = [
    (1001, "C Core", ["C2_SimpleBashUtils", "C3_s21_string+", "C4_s21_math",
                      "C5_s21_decimal", "C6_s21_matrix", "C7_SmartCalc_v1.0",
                      "C8_3DViewer_v1.0", "C7_BrickGame_v1.0"]),
    (1002, "DevOps Basics", ["DO1_Linux", "DO2_LinuxNetwork",
                             "DO3_LinuxMonitoring", "DO4_LinuxMonitoring_v2.0",
                             "DO5_SimpleDocker"]),
    (1003, "SQL Bootcamp", ["SQL_Day00", "SQL_Day01", "SQL_Day02",
                            "SQL_Day03", "SQL_Day04"]),
    (1004, "Python Basics", ["AP1_Py_T01", "AP1_Py_T02", "AP1_Py_T03"]),
]
GROUP = {"C3_s21_string+", "C5_s21_decimal", "DO5_SimpleDocker", "SQL_Day04"}
PEERS = ["wobbledo", "karenmar", "pinkyfla", "tulipmor", "jessicaw",
         "ozzybrig", "hermioni", "lambdaxx"]
SKILLS = ["Algorithms", "C", "Linux", "Team work", "Shell / Bash", "DB & Data",
          "Code Review", "Structured programming", "Types and data structures",
          "Python"]


def _project(rng, pid, title, course_id, when, login, status):
    team = None
    if title in GROUP:
        mates = rng.sample(PEERS[:5], 2)
        team = [{"login": login, "isTeamlead": rng.random() < 0.4}] + [
            {"login": m, "isTeamlead": False} for m in mates]
    done = status == "ACCEPTED"
    return {
        "id": pid, "title": title, "courseId": course_id,
        "type": "GROUP" if team else "INDIVIDUAL", "status": status,
        "finalPercentage": rng.choice([88, 100, 100, 100, 110, 120, 125])
        if done else (0 if status == "FAILED" else None),
        "completionDateTime": when.strftime("%Y-%m-%dT%H:%M:%SZ")
        if done or status == "FAILED" else None,
        "teamMembers": team,
    }


def _projects(rng, login, start):
    rows = []
    when = start
    statuses = {"C8_3DViewer_v1.0": "IN_PROGRESS", "SQL_Day03": "FAILED",
                "AP1_Py_T03": "IN_REVIEWS", "C7_BrickGame_v1.0": "IN_PROGRESS"}
    for course_id, _, titles in COURSES:
        for title in titles:
            when += dt.timedelta(days=rng.choice([3, 5, 8, 12, 15, 40]),
                                 hours=rng.choice([0, 2, 9, 13, 15, 22]),
                                 minutes=rng.randrange(60))
            pid = 20000 + len(rows)
            status = statuses.get(title, "ACCEPTED")
            rows.append(_project(rng, pid, title, course_id, when, login, status))
    for i, title in enumerate(["Exam C 1", "Exam C 2", "Exam SQL"]):
        rows.append({"id": 30000 + i, "title": title, "courseId": None,
                     "type": "EXAM", "status": "ACCEPTED",
                     "finalPercentage": rng.choice([80, 100]),
                     "completionDateTime": (start + dt.timedelta(days=60 * (i + 1),
                                            hours=11)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "teamMembers": None})
    return rows


def _courses(projects):
    rows = []
    for course_id, title, _ in COURSES:
        inside = [p for p in projects if p["courseId"] == course_id]
        done = all(p["status"] == "ACCEPTED" for p in inside)
        rows.append({"id": course_id, "title": title,
                     "status": "ACCEPTED" if done else "IN_PROGRESS",
                     "finalPercentage": 100 if done else None,
                     "completionDateTime": None})
    return rows


def _graph(projects):
    nodes = []
    for course_id, title, _ in COURSES:
        items = [{"id": f"n{p['id']}", "code": p["title"], "handles": [],
                  "entityType": "PROJECT", "entityId": p["id"]}
                 for p in projects if p["courseId"] == course_id]
        nodes.append({"id": f"c{course_id}", "label": title, "items": items})
    nodes.append({"id": "cpp", "label": "CPP", "items": [
        {"id": f"cpp{i}", "code": f"CPP{i}", "handles": [],
         "entityType": "PROJECT", "entityId": 40000 + i} for i in range(1, 6)]})
    return {"nodes": nodes, "edges": []}


def _logtime(rng, weeks):
    monday = dt.date.today() - dt.timedelta(days=dt.date.today().weekday())
    history = []
    for back in range(weeks - 1, -1, -1):
        week = monday - dt.timedelta(weeks=back)
        summer = week.month in (7, 8)
        hours = 0.0 if summer and rng.random() < 0.6 else round(
            max(0.0, rng.gauss(5.5, 2.2)), 2)
        history.append({"week": week.isoformat(), "hours": hours})
    return history


def raw_demo(login="demo", weeks=52, seed=21):
    rng = random.Random(seed)
    start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=430)
    projects = _projects(rng, login, start)
    return {
        "login": login,
        "fetchedAt": dt.datetime.now().isoformat(),
        "participant": {"login": login, "className": "25_10_MSK",
                        "parallelName": "Core program", "status": "ACTIVE",
                        "campus": {"id": "x", "shortName": "Moscow"}},
        "projects": projects,
        "courses": _courses(projects),
        "skills": [{"name": s, "points": rng.randrange(40, 900)} for s in SKILLS],
        "badges": [{"name": n, "iconUrl": None,
                    "receiptDateTime": (start + dt.timedelta(days=30 * i)
                                        ).strftime("%Y-%m-%dT%H:%M:%SZ")}
                   for i, n in enumerate(["Piscine survivor", "First blood",
                                          "Helping hand", "Night owl",
                                          "Reviewer of the month"])],
        "points": {"peerReviewPoints": 7, "codeReviewPoints": 3, "coins": 420},
        "feedback": {"averageVerifierPunctuality": 3.6,
                     "averageVerifierInterest": 3.2,
                     "averageVerifierThoroughness": 3.9,
                     "averageVerifierFriendliness": 3.8},
        "coalition": {"coalitionId": 7, "name": "Capybaras", "rank": 42},
        "graph": _graph(projects),
        "logtime": _logtime(rng, weeks),
    }
