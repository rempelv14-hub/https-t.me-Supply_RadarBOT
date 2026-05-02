from dataclasses import dataclass

from supplier_radar.runtime_config import settings


INTENT_WORDS = [
    "ищу",
    "ищем",
    "нужен",
    "нужна",
    "нужны",
    "подскажите",
    "посоветуйте",
    "где найти",
    "как найти",
    "кто знает",
    "помогите найти",
    "хочу открыть",
    "планирую открыть",
    "с чего начать",
    "где брать",
    "где закупать",
    "интересует",
    "интересуют",
]

TOPIC_WORDS = [
    "открыть магазин",
    "магазин косметики",
    "поставщики",
    "поставщик",
    "база поставщиков",
    "база брендов",
    "поставщики брендов",
    "оригинальная косметика",
    "корейская косметика",
    "европейская косметика",
    "поставщики европы",
    "закуп европа",
    "закуп с фабрик",
    "фабрики европы",
    "оптовые поставщики",
    "поставщики для wildberries",
    "поставщики для wb",
    "поставщики wb",
    "wb поставщики",
    "поставщики для ozon",
    "поставщики ozon",
    "ozon поставщики",
    "товарный бизнес",
    "где брать товар",
    "где закупать товар",
    "товар для маркетплейсов",
    "баеры европа",
    "баер европа",
]

GEO_WORDS = [
    "россия",
    "рф",
    "москва",
    "спб",
    "санкт-петербург",
    "екатеринбург",
    "новосибирск",
    "краснодар",
    "казань",
    "ростов",
    "самара",
    "нижний новгород",
    "снг",
    "доставка по россии",
    "по рф",
]

NEGATIVE_WORDS = [
    "продам базу",
    "продаю базу",
    "есть база",
    "скину базу",
    "купите базу",
    "база поставщиков в наличии",
    "пишите в лс",
    "пишите в личку",
    "пиши в лс",
    "курс",
    "обучение",
    "научу",
    "марафон",
    "вебинар",
    "заработок",
    "доход",
    "без вложений",
    "инвестиции",
    "крипта",
    "сигналы",
]

DISCOVERY_QUERIES = [
    "поставщики",
    "база поставщиков",
    "поставщики брендов",
    "оригинальная косметика",
    "косметика оптом",
    "товарный бизнес",
    "поставщики wildberries",
    "поставщики wb",
    "поставщики ozon",
    "закуп европа",
    "фабрики европы",
    "открыть магазин",
]

GROUP_POSITIVE_WORDS = [
    "поставщик",
    "поставщики",
    "поставки",
    "опт",
    "оптом",
    "косметика",
    "товарный",
    "бизнес",
    "wildberries",
    "wb",
    "ozon",
    "маркетплейс",
    "бренды",
    "европа",
    "закуп",
    "фабрики",
    "магазин",
]

GROUP_NEGATIVE_WORDS = [
    "крипта",
    "сигналы",
    "ставки",
    "казино",
    "букмекер",
    "мемы",
    "знакомства",
    "вакансии",
    "работа вахта",
    "инвестиции",
]


@dataclass
class LeadScore:
    score: int
    is_valid: bool
    reasons: list[str]


def score_message(text: str) -> LeadScore:
    original = text or ""
    text = original.lower()
    score = 0
    reasons: list[str] = []

    for word in INTENT_WORDS:
        if word in text:
            score += 3
            reasons.append(f"+3 намерение: {word}")

    for word in TOPIC_WORDS:
        if word in text:
            score += 2
            reasons.append(f"+2 тема: {word}")

    for word in GEO_WORDS:
        if word in text:
            score += 1
            reasons.append(f"+1 гео: {word}")

    for word in NEGATIVE_WORDS:
        if word in text:
            score -= 5
            reasons.append(f"-5 минус: {word}")

    return LeadScore(
        score=score,
        is_valid=score >= settings.min_score,
        reasons=reasons,
    )


def is_valid_group(title: str, username: str | None = None, about: str | None = None) -> bool:
    text = f"{title or ''} {username or ''} {about or ''}".lower()

    if any(bad in text for bad in GROUP_NEGATIVE_WORDS):
        return False

    if not settings.only_valid_groups:
        return True

    return any(good in text for good in GROUP_POSITIVE_WORDS)
