import importlib
import os
from pathlib import Path


def _reload_db(tmp_path, monkeypatch):
    monkeypatch.setenv("WORLD_REPO_DIR", str(tmp_path))
    monkeypatch.setenv("WORLD_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("WORLD_EVIDENCE_DB", str(tmp_path / "data" / "world_evidence.db"))
    import worldshepherd_sara.world_evidence_db as db
    return importlib.reload(db)


def test_force_reindex_removes_stale_fts_terms_and_preserves_project_slug(tmp_path, monkeypatch):
    db = _reload_db(tmp_path, monkeypatch)
    db.init_db()
    doc = tmp_path / "alpha-beta-proof.txt"
    doc.write_text("Worldshepherd UNIQUEOLDTOKEN sara admin evidence", encoding="utf-8")
    with db._conn() as con:
        _, evidence_id = db._upsert_doc(con, doc)
        con.commit()
        assert con.execute(
            "SELECT count(*) FROM evidence_fts WHERE evidence_fts MATCH ?",
            ("UNIQUEOLDTOKEN",),
        ).fetchone()[0] == 1
        slug = con.execute(
            "SELECT project_slug FROM evidence WHERE id=?", (evidence_id,)
        ).fetchone()[0]

    doc.write_text("Worldshepherd UNIQUENEWTOKEN sara admin evidence", encoding="utf-8")
    with db._conn() as con:
        _, evidence_id_2 = db._upsert_doc(con, doc, force=True)
        con.commit()
        assert evidence_id_2 == evidence_id
        assert con.execute(
            "SELECT count(*) FROM evidence_fts WHERE evidence_fts MATCH ?",
            ("UNIQUEOLDTOKEN",),
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT count(*) FROM evidence_fts WHERE evidence_fts MATCH ?",
            ("UNIQUENEWTOKEN",),
        ).fetchone()[0] == 1
        assert con.execute(
            "SELECT count(*) FROM evidence WHERE project_slug=?", (slug,)
        ).fetchone()[0] == 1


def test_viewer_repo_root_and_query_token_links(tmp_path, monkeypatch):
    monkeypatch.setenv("WORLD_REPO_DIR", str(tmp_path))
    monkeypatch.setenv("WORLD_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("WORLD_EVIDENCE_DB", str(tmp_path / "data" / "world_evidence.db"))
    import worldshepherd_sara.world_actual_evidence as view
    view = importlib.reload(view)

    assert view._repo_root() == tmp_path.resolve()
    assert view._db_path() == tmp_path / "data" / "world_evidence.db"

    reset = view._link_token.set("secret token")
    try:
        href = view._auth_href("/world/evidence/evidence/1?full=1")
        assert "full=1" in href
        assert "token=secret+token" in href
    finally:
        view._link_token.reset(reset)
