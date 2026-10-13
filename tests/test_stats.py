import datetime as dt
import unittest

from s21 import demo, stats

UTC = dt.timezone.utc


def project(pid, status="ACCEPTED", when=None, score=100, team=None, course=None):
    return {"id": pid, "title": f"P{pid}", "type": "GROUP" if team else "INDIVIDUAL",
            "status": status, "finalPercentage": score, "completionDateTime": when,
            "teamMembers": team, "courseId": course}


class StatsTest(unittest.TestCase):
    def test_demo_builds_every_section(self):
        story = stats.build(demo.raw_demo(), UTC)
        for key in ("grades", "timeline", "clock", "squad", "courses", "map",
                    "logtime", "feedback", "skills", "badges"):
            self.assertIsNotNone(story[key], key)
        self.assertTrue(story["persona"])

    def test_empty_student_still_builds(self):
        raw = {"login": "new", "participant": {"login": "new"}, "projects": [],
               "courses": [], "skills": [], "badges": [], "feedback": None,
               "graph": None, "logtime": [{"week": "2026-01-05", "hours": 0}]}
        story = stats.build(raw, UTC)
        self.assertEqual(story["projects"]["done"], 0)
        for key in ("grades", "timeline", "clock", "squad", "logtime", "map"):
            self.assertIsNone(story[key], key)

    def test_counts_and_grades(self):
        rows = [project(1, score=125, when="2026-01-01T10:00:00Z"),
                project(2, score=80, when="2026-01-02T10:00:00Z"),
                project(3, status="FAILED", score=0),
                project(4, status="IN_REVIEWS", score=None)]
        counts = stats.project_counts(rows)
        self.assertEqual((counts["done"], counts["failed"], counts["active"]), (2, 1, 1))
        grades = stats.grades(rows)
        self.assertEqual(grades["best"]["score"], 125)
        self.assertEqual(grades["closest"]["score"], 80)
        self.assertEqual(grades["over100"], 1)

    def test_clock_skipped_for_date_only_timestamps(self):
        rows = [project(i, when=f"2026-01-0{i}T00:00:00Z") for i in range(1, 5)]
        self.assertIsNone(stats.clock(rows, UTC))

    def test_timeline_fills_empty_months_and_finds_drought(self):
        rows = [project(1, when="2025-11-03T10:00:00Z"),
                project(2, when="2026-02-01T10:00:00Z")]
        line = stats.timeline(rows, UTC)
        self.assertEqual([m["month"] for m in line["months"]],
                         ["2025-11", "2025-12", "2026-01", "2026-02"])
        self.assertEqual(line["drought"]["days"], 90)
        self.assertEqual(line["drought"]["brokenBy"], "P2")

    def test_rush_week(self):
        times = [dt.datetime(2026, 1, d, tzinfo=UTC) for d in (1, 3, 6, 20)]
        self.assertEqual(stats._biggest_week(times)[0], 3)

    def test_squad_skips_self_and_counts_lead(self):
        me = {"login": "me", "isTeamlead": True}
        rows = [project(1, team=[me, {"login": "a"}]),
                project(2, team=[{"login": "me"}, {"login": "a"}, {"login": "b"}])]
        squad = stats.squad(rows, "me")
        self.assertEqual(squad["mates"], [{"login": "a", "count": 2},
                                          {"login": "b", "count": 1}])
        self.assertEqual(squad["teamlead"], 1)

    def test_map_counts_cleared_branches(self):
        graph = {"nodes": [
            {"label": "A", "items": [{"entityType": "PROJECT", "entityId": 1}]},
            {"label": "B", "items": [{"entityType": "PROJECT", "entityId": 2},
                                     {"entityType": "COURSE", "entityId": 9}]}]}
        explored = stats.map_explored(graph, [project(1), project(2)], [])
        self.assertEqual(explored["branchesCleared"], ["A"])
        self.assertEqual(explored["percent"], 67)

    def test_map_merges_track_copies_and_subsets(self):
        def node(label, ids):
            return {"label": label, "items": [
                {"entityType": "PROJECT", "entityId": i} for i in ids]}
        graph = {"nodes": [node("SQL (PM)", [1, 2]), node("SQL (QA)", [1, 2]),
                           node("SQL - I", [1, 2]), node("DevOps (CPP)", [3, 4, 5]),
                           node("DevOps-II", [3, 4]), node("Java Bootcamp (QA)", [6])]}
        explored = stats.map_explored(graph, [project(1)], [])
        self.assertEqual(sorted(b["label"] for b in explored["branches"]),
                         ["DevOps", "Java Bootcamp", "SQL - I"])
        self.assertEqual(explored["itemsTotal"], 6)

    def test_logtime_trims_weeks_before_start(self):
        history = [{"week": f"w{i}", "hours": h} for i, h in enumerate([0, 0, 4, 0, 8])]
        log = stats.logtime(history)
        self.assertEqual(log["totalWeeks"], 3)
        self.assertEqual(log["peak"]["hours"], 8)
        self.assertEqual(log["longestBreak"], 1)


if __name__ == "__main__":
    unittest.main()
