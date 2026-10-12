# dropcurve

Find where listeners drop off in serialized audio, and what that means for the paywall.

Audio-series apps sell long stories in short episodes: the first few free,
the rest for coins. Everything depends on people pressing play on the next
episode, so the useful questions are specific. Where inside an episode do
people leave? Which endings fail to pull them into the next one? Which
episode is quietly losing the audience? And how many free episodes should
come before the wall?

dropcurve answers those from the player's progress pings. It is pure Python
with no dependencies, reads CSV or JSONL, and prints tables, JSON, or one
HTML page.

## Quickstart

```sh
uv tool install git+https://github.com/Rakshit-gen/dropcurve
dropcurve synth demo.csv          # a demo log with known problems planted in it
dropcurve summary demo.csv
dropcurve report demo.csv -o report.html
```

The demo log has an ad break 41% into episode 6, a weak ending on episode 9
and a slow episode 14. This is what dropcurve says about it:

```
$ dropcurve summary demo.csv
the-last-heir: 2000 listeners, 30 episodes
  finished episode 1      91.5%
  started the last one    0.1%
  median depth            half don't get past episode 5

$ dropcurve hotspots demo.csv
episode   6    41-42%   3:16-3:21  lost 11.8% of starters (101x the usual rate)

$ dropcurve endings demo.csv
 ep  finishers  started next within 24h  verdict
  ...
  8        465   74.6%  (70-78%)
  9        379   38.8%  (34-44%)          weak (z = -15.6)
 10        164   78.0%  (71-84%)
  ...

$ dropcurve episodes demo.csv
 ep  starters  finished (95% range)  bounced  median heard
  ...
  6       856     80.1% (77-83%)     0.5%          100%  low: neighbours suggest 90.9%
  ...
 14        79     55.7% (45-66%)     3.8%          100%  low: neighbours suggest 86.7%
```

Episode 6 shows up twice, and rightly: the people lost at its ad break never
finish it.

## Your own data

One row per progress ping. Column names are matched loosely (`user_id`,
`show`, `position_s`, `timestamp` and so on all work):

| column | required | meaning |
|---|---|---|
| user | yes | listener id |
| series | yes | series id |
| episode | yes | episode number, from 1 |
| position | yes | seconds into the episode |
| ts | yes | ISO 8601 time, or Unix seconds or milliseconds |
| duration | no | episode length in seconds; or pass `--catalog lengths.csv` |
| kind | no | `play` (default) or `unlock` for a paid unlock |
| coins | no | what an unlock cost |
| free_episodes | no | this listener's paywall variant |

Every analysis command takes `--series`, `--since`, `--until`, `--catalog`,
`--max-errors` (skip a few bad rows instead of stopping) and `--json`.

## Commands

| command | answers |
|---|---|
| `summary` | the headline numbers |
| `curve FILE EPISODE` | the retention curve inside one episode |
| `hotspots` | moments where people leave much faster than usual |
| `episodes` | completion and bounce per episode, with odd episodes flagged |
| `funnel` | how far into the series people get, and who goes on |
| `endings` | which endings pull people into the next episode within 24 hours |
| `survival` | Kaplan-Meier depth, counting still-active listeners fairly |
| `binge` | episodes per sitting and time between episodes |
| `cohorts` | how far people get, by the week they arrived |
| `paywall` | which free-episode variant earns most per new listener |
| `report` | all of the above as one HTML page |
| `export` | every retention curve as CSV |
| `synth` | demo data with planted problems |

## Paywall tests

If listeners were split across free-episode counts, `paywall` compares the
variants by coins per new listener. That counts the people a wall loses as
well as the ones it converts:

```
$ dropcurve synth walls.csv --users 6000 --seed 11 --walls 5,8,12
$ dropcurve paywall walls.csv
free eps  starters  met wall  paid  conversion (95% range)  coins per starter
       5      1990       919   269       29.3% (26-32%)          5.66 +- 0.78
       8      1985       482   205       42.5% (38-47%)          3.15 +- 0.59
      12      2025       107    75       70.1% (61-78%)          1.26 +- 0.35
5 free episodes earns 5.66 coins per new listener, against 3.15 with 8 free (z = 5.0)
```

The later wall converts better and still loses, because far fewer people get
that far. `--project` adds a model of untested wall positions, labelled as a
model.

How each number is defined, and the thresholds behind every flag, are in
[docs/methodology.md](docs/methodology.md).

## Measured vs Claimed

| Claim | Value | How measured | Date |
|---|---|---|---|
| Speed | 401,984 events read and built in 2.03 s (about 198k events/s) | `bench/bench.py`: 20,000 synthetic listeners, 29 MB CSV, Apple M4, Python 3.13 | 2026-10-12 |
| Report | full HTML report for those 20,000 listeners in 0.81 s | same run | 2026-10-12 |
| Memory | 126 MB peak RSS, including generating the log | same run, `ru_maxrss` | 2026-10-12 |
| Finds planted problems | ad break, weak ending, slow episode, best paywall | `tests/test_planted.py`, 6,000 listeners | 2026-10-12 |

## Status

Works: everything above, with 96 tests, on Python 3.11 to 3.13.

Not done: reading straight from a warehouse (export to CSV or JSONL first),
and more than one paywall test per series. Everything is held in memory as
one view per listener per episode; the 105,065 views in the benchmark fit in
the 126 MB above.
