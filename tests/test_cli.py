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
