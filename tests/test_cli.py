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
