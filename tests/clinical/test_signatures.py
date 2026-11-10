"""A doctor's signature: drawn or uploaded, kept per version, shown on notes signed after it, never on drafts."""
import struct
import zlib

from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import clinic, join, member, started_visit


def png(shade=0):
    """A tiny real PNG (4x2, grey+alpha)."""
    raw = b"".join(b"\x00" + bytes([shade, 255] * 4) for _ in range(2))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 2, 8, 4, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def upload(c, h, data):
    return c.put("/api/me/signature", headers=h, files={"file": ("signature.png", data, "image/png")})


def signed(c, h, doc, name):
    v = started_visit(c, h, doc, name)
    c.put(f"/api/visits/{v['id']}/text", headers=h, json={"text": "Fever for two days.", "rev": 0})
    n = c.post(f"/api/visits/{v['id']}/note/draft", headers=h).json()
    return c.post(f"/api/notes/{n['id']}/sign", headers=h).json()


def test_signature_on_notes_signed_after_it_and_each_note_keeps_its_own():
    with TestClient(app) as c:
        h, doc = clinic(c, "sig@x.in")
        before = signed(c, h, doc, "Before")
        assert before["signature_id"] is None                                   # signed before any signature: none
        assert upload(c, h, b"not an image").status_code == 422
        first = upload(c, h, png(0)).json()["signature_id"]
        assert c.get("/api/me", headers=h).json()["member"]["has_signature"] is True
        one = signed(c, h, doc, "One")
        assert one["signature_id"] == first
        second = upload(c, h, png(40)).json()["signature_id"]
        two = signed(c, h, doc, "Two")
        assert two["signature_id"] == second and c.get(f"/api/visits/{one['visit_id']}", headers=h).json()["note"]["signature_id"] == first
        assert c.get(f"/api/signatures/{first}", headers=h).content == png(0)  # the old version is kept for old notes
        assert "data:image/png;base64," in c.get(f"/api/notes/{one['id']}/print", headers=h).text
        assert "data:image/png;base64," not in c.get(f"/api/notes/{before['id']}/print", headers=h).text
        with_sig = c.get(f"/api/notes/{one['id']}/pdf", headers=h).content
        assert with_sig.startswith(b"%PDF") and len(with_sig) > len(c.get(f"/api/notes/{before['id']}/pdf", headers=h).content)
        c.delete("/api/me/signature", headers=h)
        assert signed(c, h, doc, "After")["signature_id"] is None
        assert c.get(f"/api/signatures/{first}", headers=h).status_code == 200  # removing stops new use only


def test_only_the_doctor_sets_their_own_and_other_clinics_cannot_see_it():
    with TestClient(app) as c:
        h, doc = clinic(c, "sig2@x.in")
        sid = upload(c, h, png()).json()["signature_id"]
        desk = join(c, member(c, h, "Desk", "sig-desk@x.in", "staff", ["operations", "patients"])["invite_code"])
        assert upload(c, desk, png()).status_code == 403
        other, _ = clinic(c, "sig3@x.in")
        assert c.get(f"/api/signatures/{sid}", headers=other).status_code == 404
        assert c.get(f"/api/signatures/{sid}").status_code == 401
