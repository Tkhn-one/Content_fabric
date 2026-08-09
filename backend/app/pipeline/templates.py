"""Шаблоны сценариев: структура хука, тела и CTA. Заполняются LLM или mock."""

TEMPLATES: dict[str, dict] = {
    "facts": {
        "title": "Пункт про {niche}",
        "hook": "Ты знал, что {fact}?",
        "body": "Вот ещё {n} фактов о {niche}, о которых почти никто не говорит. {facts}",
        "cta": "Подпишись, чтобы узнавать такое каждый день!",
        "n": 4,
    },
    "top5": {
        "title": "Топ-5 {niche}",
        "hook": "Сегодня разбираем топ-5 самых интересных вещей про {niche}.",
        "body": "Пятое место — {fact}. Четвёртое — {fact}. Третье — {fact}. Второе — {fact}. И первое место — {fact}!",
        "cta": "Что бы ты добавил в этот топ? Пиши в комментариях!",
        "n": 5,
    },
    "story": {
        "title": "История про {niche}",
        "hook": "Это история, которую ты не забудешь.",
        "body": "Всё началось с {fact}. Потом случилось {fact}. А закончилось всё вот чем: {fact}.",
        "cta": "Дослушал до конца? Поставь лайк и подпишись!",
        "n": 3,
    },
    "qa": {
        "title": "Вопрос про {niche}",
        "hook": "Отвечаю на самый частый вопрос про {niche}.",
        "body": "Короткий ответ — {fact}. А если подробнее: {fact} и ещё {fact}.",
        "cta": "Остался вопрос? Напиши его в комментариях!",
        "n": 3,
    },
    "myth": {
        "title": "Миф о {niche}",
        "hook": "Этот миф о {niche} слышали все. Но правда другая.",
        "body": "Миф: {fact}. На самом деле: {fact}. Учёные говорят: {fact}.",
        "cta": "А во что верил ты? Расскажи в комментариях!",
        "n": 3,
    },
    "chat": {
        "title": "Переписка про {niche}",
        "hook": "Диалог, который взорвал сеть.",
        "body": "Переписка двух людей о {niche}, где каждый обменивается фактами.",
        "cta": "Подпишись, чтобы видеть такие диалоги!",
        "n": 3,
    },
}

TEMPLATES_EN: dict[str, dict] = {
    "facts": {
        "title": "Fact about {niche}",
        "hook": "Did you know that {fact}?",
        "body": "Here are {n} more facts about {niche} almost nobody talks about. {facts}",
        "cta": "Subscribe to learn something new every day!",
        "n": 4,
    },
    "top5": {
        "title": "Top 5 {niche}",
        "hook": "Today we break down the top 5 most interesting things about {niche}.",
        "body": "Number five — {fact}. Number four — {fact}. Number three — {fact}. Number two — {fact}. And the number one — {fact}!",
        "cta": "What would you add to this list? Comment below!",
        "n": 5,
    },
    "story": {
        "title": "The story of {niche}",
        "hook": "This is a story you will never forget.",
        "body": "It all started with {fact}. Then {fact} happened. And it all ended like this: {fact}.",
        "cta": "Still here? Like and subscribe!",
        "n": 3,
    },
    "qa": {
        "title": "Question about {niche}",
        "hook": "Answering the most asked question about {niche}.",
        "body": "Short answer — {fact}. If we go deeper: {fact} and also {fact}.",
        "cta": "Got a question? Write it in the comments!",
        "n": 3,
    },
    "myth": {
        "title": "The myth about {niche}",
        "hook": "Everyone believes this myth about {niche}. But the truth is different.",
        "body": "The myth: {fact}. In reality: {fact}. Scientists say: {fact}.",
        "cta": "What did you believe? Tell us in the comments!",
        "n": 3,
    },
    "chat": {
        "title": "Chat about {niche}",
        "hook": "A conversation that blew up the internet.",
        "body": "Two people chatting about {niche}, swapping facts.",
        "cta": "Subscribe to see more conversations like this!",
        "n": 3,
    },
}

TONES = {"casual": "разговорный, лёгкий", "dramatic": "эмоциональный, с интригой", "expert": "экспертный, уверенный"}
TONES_EN = {"casual": "conversational, light", "dramatic": "emotional, intriguing", "expert": "expert, confident"}


def get_templates(language: str) -> dict:
    """Возвращает шаблоны на языке темы (ru/en)."""
    return TEMPLATES_EN if (language or "ru").lower().startswith("en") else TEMPLATES


def render_prompt(template_key: str, niche: str, tone: str, language: str, facts: list[str]) -> str:
    """Собирает промпт для LLM на основе шаблона (на языке темы)."""
    is_en = (language or "ru").lower().startswith("en")
    tpl = get_templates(language).get(template_key, TEMPLATES_EN["facts"] if is_en else TEMPLATES["facts"])
    if is_en:
        tone_text = TONES_EN.get(tone, TONES_EN["casual"])
        return (
            f"Write a vertical video script up to 45 seconds about «{niche}» in {language}. "
            f"Tone: {tone_text}. "
            f"Structure: 1) hook up to 5 seconds ({tpl['hook']}) 2) main part "
            f"({tpl['body']}, use these facts: {', '.join(facts)}) "
            f"3) call to action ({tpl['cta']}). "
            "Output only the script text, no headings, short sentences."
        )
    tone_text = TONES.get(tone, TONES["casual"])
    return (
        f"Напиши сценарий вертикального видео до 45 секунд на тему «{niche}» "
        f"на языке: {language}. Тон: {tone_text}. "
        f"Структура: 1) хук до 5 секунд ({tpl['hook']}) 2) основная часть "
        f"({tpl['body']}, подставь факты из: {', '.join(facts)}) "
        f"3) призыв к действию ({tpl['cta']}). "
        "Выдай только текст сценария, без заголовков, короткими предложениями."
    )
