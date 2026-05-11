from pathlib import Path

from fastapi.testclient import TestClient

from mitorag_api.main import create_app


def _client() -> TestClient:
    return TestClient(create_app())


def test_health_endpoint() -> None:
    response = _client().get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_endpoint_returns_cited_answer_and_agent_trace() -> None:
    response = _client().post("/query", json={"question": "Complex I subunits?", "deep": True})

    assert response.status_code == 200
    payload = response.json()
    assert "Complex I" in payload["answer"]
    assert payload["citations"]
    assert payload["agent_trace"]
    assert payload["confidence"] > 0


def test_kg_stats_levels_and_contradictions() -> None:
    client = _client()

    stats = client.get("/kg/stats").json()
    assert stats["nodes"] >= 1500
    assert stats["edges"] >= 5000

    level = client.get("/kg/levels/2").json()
    assert level["name"] == "OXPHOS / ETC"
    assert "Complex I" in level["focus"]

    unknown = client.get("/kg/levels/99").json()
    assert unknown == {"level": 99, "name": "Unknown", "focus": []}

    contradictions = client.get("/kg/contradictions").json()
    assert any("mPTP" in item for item in contradictions["items"])


def test_ingest_papers_lists_configured_pdf_folder(tmp_path: Path, monkeypatch) -> None:
    paper = tmp_path / "melas.pdf"
    paper.write_bytes(b"%PDF-1.4")
    monkeypatch.setenv("PAPERS_DIR", str(tmp_path))

    response = _client().get("/ingest/papers")

    assert response.status_code == 200
    assert response.json() == [
        {"filename": "melas.pdf", "size_bytes": len(b"%PDF-1.4"), "status": "available"}
    ]


def test_upload_rejects_non_pdf() -> None:
    response = _client().post(
        "/ingest/upload",
        files={"file": ("notes.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .pdf uploads are supported"


def test_upload_pdf_saves_file_and_returns_ingestion_summary(tmp_path: Path, monkeypatch) -> None:
    class FakeResult:
        paper_id = "fake-paper"
        title = "Fake mitochondrial paper"
        chunk_count = 3

    class FakePipeline:
        def ingest_pdf(self, path: Path) -> FakeResult:
            assert path.name == "paper.pdf"
            assert path.read_bytes() == b"%PDF-1.4"
            return FakeResult()

    monkeypatch.setenv("PAPERS_DIR", str(tmp_path))
    monkeypatch.setattr("mitorag_api.routers.ingest.LocalIngestionPipeline", FakePipeline)

    response = _client().post(
        "/ingest/upload",
        files={"file": ("paper.pdf", b"%PDF-1.4", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json() == {
        "paper_id": "fake-paper",
        "title": "Fake mitochondrial paper",
        "chunk_count": 3,
        "saved_to": str(tmp_path / "paper.pdf"),
    }
