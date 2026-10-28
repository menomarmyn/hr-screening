"""Фоновые задачи Celery: скрининг идёт асинхронно, API отвечает сразу."""

from celery import Celery

from app.config import get_settings

s = get_settings()
celery_app = Celery("hr", broker=s.redis_url, backend=s.redis_url)
celery_app.conf.update(
    task_always_eager=s.celery_eager,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10, retry_backoff=True, name="screen_candidate")
def screen_candidate_task(self, candidate_id: int, provider: str | None = None, model: str | None = None):
    from app.db import SessionLocal
    from app.llm import get_provider
    from app.screening import screen_candidate

    db = SessionLocal()
    try:
        scr = screen_candidate(db, candidate_id, get_provider(provider, model))
        return {"candidate_id": candidate_id, "score": scr.score, "verdict": scr.verdict}
    except Exception as e:
        # Ретраи на сетевые сбои/лимиты провайдера; ошибки валидации тоже повторяем — LLM недетерминирована
        raise self.retry(exc=e) from e
    finally:
        db.close()


def enqueue_screening(candidate_id: int, provider: str | None = None, model: str | None = None) -> None:
    if s.celery_eager:
        # Синхронный режим (dev без Redis): выполняем напрямую, ошибка уже записана в кандидата
        from app.db import SessionLocal
        from app.llm import get_provider
        from app.screening import screen_candidate

        db = SessionLocal()
        try:
            screen_candidate(db, candidate_id, get_provider(provider, model))
        except Exception:  # noqa: BLE001
            pass
        finally:
            db.close()
        return
    screen_candidate_task.delay(candidate_id, provider, model)
