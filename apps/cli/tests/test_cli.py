from __future__ import annotations

from mitorag_cli.main import main


def test_cli_ask_outputs_cited_answer(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["ask", "Complex I subunits?"]) == 0
    output = capsys.readouterr().out
    assert "[PMID:" in output
    assert "Complex I" in output


def test_cli_ask_deep_outputs_agent_trace(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["ask", "What causes MELAS?", "--deep"]) == 0
    output = capsys.readouterr().out
    assert "Agent trace:" in output
    assert "- router:" in output


def test_cli_ingest_empty_folder_reports_no_pdfs(tmp_path, capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["ingest", str(tmp_path)]) == 0
    output = capsys.readouterr().out
    assert "No PDFs found" in output


def test_cli_kg_stats_outputs_counts(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["kg", "stats"]) == 0
    output = capsys.readouterr().out
    assert "nodes=" in output
    assert "edges=" in output


def test_cli_kg_query_handles_matrix_count(capsys) -> None:  # type: ignore[no-untyped-def]
    cypher = "MATCH (g:Gene)-[:ENCODED_BY]-(p:Protein) RETURN count(p)"
    assert main(["kg", "query", cypher]) == 0
    output = capsys.readouterr().out
    assert output.strip().isdigit()


def test_cli_kg_query_accepts_unknown_cypher(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["kg", "query", "MATCH (n) RETURN n LIMIT 1"]) == 0
    output = capsys.readouterr().out
    assert "Query accepted" in output


def test_cli_kg_level_outputs_oxphos_summary(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["kg", "level", "2"]) == 0
    output = capsys.readouterr().out
    assert "OXPHOS" in output
    assert "Complex I-V" in output


def test_cli_search_outputs_local_and_web_hits(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["search", "PINK1 Parkin mitophagy"]) == 0
    output = capsys.readouterr().out
    assert "PMID" in output
    assert "mitophagy" in output.lower()


def test_cli_contradictions_lists_mptp(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["contradictions"]) == 0
    output = capsys.readouterr().out
    assert "mPTP" in output
