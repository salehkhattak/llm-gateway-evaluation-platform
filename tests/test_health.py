from fastapi import FastAPI

def test_health_shape():
    app = FastAPI()
    @app.get("/health")
    def health():
        return {"status": "ok"}
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
