"""Шаг «Монтаж»: собирает вертикальное видео 1080x1920 из сегментов.

Пайплайн рендера:
  1. Фразы из сценария + тайминги слов (реальные из TTS или оценка)
  2. На каждый сегмент — фон: сток Pexels (если ключ) ИЛИ градиент (Pillow, без сети)
  3. Сегментные клипы (ffmpeg: scale/crop + zoompan) → concat
  4. Аудио: голос + музыка с ducking (sidechaincompress) или тишина
  5. Кинетические субтитры (ASS karaoke) + водяной знак в демо-режиме
"""
import asyncio
import logging
import random
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.license import parse_license
from app.models import Job, LicenseKey, Topic
from app.providers.registry import get_provider_settings
from app.services.ffmpeg import ffmpeg_available, ffmpeg_path, probe_duration
from app.services.subtitles import build_ass, Word
from app.services.wordtimings import estimate_word_timings, group_words_by_phrases, split_phrases

logger = logging.getLogger(__name__)

W, H = 1080, 1920
FPS = 30
SEGMENT_MAX_LEN = 70

PALETTE = [
    (16, 23, 42), (30, 27, 75), (59, 7, 100), (76, 29, 149),
    (30, 58, 138), (12, 74, 110), (134, 25, 143), (190, 24, 93),
]


def _is_demo(db: Session) -> tuple[bool, str]:
    row = db.query(LicenseKey).first()
    info = parse_license(row.key if row else "")
    return info.demo, getattr(settings, "watermark", "Content Factory")


def _make_gradient_bg(path: Path, c1: tuple[int, int, int], c2: tuple[int, int, int]) -> None:
    """Вертикальный градиент через Pillow (заглушка без сети)."""
    from PIL import Image

    img = Image.new("RGB", (W, H))
    for y in range(H):
        t = y / H
        color = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
        for x in range(0, W, 4):
            img.paste(color, (x, y, min(x + 4, W), y + 1))
    img.save(path, quality=90)


async def _download_bg(url: str, path: Path) -> bool:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            path.write_bytes(resp.content)
        return True
    except Exception as exc:
        logger.debug("Не скачался фон %s: %s", url, exc)
        return False


async def _prepare_backgrounds(db: Session, topic: Topic, job_dir: Path, n: int) -> tuple[list[Path], bool]:
    """Фоны для сегментов: Pexels если настроен, иначе градиенты. Возвращает (пути, использован ли сток)."""
    paths: list[Path] = []
    used_stock = False
    stock_name, stock_payload = get_provider_settings(db, "stock") or ("picsum", {})
    urls: list[str] = []
    if stock_name == "pexels" and stock_payload.get("api_key"):
        try:
            from app.providers.stock.pexels import PexelsStock

            stock = PexelsStock(stock_payload["api_key"])
            urls = await stock.search(topic.niche, n=n, orientation="vertical")
        except Exception as exc:
            logger.warning("Pexels недоступен: %s", exc)

    for i in range(n):
        path = job_dir / f"bg_{i}.jpg"
        ok = False
        if i < len(urls):
            ok = await _download_bg(urls[i], path)
            used_stock = used_stock or ok
        if not ok:
            c1, c2 = random.choice(PALETTE), random.choice(PALETTE)
            _make_gradient_bg(path, c1, c2)
        paths.append(path)
    return paths, used_stock


def _segment_clip(bg: Path, dur: float, out: Path) -> None:
    """Один сегмент: статичный фон + лёгкий zoom (zoompan)."""
    frames = max(1, int(dur * FPS))
    exe = ffmpeg_path()
    zoom = "min(zoom+0.0009,1.12)"
    cmd = [
        exe, "-y", "-i", str(bg),
        "-vf",
        (
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},"
            f"zoompan=z='{zoom}':d={frames}:s={W}x{H}:fps={FPS},"
            f"format=yuv420p"
        ),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-r", str(FPS),
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg segment: {res.stderr[-400:]}")


def _concat_segments(clips: list[Path], out: Path) -> None:
    list_file = out.parent / "concat.txt"
    list_file.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    exe = ffmpeg_path()
    res = subprocess.run(
        [exe, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out)],
        capture_output=True, text=True, timeout=300,
    )
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg concat: {res.stderr[-400:]}")


