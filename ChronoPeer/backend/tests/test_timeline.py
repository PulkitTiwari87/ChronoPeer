from backend.services.timestamp_normalizer import normalize, parse_assumed_tz

from .conftest import HEADER, make_case, refs, upload

SHUFFLED = (
    HEADER
    + "2024-01-15T09:35:00Z,USB,Disconnected,USB,EV004\n"
    + "2024-01-15T09:02:00Z,LOGIN,Login,Log,EV001\n"
    + "2024-01-15T09:19:00Z,FILE_ACCESS,Doc,FS,EV003\n"
    + "2024-01-15T09:15:00Z,USB,Connected,USB,EV002\n"
)


def test_chronological_sorting_and_descending_order(client):
    cid = make_case(client)
    upload(client, cid, SHUFFLED)
    assert refs(client, cid) == ["EV001", "EV002", "EV003", "EV004"]
    assert refs(client, cid, order="desc") == ["EV004", "EV003", "EV002", "EV001"]


def test_identical_timestamps_break_ties_naturally_not_alphabetically(client):
    cid = make_case(client)
    ts = "2024-01-15T09:00:00Z"
    upload(client, cid, HEADER + f"{ts},A,x,S,EV10\n{ts},A,x,S,EV2\n{ts},A,x,S,EV1\n")
    assert refs(client, cid) == ["EV1", "EV2", "EV10"]


def test_different_timezones_normalise_to_utc(client):
    cid = make_case(client)
    upload(
        client, cid,
        HEADER + "2024-01-15T09:30:00Z,A,x,S,B\n2024-01-15T10:00:00+01:00,A,x,S,C\n2024-01-15T04:00:00-05:00,A,x,S,A\n",
    )
    events = client.get(f"/api/cases/{cid}/timeline").json()["events"]
    assert [e["artifact_reference"] for e in events] == ["A", "C", "B"]  # A and C are both 09:00Z
    assert [e["event_time_utc"] for e in events] == ["2024-01-15T09:00:00.000Z"] * 2 + ["2024-01-15T09:30:00.000Z"]
    assert {e["timezone_status"] for e in events} == {"known"}


def test_unknown_timezone_is_never_converted_and_sorts_after_known_events(client):
    cid = make_case(client)
    upload(client, cid, HEADER + "2024-01-15 08:00:00,A,naive late clock,S,N2\n2024-01-15 07:00:00,A,naive early clock,S,N1\n2024-01-15T12:00:00Z,A,known,S,K1\n")
    events = client.get(f"/api/cases/{cid}/timeline").json()["events"]
    assert [e["artifact_reference"] for e in events] == ["K1", "N1", "N2"]
    naive = events[1]
    assert naive["timezone_status"] == "unknown" and naive["event_time_utc"] is None
    assert naive["event_time_original"] == "2024-01-15 07:00:00" and "not converted" in naive["flag"]
    assert client.get(f"/api/cases/{cid}/timeline").json()["summary"]["by_timezone_status"]["unknown"] == 2


def test_assumed_timezone_is_recorded_as_assumed(client):
    cid = make_case(client)
    r = upload(client, cid, HEADER + "2024-01-15 10:00:00,A,x,S,N1\n", tz="+05:30")
    assert r.status_code == 201 and r.json()["by_timezone_status"] == {"assumed": 1}
    e = client.get(f"/api/cases/{cid}/timeline").json()["events"][0]
    assert e["timezone_status"] == "assumed" and e["event_time_utc"] == "2024-01-15T04:30:00.000Z"


def test_invalid_assumed_timezone_is_rejected(client):
    cid = make_case(client)
    assert upload(client, cid, HEADER + "2024-01-15 10:00:00,A,x,S,N1\n", tz="Mars/Phobos").status_code == 422


def test_missing_and_invalid_timestamps_are_flagged_and_last(client):
    cid = make_case(client)
    upload(client, cid, HEADER + ",A,no time,S,M1\nnot-a-date,A,bad time,S,M2\n2024-01-15T09:00:00Z,A,fine,S,K1\n")
    events = client.get(f"/api/cases/{cid}/timeline").json()["events"]
    assert [e["artifact_reference"] for e in events] == ["K1", "M1", "M2"]
    assert [e["timezone_status"] for e in events] == ["known", "missing", "invalid"]
    assert all(e["flag"] for e in events[1:])


def test_same_input_gives_the_same_order_every_time(client):
    a, b = make_case(client, "A"), make_case(client, "B")
    upload(client, a, SHUFFLED)
    upload(client, b, SHUFFLED)
    assert refs(client, a) == refs(client, b) == ["EV001", "EV002", "EV003", "EV004"]


def test_normalizer_unit_cases():
    assert normalize("2024-01-15T09:00:00Z").status == "known"
    assert normalize("2024-01-15 09:00:00.250").status == "unknown"
    assert normalize("2024-01-15 09:00:00").utc is None  # no local-time guessing
    assert normalize("").status == "missing" and normalize(None).status == "missing"
    assert normalize("yesterday").status == "invalid"
    assert normalize("2024-01-15 09:00:00", parse_assumed_tz("UTC")).status == "assumed"
