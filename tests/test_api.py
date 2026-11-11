from fastapi.testclient import TestClient

from app.main import app


def client():
    return TestClient(app)


def test_index_and_health():
    c = client()
    assert c.get("/").status_code == 200
    assert c.get("/health").json()["status"] == "ok"


def test_each_visitor_has_its_own_sandbox():
    a, b = client(), client()
    pending = [e for e in a.get("/api/emails?view=queue").json() if "auroranet" in e["sender"]][0]
    r = a.post(f"/api/emails/{pending['id']}/actions/process")
    assert r.status_code == 200 and r.json()["status"] == "Awaiting Purchasing"
    assert any("auroranet" in e["sender"] for e in b.get("/api/emails?view=queue").json())


def test_workflow_error_is_409_and_unknown_action_404():
    c = client()
    e = c.get("/api/emails?view=queue").json()[0]
    assert c.post(f"/api/emails/{e['id']}/actions/finalize").status_code == 409
    assert c.post(f"/api/emails/{e['id']}/actions/drop_table").status_code == 404


def test_manual_upload_flow_over_http():
    c = client()
    nf = c.get("/api/samples/sample_nfse_valelink.pdf").content
    boleto = c.get("/api/samples/sample_boleto_valelink.pdf").content
    p = c.post("/api/manual/preview", files=[("files", ("nf.pdf", nf, "application/pdf")),
                                             ("files", ("b.pdf", boleto, "application/pdf"))]).json()
    assert p["records"][0]["fornecedor"] == "ValeLink Internet"
    r = c.post("/api/manual/confirm", json={"token": p["token"], "destination": "purchasing", "records": p["records"]})
    assert r.json()["status"] == "Awaiting Purchasing"


def test_exports_and_metrics():
    c = client()
    x = c.get("/api/invoices/export.xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    assert "invoice_demo_http_requests_total" in c.get("/metrics").text


def test_reset():
    c = client()
    c.post("/api/queue/process")
    assert c.post("/api/reset").json()["success"]
    assert len(c.get("/api/emails?view=queue").json()) == 4


def test_language_toggle_translates_messages_and_history():
    c = client()
    e = c.get("/api/emails?view=queue").json()[0]
    r = c.post(f"/api/emails/{e['id']}/actions/finalize", headers={"X-Lang": "pt-BR"})
    assert r.status_code == 409 and "não é permitido" in r.json()["message"]
    logs_pt = c.get("/api/logs", headers={"X-Lang": "pt"}).json()
    logs_en = c.get("/api/logs", headers={"X-Lang": "en"}).json()
    assert logs_pt[0]["message"] != logs_en[0]["message"]  # same entry, both languages


def test_browser_runtime_uses_the_same_routes():
    import json
    from app import browser
    status, kind, payload, *_ = browser.handle("GET", "/api/summary", "{}", None, None, None, "pt")
    assert status == 200 and kind == "json" and json.loads(payload)["queue"] == 4
    status, kind, data, media, name, inline = browser.handle("GET", "/api/invoices/export.xlsx", "{}", None, None,
                                                             None, "en")
    assert kind == "file" and data[:2] == b"PK" and not inline
    status, kind, payload, *_ = browser.handle("POST", "/api/reset", "{}", None, None, None, "en")
    assert json.loads(payload)["success"]
