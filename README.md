# 21😭wrapped

A Spotify-Wrapped-style recap of your School 21 life, built from the
[School 21 Open API](https://platform.21-school.ru/services/21-school/api/swagger).
No XP anywhere: it's built from projects, grades, teammates, courses, the project map,
weekly logtime, peer feedback, skills, badges and coins.

Python 3 stdlib only. No pip installs.

## Run

```sh
python3 wrapped.py --demo --open        # try it with fake data
python3 wrapped.py --open               # your Wrapped
python3 wrapped.py somepeer --open      # a peer's Wrapped (no project-map slide)
python3 wrapped.py --offline mylogin    # re-render from cache/, no API calls
```

Put your login and password in `credentials.env` (gitignored, chmod 600; see
`credentials.env.example`). `S21_LOGIN` / `S21_PASSWORD` env vars override it, and anything
missing is prompted for. The password only goes to `auth.21-school.ru`; the token it returns is
kept in `cache/token.json` and reused until it expires.

Raw API responses are cached in `cache/<login>.json` and the page goes to
`out/<login>-wrapped.html`. Both folders are gitignored because they hold personal data.

The API allows roughly one request every few seconds, so the first run spends most of its time
on logtime (one request per week). Finished weeks are reused from the cache on later runs, so
re-runs only fetch the newest weeks. `--weeks 20` shortens the first run.

`.claude/settings.json` denies Claude Code reads of `credentials.env` and `cache/token.json`
when Claude Code is started in this folder.

Navigation: tap or click the right side (or press →/space) to go forward, the left side (or ←)
to go back, or use the progress bar at the top. Hover or tap charts for exact values.

## Slides

| Slide | Source |
|---|---|
| Projects passed, split into solo/group/exams | `/participants/{login}/projects` |
| Busiest month, speedrun week, great drought, first project | project `completionDateTime` |
| Average grade, best, closest call | project `finalPercentage` |
| Still cooking / unfinished business | in-progress and failed projects |
| Night owl or early bird | hour of each completion, local time (skipped if the API only stores dates) |
| Ride-or-die and every other teammate | `teamMembers` on group projects |
| Course clusters | `/courses`, with projects grouped by their `courseId` |
| Project map: passed projects per branch, also for peers | `/graph` nodes. Course nodes are opened up into their projects, branches sharing a project (`SQL (PM)`/`SQL - I`, `DO - I`/`DevOps-I`) are merged, renamed copies are collapsed. A peer's cache without a graph borrows yours as the layout |
| Time on campus | `/logtime?date=`, sampled once per week (`--weeks`, default 52) |
| Peers' verdict | `/feedback` |
| Top skills, badges, coins, review points, coalition rank | `/skills`, `/badges`, `/points`, `/coalition` |
| Summary card and persona | all of the above |

Any endpoint that fails just drops its slide.

## Test

```sh
python3 -m unittest -v
```
