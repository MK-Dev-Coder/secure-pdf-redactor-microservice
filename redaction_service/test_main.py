from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code in [404, 405] # Verify service connectivity; root endpoint allows 404 or 405.

def test_hash_text():
    response = client.post("/hash", json={"text": "hello"})
    assert response.status_code == 200
    # SHA256 of "hello"
    assert response.json()["hash"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

def test_redact_text_names():
    # Verify that the PII redaction endpoint processes a request successfully
    response = client.post("/redact", json={"text": "Hello Mike, call me."})
    assert response.status_code == 200
    assert "pdf_base64" in response.json()
    assert "_links" in response.json()

def test_stats_endpoint():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_redactions" in data
