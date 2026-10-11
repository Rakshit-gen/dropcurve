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


@pytest.mark.parametrize(
    "raw",
    [
        "2026-01-05T10:00:00Z",
        "2026-01-05T10:00:00+00:00",
        "2026-01-05 10:00:00",
        "1767607200",
        "1767607200000",
        1767607200.0,
    ],
)
def test_timestamp_formats(raw):
    from datetime import UTC, datetime

    from dropcurve.events import parse_ts

    assert parse_ts(raw) == datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


def test_offset_is_kept():
    from dropcurve.events import parse_ts

    assert parse_ts("2026-01-05T15:30:00+05:30") == parse_ts("2026-01-05T10:00:00Z")


def test_jsonl(tmp_path):
    from dropcurve.events import read_events

    p = write(
        tmp_path,
        '{"uid": "u1", "show": "s1", "ep": 2, "pos": 30, "length": null, '
        '"time": 1767607200}\n\n'
        '{"uid": "u2", "show": "s1", "ep": 2, "pos": 45.5, "length": 900, '
        '"time": 1767607260}\n',
        name="events.jsonl",
    )
    events = list(read_events(p))
    assert [e.user for e in events] == ["u1", "u2"]
    assert events[0].duration is None and events[1].duration == 900