def _mix_audio(voice: Path | None, music: Path | None, duration: float, out: Path) -> None:
    exe = ffmpeg_path()
    cmd = [exe, "-y"]
    has_voice = voice is not None and voice.exists()
    has_music = music is not None and music.exists()

    if has_voice:
        cmd += ["-i", str(voice)]
    if has_music:
        cmd += ["-i", str(music)]

    if has_voice and has_music:
        # музыка приглушается голосом (ducking)
        fc = (
            "[1:a]aresample=44100,volume=0.9[mus];"
            "[0:a]aresample=44100[voi];"
            "[mus][voi]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=600[ducked];"
            "[voi][ducked]amix=inputs=2:duration=first:dropout_transition=2[a]"
        )
        cmd += ["-filter_complex", fc, "-map", "[a]"]
    elif has_voice:
        cmd += ["-map", "0:a", "-af", "aresample=44100"]
    elif has_music:
        cmd += ["-map", "0:a", "-af", "volume=0.6,aresample=44100"]
    else:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-map", "0:a"]

    cmd += ["-c:a", "aac", "-b:a", "192k", "-t", f"{duration:.2f}", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg audio: {res.stderr[-400:]}")


def _finalize(video: Path, audio: Path, ass_path: Path, out: Path) -> None:
    exe = ffmpeg_path()
    cmd = [
        exe, "-y", "-i", str(video), "-i", str(audio),
        "-vf", f"ass={ass_path}",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k", "-shortest",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg finalize: {res.stderr[-500:]}")


def _pick_music() -> Path | None:
    music_dir = settings.media_dir / "music"
    if not music_dir.exists():
        return None
    tracks = [p for p in music_dir.iterdir() if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")]
    if not tracks:
        return None
    return random.choice(tracks)


async def _render_avatar(job: Job, data: dict, avatar_path: Path, job_dir: Path, db: Session) -> None:
    """Режим аватара: видео аватара 9:16 + субтитры + музыка с ducking + водяной знак."""
    script = data.get("script", "")
    exe = ffmpeg_path()

    # 1) основа: обрезать аватар под 1080x1920, без звука
    base = job_dir / "avatar_base.mp4"
    res = subprocess.run(
        [
            exe, "-y", "-i", str(avatar_path),
            "-vf", (
                f"scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},format=yuv420p"
            ),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-an", str(base),
        ],
        capture_output=True, text=True, timeout=300,
    )
    if res.returncode != 0:
        raise RuntimeError(f"ffmpeg avatar base: {res.stderr[-400:]}")
    total = probe_duration(base) or 0

    # 2) голос аватара — из его аудиодорожки
    voice_av = job_dir / "avatar_voice.m4a"
    res = subprocess.run(
        [exe, "-y", "-i", str(avatar_path), "-vn", "-c:a", "aac", str(voice_av)],
        capture_output=True, text=True, timeout=120,
    )
    if res.returncode != 0 or not voice_av.exists():
        voice_av = None

    # 3) тайминги слов: нет реальных — оцениваем по длительности
    words: list[Word] = [Word(w["text"], w["start"], w["end"]) for w in data.get("word_timings", [])]
    if not words:
        words = estimate_word_timings(script, total)
    phrases = split_phrases(script, SEGMENT_MAX_LEN)
    grouped = group_words_by_phrases(script, words, SEGMENT_MAX_LEN)
    if not grouped:
        grouped = [(p, []) for p in phrases]

    # 4) музыка с ducking
    music = _pick_music()
    audio = job_dir / "audio.m4a"
    _mix_audio(voice_av, music, total, audio)

    # 5) субтитры + водяной знак
    demo, watermark = _is_demo(db)
    ass_path = job_dir / "subs.ass"
    ass_path.write_text(build_ass(grouped, total, watermark=watermark if demo else None), encoding="utf-8")

    out_video = job_dir / "video.mp4"
    _finalize(base, audio, ass_path, out_video)

    data["video_path"] = str(out_video)
    data["video_duration"] = round(probe_duration(out_video), 1)
    data["video_note"] = f"аватар: {data.get('avatar_note', 'heygen')}, музыка: {'да' if music else 'нет'}"
    job.payload = data
    db.commit()


async def run(db: Session, job: Job, topic: Topic) -> None:
    data = dict(job.payload or {})
    script = data.get("script", "")
    if not script:
        raise RuntimeError("Нет сценария")

    if not ffmpeg_available():
        data["video_path"] = None
        data["video_note"] = "ffmpeg не установлен (pip install imageio-ffmpeg или системный ffmpeg)"
        job.payload = data
        db.commit()
        return

    job_dir = settings.media_dir / "jobs" / str(job.id)
    job_dir.mkdir(parents=True, exist_ok=True)

    # --- тайминги слов ---
    words: list[Word] = [Word(w["text"], w["start"], w["end"]) for w in data.get("word_timings", [])]
    voice_path = Path(data["voice_path"]) if data.get("voice_path") else None
    avatar_path = Path(data["avatar_path"]) if data.get("avatar_path") else None

    if avatar_path and avatar_path.exists():
        return await _render_avatar(job, data, avatar_path, job_dir, db)

    if not words:
        dur = probe_duration(voice_path) if voice_path else max(8.0, len(script) / 13.0)
        words = estimate_word_timings(script, dur)
    if not words:
        raise RuntimeError("Не удалось получить тайминги слов")

    phrases = split_phrases(script, SEGMENT_MAX_LEN)
    grouped = group_words_by_phrases(script, words, SEGMENT_MAX_LEN)
    if not grouped:
        grouped = [(p, []) for p in phrases]

    # --- фоны ---
    bgs, used_stock = await _prepare_backgrounds(db, topic, job_dir, len(grouped))

    # --- сегментные клипы ---
    clips: list[Path] = []
    for i, ((phrase, pwords), bg) in enumerate(zip(grouped, bgs)):
        start = pwords[0].start if pwords else (clips and i)
        end = pwords[-1].end if pwords else (clips and i + 3)
        dur = max(1.2, min(12.0, end - start)) if pwords else 3.0
        out = job_dir / f"seg_{i:02d}.mp4"
        _segment_clip(bg, dur, out)
        clips.append(out)

    silent = job_dir / "silent.mp4"
    _concat_segments(clips, silent)
    total = probe_duration(silent) or sum(len(c) for c in clips)

    # --- аудио ---
    music = _pick_music()
    audio = job_dir / "audio.m4a"
    _mix_audio(voice_path, music, total, audio)

    # --- субтитры + водяной знак ---
    demo, watermark = _is_demo(db)
    ass_path = job_dir / "subs.ass"
    ass_path.write_text(build_ass(grouped, total, watermark=watermark if demo else None), encoding="utf-8")

    out_video = job_dir / "video.mp4"
    _finalize(silent, audio, ass_path, out_video)

    data["video_path"] = str(out_video)
    data["video_duration"] = round(probe_duration(out_video), 1)
    data["video_note"] = (
        f"сегментов: {len(clips)}, музыка: {'да' if music else 'нет'}, "
        f"фон: {'pexels' if used_stock else 'градиент'}"
    )
    job.payload = data
    db.commit()
