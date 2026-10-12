import json

import pytest

from dropcurve.cli import main
from dropcurve.events import read_events


def test_synth_writes_a_readable_log(tmp_path, capsys):
    out = tmp_path / "demo.csv"
    assert main(["synth", str(out), "--users", "50", "--walls", "3,6"]) == 0
    assert "from 50 listeners" in capsys.readouterr().out
    events = list(read_events(out))
    assert len({e.user for e in events}) == 50
    assert {e.free for e in events} == {3, 6}


def test_bad_walls_is_a_usage_error(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["synth", str(tmp_path / "x.csv"), "--walls", "five"])
    assert exc.value.code == 2


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    out = tmp_path_factory.mktemp("cli") / "demo.csv"
    main(["synth", str(out), "--users", "1500", "--seed", "3"])
    return str(out)


def test_summary(demo, capsys):
    assert main(["summary", demo]) == 0
    out = capsys.readouterr().out
    assert out.startswith("the-last-heir: 1500 listeners, ")
    assert "median depth" in out


def test_unknown_series_and_missing_file(demo, capsys):
    assert main(["summary", demo, "--series", "nope"]) == 2
    assert "no series 'nope'" in capsys.readouterr().err
    assert main(["summary", "missing.csv"]) == 2


def test_sparkline_scales_to_blocks():
    from dropcurve.cli import sparkline

    assert sparkline([1.0, 0.5, 0.0], width=3) == "█▅▁"
    assert len(sparkline([0.5] * 101)) == 50


