"""Шаг 2: сценарий по шаблону. С реальным LLM — генерация, иначе — сборка из фактов."""
import random

from sqlalchemy.orm import Session

from app.models import Job, Topic
from app.pipeline.templates import get_templates, render_prompt
from app.providers.llm import get_llm

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

EN_FACTS_POOL = {
    "space": ["a day on Venus is longer than its year", "neutron stars spin 600 times per second",
              "astronauts' footprints on the Moon will last for millions of years", "the Milky Way moves at 2 million km/h",
              "there is a giant cloud of water vapor in space", "Saturn has over 140 moons"],
    "money": ["compound interest is the eighth wonder of the world", "most millionaires keep a budget",
              "inflation eats cash by about 10% a year", "small daily purchases cost the most",
              "the stock market grows 7-9% a year on average", "the rich diversify their assets"],
    "history": ["the first Olympic Games were held naked", "ancient Rome had its own fast food",
                "coffee was once called the devil's drink in Europe", "the Great Wall of China took 2000 years to build",
                "cleanliness was rare in the Middle Ages", "pyramids were already ancient to the Romans"],
}

# ключевые слова ниши → ключ пула (ru/en)
POOL_KEYS = {
    "космос": "космос", "space": "space", "психология": "психология", "деньги": "деньги",
    "money": "money", "история": "история", "history": "history",
}


def _pick_facts(topic: Topic, n: int) -> list[str]:
    lang = (topic.language or "ru").lower()
    pool = EN_FACTS_POOL if lang.startswith("en") else FACTS_POOL
    key = POOL_KEYS.get(topic.niche.strip().lower(), None)
    if not key or key not in pool:
        # ищем по первому слову ниши
        key = POOL_KEYS.get(topic.niche.lower().split()[0], None) if topic.niche else None
    facts = pool.get(key, list(pool.values())[0] if pool else [])
    if len(facts) > n:
        return random.sample(facts, n)
    return facts


async def run(db: Session, job: Job, topic: Topic) -> None:
    templates = get_templates(topic.language)
    tpl = templates.get(topic.template, templates["facts"])
    facts = _pick_facts(topic, tpl["n"])
    prompt = render_prompt(topic.template, topic.niche, topic.tone, topic.language, facts)

    llm = get_llm(db)
    script = ""
    from app.providers.llm.mock import MockLLM

    if not isinstance(llm, MockLLM):
        try:
            script = await llm.generate_script(prompt)
        except Exception:
            script = ""

    kwargs = {
        "niche": topic.niche,
        "fact": facts[0] if facts else "",
        "facts": " ".join(facts[1:]) if len(facts) > 1 else (facts[0] if facts else ""),
        "n": tpl.get("n", 3),
    }
    if not script:
        try:
            body = tpl["body"].format(**kwargs)
            hook = tpl["hook"].format(**kwargs)
            title = tpl["title"].format(**kwargs)
        except KeyError:
            body, hook, title = tpl["body"], tpl["hook"], tpl["title"]
        script = " ".join(filter(None, [hook, body, tpl["cta"]]))
    else:
        # заголовок для публикации
        try:
            title = tpl["title"].format(**kwargs)
        except KeyError:
            title = topic.name

    payload_data = dict(job.payload or {})
    payload_data["prompt"] = prompt
    payload_data["script"] = script
    payload_data["title"] = title

    # авто-хештеги
    if topic.auto_hashtags:
        try:
            hashtags = await llm.generate_hashtags(title, topic.niche)
        except Exception:
            hashtags = []
        if not hashtags:
            hashtags = ["#shorts", "#fyp", *[f"#{w.strip('# ').lower()}" for w in topic.niche.split() if len(w) > 3]]
        payload_data["hashtags"] = list(dict.fromkeys(hashtags))[:12]

    job.payload = payload_data
    db.commit()
