"""Эвристический разбор свободного текста — запасной режим без LLM.

С подключённой моделью (OpenAI / Gemini / Claude / Ollama) этот код не используется:
вакансию и резюме читает модель. Здесь — чтобы проект работал офлайн и в тестах,
и при этом принимал текст в любом виде, а не только по шаблону с заголовками."""

import re

from app.knowledge import find_skills, normalize
from app.schemas import ExperienceItem, Requirement, ResumeProfile, VacancyDraft

NICE = ("плюс", "преимуществ", "желательно", "будет здорово", "nice to have", "приветствуется", "хорошо, если", "бонусом",
        "если знает", "если есть", "если работал", "если умеет", "— отлично", "- отлично", "будет круто", "отлично, если")
CONDITION = (
    "предлагаем", "зарплат", "оклад", "дмс", "оплач", "график", "отпуск", "бонус", "обучени", "конкурентн",
    "комфортн", "офис в", "платим", "доход", "компенсаци", "возможность профессионального", "белая", "оформлени", "мы даём", "мы дадим", "у нас",
)
REQUIREMENT = (
    "опыт", "знани", "владени", "умени", "понимани", "навык", "требуется", "нужен", "нужна", "нужно", "должен",
    "уверенн", "способност", "ответственн", "коммуникаб", "образовани", "английск", "готовность",
)
DUTY_START = (
    "будешь", "будете", "будет писать", "будет делать", "будет вести", "будет работать", "будет разрабатывать", "будет заниматься", "предстоит", "твоя задача", "ваша задача", "разрабатыва", "создава", "создать", "участвова", "проектирова", "интегрирова", "проводить", "поддержива",
    "анализирова", "вести", "писать", "внедря", "сопровожда", "оценива", "настраива", "переводить", "изуча",
    "активно", "применя", "использова", "реализовыва", "работать с", "разрабатывать", "строить", "автоматизирова",
    "выстраива", "общаться", "встречаться", "готовить", "тестирова", "запуска", "оптимизирова", "улучша", "делать",
)
HEADINGS = {
    "duty": ("чем предстоит", "обязанности", "задачи", "что делать", "чем заниматься", "что нужно делать", "внедрение решений", "работа с ai", "разработка программных", "ai engineering"),
    "must": ("что мы ожидаем", "требования", "мы ожидаем", "кого мы ищем", "ожидаем от", "необходимо"),
    "nice": ("будет преимуществом", "плюсом", "желательно", "nice to have", "преимуществом"),
    "cond": ("мы предлагаем", "условия", "что мы даём", "что предлагаем", "у нас"),
}
ROLE_WORDS = ("engineer", "developer", "разработчик", "инженер", "менеджер", "аналитик", "дизайнер", "специалист", "manager", "lead", "архитектор", "тестировщик", "qa", "devops", "рекрутер")


def _units(text: str) -> list[str]:
    """Режем текст на смысловые единицы: строки, пункты списка, предложения, «желательно ...»."""
    out: list[str] = []
    for raw in text.splitlines():
        line = raw.strip().lstrip("-•*·—–>▪◦").strip()
        if not line:
            continue
        parts = [line] if line.endswith(":") else re.split(r"(?<=[.!?;])\s+(?=[A-ZА-ЯЁ0-9«])", line)
        for p in parts:
            # «нужен питонист с опытом Django, желательно знание 1С» → две единицы
            for q in re.split(r",?\s+(?=(?:желательно|будет плюсом|плюсом будет|а также)\b)", p, flags=re.I):
                q = q.strip(" ,;")
                if q:
                    out.append(q)
    return out


def _heading_kind(line: str) -> str | None:
    low = normalize(line).rstrip(":")
    # заголовок — строка с двоеточием в конце или короткая фраза без точки («Требования», «Мы предлагаем»)
    if not line.endswith(":") and (len(low.split()) > 4 or line.endswith(".")):
        return None
    for kind, keys in HEADINGS.items():
        if any(k in low for k in keys):
            return kind
    return "other" if line.endswith(":") else None


