from app.knowledge import find_skills
from app.llm.mock_provider import extract_requirements
from app.parsing import chunk_text, extract_contacts, mask_pii
from app.schemas import RequirementMatch, ScreeningResult
from app.screening import compute_score


def test_mask_pii_removes_contacts():
    text = "Иван Иванов +7 701 555 12 34, ivan@example.com, ИИН 900101300123, t.me/ivan"
    masked = mask_pii(text)
    assert "555" not in masked and "ivan@" not in masked and "900101300123" not in masked
    assert "[PHONE]" in masked and "[EMAIL]" in masked and "[IIN]" in masked and "[TELEGRAM]" in masked
    assert extract_contacts(text)["emails"] == ["ivan@example.com"]


def test_find_skills_word_boundaries():
    assert "typescript" in find_skills("Пишу на TypeScript")
    assert "1c" in find_skills("Интеграция с 1С через OData")
    assert "rag" not in find_skills("storage")  # подстрока не должна срабатывать


def test_chunking_respects_size():
    text = "\n\n".join(["абзац " * 50] * 5)
    chunks = chunk_text(text, max_chars=400)
    assert chunks and all(len(c) <= 400 for c in chunks)


def test_requirements_extraction_skips_intro_and_duties():
    desc = "О компании всё хорошо и прекрасно, очень длинный текст о компании.\nЧем предстоит заниматься:\n- Писать код на Python каждый день\nЧто мы ожидаем от Вас:\n- Опыт работы с FastAPI и PostgreSQL\nБудет преимуществом:\n- Опыт интеграции с 1С и CRM\n"
    reqs = extract_requirements(desc)
    assert [r.kind for r in reqs] == ["must", "nice"]
    assert "FastAPI" in reqs[0].text


def test_compute_score_and_verdict():
    reqs = [{"id": "r1", "kind": "must", "text": "a"}, {"id": "r2", "kind": "must", "text": "b"}, {"id": "r3", "kind": "nice", "text": "c"}]
    res = ScreeningResult(matches=[RequirementMatch(requirement_id="r1", status="met"), RequirementMatch(requirement_id="r2", status="met"), RequirementMatch(requirement_id="r3", status="missing")])
    score, verdict = compute_score(reqs, res)
    assert score == 80.0 and verdict == "strong"
    res2 = ScreeningResult(matches=[RequirementMatch(requirement_id="r3", status="met")])
    assert compute_score(reqs, res2)[1] == "reject"  # большинство must отсутствует
