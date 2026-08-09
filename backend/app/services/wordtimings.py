"""Тайминги слов: реальные (из edge-tts WordBoundary) или оценка по длительности."""
from __future__ import annotations

from .subtitles import Word

RU_CHARS_PER_SEC = 13.0   # скорость речи для оценки, когда нет реальных таймингов
OTHER_CHARS_PER_SEC = 15.0


def estimate_word_timings(text: str, duration: float) -> list[Word]:
    """Если реальных таймингов нет — раскладываем слова пропорционально длительности."""
    words = text.split()
    if not words or duration <= 0:
        return []
    total_chars = sum(len(w) for w in words)
    if total_chars == 0:
        return []
    rate = total_chars / duration
    cur = 0.0
    out: list[Word] = []
    for w in words:
        wd = (len(w) + 1) / rate
        out.append(Word(text=w, start=cur, end=min(duration, cur + wd)))
        cur += wd
    return out


def split_phrases(text: str, max_len: int = 70) -> list[str]:
    """Разбивает сценарий на фразы для субтитров и сегментов."""
    import re

    parts = re.split(r"(?<=[.!?…])\s+", text.strip())
    phrases: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_len:
            phrases.append(part)
        else:
            # режем длинную фразу по запятым/пробелам
            chunks = re.split(r"(?<=[,;:—–-])\s+", part)
            buf = ""
            for ch in chunks:
                if len(buf) + len(ch) + 1 > max_len and buf:
                    phrases.append(buf.strip())
                    buf = ch
                else:
                    buf = f"{buf} {ch}".strip()
            if buf:
                phrases.append(buf.strip())
    return phrases


def group_words_by_phrases(text: str, words: list[Word], max_len: int = 70) -> list[tuple[str, list[Word]]]:
    """Распределяет слова по фразам с таймингами (для кинетических субтитров)."""
    phrases = split_phrases(text, max_len)
    result: list[tuple[str, list[Word]]] = []
    wi = 0
    for phrase in phrases:
        pwords = []
        # набираем слова, пока не покроем текст фразы (по длине)
        used = 0
        while wi < len(words) and used < len(phrase.replace(" ", "")):
            w = words[wi]
            # слова могут содержать пунктуацию; считаем по длине с запасом
            pwords.append(w)
            used += len(w.text.strip(" ,.!?…—"))
            wi += 1
        if pwords:
            result.append((phrase, pwords))
    # хвост слов, не попавший в фразы
    if wi < len(words):
        leftover = words[wi:]
        if leftover:
            if result:
                _, last_words = result[-1]
                last_words.extend(leftover)
            else:
                result.append((" ".join(w.text for w in leftover), leftover))
    return result
