import hashlib, hmac
from mcp_server import server as ws

def _tok(aid, payload, secret=b"test-secret"):
    return hmac.new(secret, f"{aid}:{ws.payload_sha256(payload)}".encode(), hashlib.sha256).hexdigest()

def test_valid_write_then_replay_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "DB_PATH", tmp_path / "w.db"); monkeypatch.setattr(ws, "SECRET", b"test-secret")
    p = {"document": "support-answers-log", "title": "t", "body": "approved text"}
    import json
    assert json.loads(ws.append_doc_entry(1, **p, approval_token=_tok(1, p)))["ok"]
    assert "replay" in json.loads(ws.append_doc_entry(1, **p, approval_token=_tok(1, p)))["error"]

def test_tampered_payload_and_wrong_action_refused(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(ws, "DB_PATH", tmp_path / "w.db"); monkeypatch.setattr(ws, "SECRET", b"test-secret")
    p = {"to": "Product Team", "subject": "s", "body": "b"}
    tok = _tok(7, p)
    assert not json.loads(ws.create_email_draft(7, p["to"], p["subject"], "tampered", tok))["ok"]
    assert not json.loads(ws.create_email_draft(8, **p, approval_token=tok))["ok"]   # token is bound to action 7
    r = json.loads(ws.create_email_draft(7, **p, approval_token=tok))
    assert r["ok"] and r["sent"] is False

def test_pii_content_refused(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(ws, "DB_PATH", tmp_path / "w.db"); monkeypatch.setattr(ws, "SECRET", b"test-secret")
    p = {"document": "support-answers-log", "title": "t", "body": "customer PAN ABCPK1234D"}
    assert not json.loads(ws.append_doc_entry(3, **p, approval_token=_tok(3, p)))["ok"]

def test_no_send_tool():
    assert not any("send" in n for n in dir(ws) if not n.startswith("_") and callable(getattr(ws, n)) and n != "server")
