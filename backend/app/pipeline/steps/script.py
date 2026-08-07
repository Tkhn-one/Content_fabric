"""Шаг 2: сценарий по шаблону. На этапе 0 — сборка из фактов mock-генератором."""
from sqlalchemy.orm import Session

from app.models import Job, Topic
from app.pipeline.templates import TEMPLATES, render_prompt

FACTS_POOL = {
    "космос": ["на Венере сутки длиннее года", "нейтронные звёзды вращаются 600 раз в секунду",
               "на Луне следы астронавтов останутся на миллионы лет", "Млечный Путь движется со скоростью 2 млн км/ч",
               "в космосе есть гигантское облако водяного пара", "у Сатурна больше 140 спутников"],
    "психология": ["эффект фон Ресторфф: яркое запоминается лучше", "решения утром даются легче",
                   "мы запоминаем начало и конец разговора", "улыбка реально снижает стресс",
                   "люди переоценивают, как часто о них думают", "повторение через паузы работает лучше зубрёжки"],
    "деньги": ["сложный процент — восьмое чудо света", "большинство миллионеров ведут бюджет",
               "инфляция съедает наличные примерно на 10% в год", "дороже всего обходятся мелкие ежедневные траты",
               "фондовый рынок в среднем растёт на 7-9% в год", "богатые диверсифицируют активы"],
    "история": ["первые Олимпийские игры проводились обнажёнными", "в Древнем Риме был свой фастфуд",
                "кофе в Европе сначала считали напитком дьявола", "Великую Китайскую стену строили 2000 лет",
                "в Средневековье чистота была редкостью", "пирамиды были древнейшими уже для римлян"],
}


async def run(db: Session, job: Job, topic: Topic) -> None:
    tpl = TEMPLATES.get(topic.template, TEMPLATES["facts"])
    facts = FACTS_POOL.get(topic.niche.lower().split()[0] if topic.niche else "", FACTS_POOL["космос"])
    import random

    selected = random.sample(facts, min(tpl["n"], len(facts)))
    # Этап 0: собираем сценарий напрямую из шаблона; LLM-генерация — этап 1
    prompt = render_prompt(topic.template, topic.niche, topic.tone, topic.language, selected)
    kwargs = {
        "niche": topic.niche,
        "fact": selected[0],
        "facts": " ".join(selected[1:]) if len(selected) > 1 else selected[0],
        "n": tpl.get("n", 3),
    }
    try:
        body = tpl["body"].format(**kwargs)
        hook = tpl["hook"].format(**kwargs)
        title = tpl["title"].format(**kwargs)
    except KeyError:
        # шаблон содержит неизвестный плейсхолдер — подставляем как есть
        body, hook, title = tpl["body"], tpl["hook"], tpl["title"]
    script = " ".join(filter(None, [hook, body, tpl["cta"]]))
    payload_data = dict(job.payload or {})
    payload_data["prompt"] = prompt
    payload_data["script"] = script
    payload_data["title"] = title
    job.payload = payload_data
    db.commit()
