def test_auth_required(client):
    r = client.get("/api/vacancies", headers={"X-API-Key": "wrong"})
    assert r.status_code == 401


def test_vacancy_requirements_extracted(vacancy):
    kinds = {r["kind"] for r in vacancy["requirements"]}
    assert kinds == {"must", "nice"}
    assert len(vacancy["requirements"]) >= 15


def test_upload_and_ranking(client, vacancy, screened):
    assert len(screened) == 8
    ranking = client.get(f"/api/vacancies/{vacancy['id']}/candidates").json()
    assert all(c["status"] == "screened" for c in ranking)
    scores = [c["score"] for c in ranking]
    assert scores == sorted(scores, reverse=True)
    assert ranking[0]["name"] == "Арман Садыков"
    assert ranking[-1]["verdict"] == "reject"


def test_candidate_detail_has_no_pii(client, screened):
    cid = screened[0]["id"]
    d = client.get(f"/api/candidates/{cid}").json()
    assert "+7 701" not in d["masked_text"] and "@example.com" not in d["masked_text"]
    assert d["screening"]["matches"] and d["usage"]["provider"] == "mock"


def test_unsupported_file(client, vacancy):
    r = client.post(f"/api/vacancies/{vacancy['id']}/candidates", files=[("files", ("a.exe", b"x" * 100, "application/octet-stream"))])
    assert r.status_code == 422


def test_export_dry_run(client, screened):
    cid = screened[0]["id"]
    r = client.post(f"/api/candidates/{cid}/export", params={"system": "bitrix24"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "dry_run"
    assert body["request"]["body"]["fields"]["PHONE"][0]["VALUE"].startswith("+7")
    r = client.post(f"/api/candidates/{cid}/export", params={"system": "1c"})
    assert r.json()["system"] == "1c"
    logs = client.get("/api/integrations/logs").json()
    assert len(logs) >= 2


def test_agent_tools(client, vacancy, screened):
    def ask(text):
        r = client.post("/api/agent/chat", json={"vacancy_id": vacancy["id"], "messages": [{"role": "user", "content": text}]})
        assert r.status_code == 200, r.text
        return r.json()

    top = ask("Покажи топ 3 кандидатов")
    assert top["tool_calls"][0]["name"] == "rank_candidates"
    assert "Арман" in top["answer"]

    search = ask("У кого есть опыт с 1С и Битрикс24?")
    assert search["tool_calls"][0]["name"] == "search_candidates"

    ids = [c["id"] for c in screened[:2]]
    cmp_ = ask(f"Сравни кандидатов {ids[0]} и {ids[1]}")
    assert cmp_["tool_calls"][0]["name"] == "compare_candidates"


def test_analytics(client, vacancy, screened):
    a = client.get(f"/api/vacancies/{vacancy['id']}/analytics").json()
    assert a["screened"] == 8
    assert sum(a["verdicts"].values()) == 8
    assert a["top_skills"]


def test_mcp_tools_registered():
    import asyncio

    from app.mcp_server import mcp

    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"rank_candidates", "search_candidates", "export_candidate"} <= names


def test_ranking_fingerprint(client, vacancy, screened):
    ranking = client.get(f"/api/vacancies/{vacancy['id']}/candidates").json()
    fp = ranking[0]["fingerprint"]
    assert len(fp) == len(vacancy["requirements"])
    assert set(fp) <= {"met", "partial", "missing"}
