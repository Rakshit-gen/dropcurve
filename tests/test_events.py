import pytest

from dropcurve.events import read_csv


def write(tmp_path, text, name="events.csv"):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_reads_rows(tmp_path):
    p = write(
        tmp_path,
        "user_id,series_id,episode,position_s,duration_s,timestamp\n"
        "u1,s1,1,120.5,600,2026-01-05T10:00:00+00:00\n"
        "u1,s1,1,240,,2026-01-05T10:02:00+00:00\n",
    )
    events = list(read_csv(p))
    assert len(events) == 2
    assert events[0].user == "u1" and events[0].episode == 1
    assert events[0].position == 120.5 and events[0].duration == 600
    assert events[1].duration is None


def test_missing_column(tmp_path):
    p = write(tmp_path, "user,series,episode,ts\nu1,s1,1,2026-01-05T10:00:00\n")
    with pytest.raises(ValueError, match="position"):
        list(read_csv(p))