def _classify(unit: str) -> str:
    low = normalize(unit)
    if any(w in low for w in NICE):
        return "nice"
    if any(low.startswith(v) for v in DUTY_START):
        return "duty"
    if any(w in low for w in CONDITION):
        return "cond"
    if any(w in low for w in REQUIREMENT) or find_skills(unit):
        return "must"
    return "other"


def _clean_nice(text: str) -> str:
    t = re.sub(r"^(?:желательно|будет плюсом|плюсом будет|будет преимуществом)[:\s,]*", "", text, flags=re.I).strip()
    return (t[:1].upper() + t[1:]) if t else text


def heuristic_vacancy(text: str) -> VacancyDraft:
    units = _units(text)
    title = ""
    for u in units[:6]:
        low = normalize(u)
        if len(u) <= 70 and not u.endswith((".", ":")) and (any(w in low for w in ROLE_WORDS) or len(units) > 3 and u == units[0]):
            title = u
            break
    if not title:
        m = re.search(r"(?:ищем|нужен|нужна|требуется|вакансия)\s+([^,.;\n]{3,60})", text, re.I)
        title = _nominative(m.group(1)) if m else "Новая вакансия"
        title = title[:1].upper() + title[1:]

    duties: list[str] = []
    reqs: list[Requirement] = []
    conds: list[str] = []
    intro: list[str] = []
    mode: str | None = None
    has_headings = any(_heading_kind(u) for u in units)
    seen_heading = False
    for u in units:
        if u == title:
            continue
        h = _heading_kind(u)
        if has_headings and not seen_heading and not h:
            intro.append(u)  # вводный текст о компании до первого заголовка
            continue
        if re.match(r"(?:мы\s+|нам\s+|сейчас\s+мы\s+)?(?:ищем|нужен|нужна|требуется)\b", u, re.I) and any(w in normalize(u) for w in ROLE_WORDS):
            intro.append(u)  # «Нам нужен python-разработчик…» — это описание, а не требование
            continue
        if h:
            seen_heading = True
            mode = None if h == "other" else h
            continue
        inline = re.match(r"(задачи|обязанности|требования|условия|мы предлагаем)\s*:\s*(.+)", u, re.I)
        if inline:  # «Задачи: поиск клиентов, ведение сделок» в одну строку
            k = {"задачи": "duty", "обязанности": "duty", "требования": "must"}.get(inline.group(1).lower(), "cond")
            items = [x.strip(" .") for x in re.split(r",|;", inline.group(2)) if x.strip(" .")]
            for it in items:
                it = it[:1].upper() + it[1:]
                if k == "duty":
                    duties.append(it)
                elif k == "must":
                    reqs.append(Requirement(id="", text=it, kind="must", category=_category(it)))
                else:
                    conds.append(it)
            continue
        kind = _classify(u)
        if mode == "duty" and kind not in ("nice",):
            kind = "duty"
        elif mode in ("must", "nice"):
            kind = "nice" if (mode == "nice" or kind == "nice") else "must"
        elif mode == "cond":
            kind = "cond"
        if kind == "duty":
            duties.append(u)
        elif kind == "must":
            reqs.append(Requirement(id="", text=u[:1].upper() + u[1:], kind="must", category=_category(u)))
        elif kind == "nice":
            t = _clean_nice(u)
            reqs.append(Requirement(id="", text=t, kind="nice", category=_category(t)))
        elif kind == "cond":
            conds.append(u)
        elif mode is None and len(u) > 30:
            intro.append(u)
    for i, r in enumerate(reqs, 1):
        r.id = f"r{i}"

    low = normalize(text)
    location = next((city for stem, city in (("алмат", "Алматы"), ("астан", "Астана"), ("шымкент", "Шымкент"), ("караганд", "Караганда")) if stem in low), "")
    employment = ", ".join(
        w for w, keys in (("офис", ("в офис", "офисе", "офис в")), ("гибрид", ("гибрид",)), ("удалённо", ("удал",)), ("полная занятость", ("полная занятость", "полный день")))
        if any(k in low for k in keys)
    )
    sal = re.search(r"(?:от|до)?\s*\d[\d\s]{2,}\s*(?:₸|тенге|тг|руб|\$|usd|тысяч|тыс\.?|k\b)(?:[^\n.,;]{0,30})?", text, re.I)
    # о работе — предложения про «ищем/нужен», а не абзац о компании
    about_role = [u for u in intro if re.search(r"ищем|нужен|нужна|требуется|предстоит", u, re.I)]
    summary = " ".join((about_role or intro)[:2]) or (f"Ищем: {title}. " + (duties[0] if duties else ""))
    return VacancyDraft(
        title=title, summary=summary.strip(), responsibilities=duties[:12], requirements=reqs[:30], conditions=conds[:10],
        location=location, employment=employment, salary=sal.group(0).strip() if sal else "",
    )


