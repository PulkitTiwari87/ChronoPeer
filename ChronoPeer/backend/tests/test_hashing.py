import hashlib

from backend.services.hashing import sha256_bytes, sha256_file, verify_stored

from .conftest import SAMPLE_CSV, make_case, upload


def test_sha256_known_vector(tmp_path):
    assert sha256_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc")
    assert sha256_file(p) == sha256_bytes(b"abc")


def test_verify_stored_detects_match_mismatch_and_missing(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"original")
    digest = sha256_bytes(b"original")
    assert verify_stored(p, digest) == "MATCH"
    p.write_bytes(b"tampered")
    assert verify_stored(p, digest) == "MISMATCH"
    assert verify_stored(tmp_path / "gone.bin", digest) == "MISSING"


def test_verify_endpoint_rechecks_the_stored_file(client):
    cid = make_case(client)
    body = upload(client, cid, SAMPLE_CSV).json()
    ev = client.get(f"/api/cases/{cid}/evidence").json()[0]
    assert ev["sha256"] == body["sha256"] == hashlib.sha256(SAMPLE_CSV.encode()).hexdigest()
    assert client.get(f"/api/evidence/{ev['id']}/verify").json()["result"] == "MATCH"
    stored = client.settings.storage_dir / str(cid) / f"{ev['sha256']}.csv"
    stored.write_bytes(stored.read_bytes() + b"x")  # simulate tampering after import
    assert client.get(f"/api/evidence/{ev['id']}/verify").json()["result"] == "MISMATCH"
