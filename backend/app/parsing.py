"""Извлечение текста из резюме и маскирование персональных данных."""

import io
import re

PHONE_RE = re.compile(r"(?:\+7|8)[\s\-()]*\d{3}[\s\-()]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
IIN_RE = re.compile(r"\b\d{12}\b")  # ИИН РК — 12 цифр
URL_RE = re.compile(r"https?://\S+|(?:t\.me|telegram\.me|linkedin\.com|github\.com)/\S+", re.I)


class UnsupportedFile(ValueError):
    pass


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif name.endswith(".docx"):
        from docx import Document

        doc = Document(io.BytesIO(data))
        text = "\n".join(p.text for p in doc.paragraphs)
    elif name.endswith((".txt", ".md")):
        text = data.decode("utf-8", errors="replace")
    else:
        raise UnsupportedFile(f"Неподдерживаемый формат: {filename}. Нужен PDF, DOCX или TXT.")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 50:
        raise UnsupportedFile("В файле почти нет текста (возможно, это скан — нужен OCR).")
    return text


def extract_contacts(text: str) -> dict:
    return {
        "phones": sorted(set(PHONE_RE.findall(text))),
        "emails": sorted(set(EMAIL_RE.findall(text))),
        "links": sorted(set(URL_RE.findall(text))),
    }


def mask_pii(text: str) -> str:
    """Убираем контакты и ИИН до отправки во внешнюю LLM. Ссылку на GitHub оставляем как факт."""
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    text = IIN_RE.sub("[IIN]", text)
    text = re.sub(r"(t\.me|telegram\.me)/\S+", "[TELEGRAM]", text, flags=re.I)
    return text


def guess_name(text: str) -> str:
    for line in text.splitlines()[:5]:
        line = line.strip().strip("#").strip()
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[:1].isupper() for w in words) and not any(c.isdigit() for c in line):
            return line
    return ""


def chunk_text(text: str, max_chars: int = 600, overlap: int = 100) -> list[str]:
    """Режем по абзацам, длинные абзацы — окнами с перекрытием."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n(?=[-•*] )", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        if len(buf) + len(p) + 1 <= max_chars:
            buf = f"{buf}\n{p}".strip()
            continue
        if buf:
            chunks.append(buf)
        if len(p) <= max_chars:
            buf = p
        else:
            start = 0
            while start < len(p):
                chunks.append(p[start : start + max_chars])
                start += max_chars - overlap
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks
