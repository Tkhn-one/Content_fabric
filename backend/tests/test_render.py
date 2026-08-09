"""Тесты рендера и субтитров (работают без сети)."""
import os
import tempfile

os.environ.setdefault("CF_SECRET_KEY", "test-secret")
os.environ.setdefault("CF_ADMIN_USERNAME", "admin")
os.environ.setdefault("CF_ADMIN_PASSWORD", "admin123")
os.environ.setdefault("CF_DB_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")
os.environ.setdefault("CF_MEDIA_DIR", tempfile.mkdtemp(prefix="cf_media_"))

import pytest  # noqa: E402

from app.services.subtitles import build_ass  # noqa: E402
from app.services.wordtimings import estimate_word_timings, group_words_by_phrases, split_phrases  # noqa: E402


def test_split_phrases():
    text = "Первое предложение. Второе, но с запятой. Третье!"
    phrases = split_phrases(text)
    assert len(phrases) == 3
    assert phrases[0].startswith("Первое")


def test_estimate_word_timings_total():
    words = estimate_word_timings("один два три четыре", 4.0)
    assert len(words) == 4
    assert abs(words[-1].end - 4.0) < 0.01


def test_group_words_by_phrases():
    text = "Короткая фраза. Длинная фраза, которая не помещается и режется."
    words = estimate_word_timings(text, 8.0)
    grouped = group_words_by_phrases(text, words)
    assert len(grouped) >= 2
    joined_words = [w.text for _, ws in grouped for w in ws]
    assert len(joined_words) == len(words)


def test_build_ass_karaoke_and_watermark():
    words = estimate_word_timings("Привет мир", 2.0)
    ass = build_ass([("Привет мир", words)], 2.0, watermark="Content Factory")
    assert "\\k" in ass          # karaoke-тайминги
    assert "Content Factory" in ass  # водяной знак
    assert "Dialogue: 0," in ass
    assert "[Events]" in ass


@pytest.mark.skipif(not os.environ.get("RUN_RENDER_TESTS"), reason="медленный тест рендера, RUN_RENDER_TESTS=1")
def test_render_produces_video():
    import asyncio

    from app.core.db import SessionLocal, init_db
    from app.models import Job, Topic
    from app.pipeline.steps import render as render_step
    from app.services.ffmpeg import ffmpeg_available, probe_duration

    if not ffmpeg_available():
        pytest.skip("ffmpeg недоступен")

    init_db()
    db = SessionLocal()
    topic = Topic(user_id=1, name="Тест", niche="космос", platforms=["youtube"])
    db.add(topic)
    db.flush()
    job = Job(topic_id=topic.id)
    db.add(job)
    db.flush()
    script = "Ты знал, что на Венере сутки длиннее года? Подпишись на канал!"
    words = estimate_word_timings(script, 8.0)
    job.payload = {
        "script": script,
        "word_timings": [{"text": w.text, "start": w.start, "end": w.end} for w in words],
    }
    db.commit()

    asyncio.run(render_step.run(db, job, topic))
    db.refresh(job)
    video = job.payload.get("video_path")
    assert video, job.payload.get("video_note")
    assert probe_duration(video) >= 5
    db.close()