_ACC = {"разработчика": "разработчик", "инженера": "инженер", "менеджера": "менеджер", "аналитика": "аналитик", "дизайнера": "дизайнер",
        "специалиста": "специалист", "тестировщика": "тестировщик", "архитектора": "архитектор", "рекрутера": "рекрутер", "руководителя": "руководитель"}


def _nominative(phrase: str) -> str:
    """«бэкенд-разработчика на Python в Алматы» → «бэкенд-разработчик на Python»."""
    phrase = re.split(r"\s+(?:в|во)\s+(?:[А-ЯЁ]|команд)|\s+(?:с опытом|можно|для)\b", phrase.strip())[0]
    words = phrase.split()
    for i, w in enumerate(words):
        low = w.lower()
        for acc, nom in _ACC.items():
            if low.endswith(acc):
                words[i] = w[: len(w) - len(acc)] + nom
    return " ".join(words)


def _category(text: str) -> str:
    skills = sorted(find_skills(text) - {"b2b", "production"}) or sorted(find_skills(text))
    return skills[0] if skills else "soft"


PERIOD_RE = re.compile(r"(\d{4})\s*[—–-]\s*(\d{4}|н\.?\s?в\.?|наст\w*|present|сейчас)", re.I)


def heuristic_profile(resume: str) -> ResumeProfile:
    lines = [ln.strip() for ln in resume.splitlines()]
    experience: list[ExperienceItem] = []
    education: list[str] = []
    skills_line: list[str] = []
    section = ""
    current: ExperienceItem | None = None
    for ln in lines:
        if not ln:
            continue
        low = normalize(ln)
        if low.startswith("образование"):
            section = "edu"
            rest = ln.split(":", 1)[1].strip() if ":" in ln else ""
            if rest:
                education.append(rest)
            continue
        if low.startswith(("навыки", "skills", "стек")):
            section = "skills"
            rest = ln.split(":", 1)[1] if ":" in ln else ""
            skills_line += [s.strip() for s in re.split(r"[,;]", rest) if s.strip()]
            continue
        if low.startswith(("опыт", "о себе", "учебные проекты", "пет-проекты")):
            section = "exp" if low.startswith("опыт") else ""
            continue
        m = PERIOD_RE.search(ln)
        if m:
            tail = PERIOD_RE.sub("", ln).strip(" ,.—–-")
            role, _, company = tail.partition(",")
            current = ExperienceItem(period=m.group(0), role=role.strip(), company=company.strip().strip("«»\"").split("»")[0].strip())
            experience.append(current)
            section = "exp"
            continue
        if section == "exp" and current and ln.startswith(("-", "•", "*")):
            current.highlights.append(ln.lstrip("-•* ").strip())
        elif section == "edu":
            education.append(ln)
        elif section == "skills" and "," in ln:
            skills_line += [s.strip() for s in ln.split(",") if s.strip()]
    skills = skills_line or sorted(find_skills(resume))
    head = next((ln for ln in lines[1:4] if ln and not any(c.isdigit() for c in ln) and "@" not in ln and "[" not in ln), "")
    years = re.search(r"(\d+(?:[.,]\d)?)\+?\s*(?:год|лет|years)", normalize(resume))
    headline = ", ".join(x for x in (head, f"{years.group(1)} лет опыта" if years else "") if x)
    return ResumeProfile(headline=headline, experience=experience[:8], skills=skills[:30], education=education[:4])