def test_curve(demo, capsys):
    assert main(["curve", demo, "6"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "the-last-heir episode 6: share of starters still listening"
    assert lines[2].strip() == "0%  (0:00)  100.0%"
    assert main(["curve", demo, "99"]) == 2


def test_hotspots_lists_the_planted_cliff(demo, capsys):
    assert main(["hotspots", demo]) == 0
    out = capsys.readouterr().out
    assert out.startswith("episode   6    41-42%   3:16-3:21  lost ")
    assert main(["hotspots", demo, "--episode", "3"]) == 0
    assert capsys.readouterr().out.startswith("no hotspots")


def test_funnel_table(demo, capsys):
    assert main(["funnel", demo]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[1].startswith("  1       1500  100.0%")
    assert lines[-1].endswith("  -")  # no next episode to go on to


def test_endings_flags_the_weak_one(demo, capsys):
    assert main(["endings", demo]) == 0
    flagged = [line.split()[0] for line in capsys.readouterr().out.splitlines() if "weak" in line]
    assert flagged == ["9"]


def test_survival_table(demo, capsys):
    assert main(["survival", demo]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("1500 listeners, ")
    assert out[2].startswith("  1     1500")
    assert out[-1].startswith("half of new listeners don't get past episode ")


def test_binge(demo, capsys):
    assert main(["binge", demo]) == 0
    out = capsys.readouterr().out
    assert "listening sessions" in out
    assert "time to next episode    median " in out


def test_cohorts(demo, capsys):
    assert main(["cohorts", demo, "--milestones", "2,5"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ["week", "listeners", "ep", "2", "ep", "5"]
    assert lines[1].startswith("2026-W02")
    assert sum(int(line.split()[1]) for line in lines[1:]) == 1500


def test_paywall(tmp_path, capsys):
    out = str(tmp_path / "walls.csv")
    main(["synth", out, "--users", "3000", "--seed", "11", "--walls", "5,12"])
    capsys.readouterr()
    assert main(["paywall", out]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[0] for line in lines[1:3]] == ["5", "12"]
    assert lines[-1].startswith("5 free episodes earns ")


def test_paywall_without_variants(demo, capsys):
    assert main(["paywall", demo]) == 2
    assert "no paywall variants" in capsys.readouterr().err


def test_paywall_projection_is_labelled_a_model(tmp_path, capsys):
    out = str(tmp_path / "walls.csv")
    main(["synth", out, "--users", "1500", "--seed", "11", "--walls", "4,6"])
    capsys.readouterr()
    assert main(["paywall", out, "--project"]) == 0
    text = capsys.readouterr().out
    assert "Model, not a measurement" in text
    walls = [line.split()[3] for line in text.splitlines() if "wall after episode" in line]
    assert walls == ["1", "2", "3", "4", "5"]


def test_episodes_flags_the_slow_one(demo, capsys):
    assert main(["episodes", demo]) == 0
    lines = capsys.readouterr().out.splitlines()
    flagged = [line.split()[0] for line in lines if "neighbours suggest" in line]
    assert "14" in flagged
    assert len(lines) == 31


@pytest.mark.parametrize(
    "command",
    ["summary", "episodes", "hotspots", "funnel", "endings", "survival", "binge", "cohorts"],
)
def test_every_command_can_print_json(demo, capsys, command):
    assert main([command, demo, "--json"]) == 0
    json.loads(capsys.readouterr().out)


def test_json_includes_computed_fields(demo, capsys):
    main(["endings", demo, "--json"])
    ends = json.loads(capsys.readouterr().out)
    weak = [e for e in ends if e["verdict"] == "weak"]
    assert weak[0]["episode"] == 9 and 0 < weak[0]["pull"] < 0.5


def test_since_and_until_filter_by_time(demo, capsys):
    main(["summary", demo, "--json"])
    everyone = json.loads(capsys.readouterr().out)["listeners"]
    main(["summary", demo, "--json", "--until", "2026-01-12"])
    first_week = json.loads(capsys.readouterr().out)["listeners"]
    main(["summary", demo, "--json", "--since", "2026-01-12"])
    later = json.loads(capsys.readouterr().out)["listeners"]
    assert 0 < first_week < everyone
    assert 0 < later < everyone
    with pytest.raises(SystemExit):
        main(["summary", demo, "--since", "last tuesday"])


def test_catalog_supplies_missing_lengths(tmp_path, capsys):
    events = tmp_path / "e.csv"
    events.write_text(
        "user,series,episode,position,ts\n"
        "a,s,1,300,2026-01-05T10:00:00Z\n"
        "b,s,1,600,2026-01-05T10:00:00Z\n"
    )
    assert main(["episodes", str(events), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["episodes"][0]["starters"] == 0
    catalog = tmp_path / "c.csv"
    catalog.write_text("series,episode,duration\ns,1,600\n")
    assert main(["episodes", str(events), "--json", "--catalog", str(catalog)]) == 0
    ep = json.loads(capsys.readouterr().out)["episodes"][0]
    assert ep["starters"] == 2 and ep["finishers"] == 1


def test_max_errors(tmp_path, capsys):
    events = tmp_path / "e.csv"
    events.write_text(
        "user,series,episode,position,duration,ts\n"
        "a,s,1,300,600,2026-01-05T10:00:00Z\n"
        "b,s,0,600,600,2026-01-05T10:00:00Z\n"
        "c,s,1,oops,600,2026-01-05T10:00:00Z\n"
    )
    assert main(["summary", str(events)]) == 2
    assert ":3: episode 0" in capsys.readouterr().err
    assert main(["summary", str(events), "--max-errors", "1"]) == 2
    assert "2 bad rows, more than --max-errors 1" in capsys.readouterr().err
    assert main(["summary", str(events), "--max-errors", "5"]) == 0
    out = capsys.readouterr()
    assert out.out.startswith("s: 1 listeners")
    assert out.err.count("skipped") == 2


def test_report_names_the_planted_problems(demo, tmp_path, capsys):
    out = tmp_path / "r.html"
    assert main(["report", demo, "-o", str(out)]) == 0
    html = out.read_text()
    assert html.startswith("<!doctype html>")
    assert "<h1>the-last-heir</h1>" in html
    for finding in ("episode 6</td><td>drop at 3:16", "episode 9</td><td>weak ending"):
        assert finding in html
    assert "<h2>Inside episode 6</h2>" in html
    assert "Paywall test" not in html


def test_export_writes_every_curve(demo, capsys):
    import csv
    import io

    assert main(["export", demo]) == 0
    rows = list(csv.DictReader(io.StringIO(capsys.readouterr().out)))
    assert len(rows) == 30 * 101
    first = rows[0]
    assert (first["episode"], first["percent_in"], first["share_listening"]) == ("1", "0", "1.0000")
