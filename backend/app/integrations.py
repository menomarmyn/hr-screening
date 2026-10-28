"""Интеграции с корпоративными системами: Битрикс24 (CRM) и 1С (OData).

По умолчанию INTEGRATIONS_DRY_RUN=true: запрос формируется и пишется в журнал, но не отправляется —
так безопасно показывать демо и тестировать маппинг полей до подключения боевой системы."""

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Candidate, IntegrationLog, Screening


def _candidate_payload(db: Session, cand: Candidate) -> dict:
    scr = db.query(Screening).filter(Screening.candidate_id == cand.id).first()
    summary = ""
    if scr:
        r = scr.result
        summary = (
            f"AI-скрининг: {scr.score}/100 ({scr.verdict}).\n{r.get('summary', '')}\n"
            f"Сильные стороны: {'; '.join(r.get('strengths', [])[:5])}\n"
            f"Риски: {'; '.join(r.get('risks', [])[:5])}"
        )
    return {
        "name": cand.name or cand.filename,
        "phones": cand.contacts.get("phones", []),
        "emails": cand.contacts.get("emails", []),
        "score": scr.score if scr else None,
        "summary": summary,
    }


def _send(db: Session, system: str, action: str, cand: Candidate, method: str, url: str, body: dict, auth=None) -> dict:
    s = get_settings()
    log = IntegrationLog(system=system, action=action, candidate_id=cand.id, request={"method": method, "url": url, "body": body}, status="dry_run")
    if s.integrations_dry_run or not url:
        log.response = {"note": "dry run: запрос не отправлялся"}
        external_id = f"dry-{system}-{cand.id}"
    else:
        try:
            resp = httpx.request(method, url, json=body, auth=auth, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            log.response, log.status = data, "ok"
            external_id = str(data.get("result") or data.get("Ref_Key") or "")
        except Exception as e:  # noqa: BLE001
            log.response, log.status = {"error": str(e)}, "error"
            db.add(log)
            db.commit()
            raise
    cand.crm_id = external_id
    db.add(log)
    db.commit()
    return {"system": system, "status": log.status, "external_id": external_id, "request": log.request}


def export_to_bitrix24(db: Session, cand: Candidate) -> dict:
    p = _candidate_payload(db, cand)
    fields = {
        "TITLE": f"Кандидат: {p['name']}",
        "NAME": p["name"],
        "SOURCE_ID": "WEB",
        "COMMENTS": p["summary"],
        "PHONE": [{"VALUE": x, "VALUE_TYPE": "WORK"} for x in p["phones"]],
        "EMAIL": [{"VALUE": x, "VALUE_TYPE": "WORK"} for x in p["emails"]],
    }
    base = get_settings().bitrix24_webhook_url.rstrip("/")
    url = f"{base}/crm.lead.add.json" if base else ""
    return _send(db, "bitrix24", "crm.lead.add", cand, "POST", url, {"fields": fields})


def export_to_1c(db: Session, cand: Candidate) -> dict:
    """Создание элемента справочника через стандартный OData-интерфейс 1С.
    Имя справочника и реквизиты зависят от конфигурации заказчика — здесь пример маппинга."""
    s = get_settings()
    p = _candidate_payload(db, cand)
    body = {"Description": p["name"], "Телефон": ", ".join(p["phones"]), "Email": ", ".join(p["emails"]), "ОценкаAI": p["score"], "Комментарий": p["summary"]}
    base = s.onec_base_url.rstrip("/")
    url = f"{base}/odata/standard.odata/Catalog_Кандидаты?$format=json" if base else ""
    auth = (s.onec_user, s.onec_password) if s.onec_user else None
    return _send(db, "1c", "create_candidate", cand, "POST", url, body, auth)


EXPORTERS = {"bitrix24": export_to_bitrix24, "1c": export_to_1c}
