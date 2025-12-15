import csv
from pathlib import Path
from typing import List, Dict
import re
import pymorphy3

PRICE_LIST_PATH = Path("data/price_list.csv")


def load_price_list() -> List[Dict]:
    items = []
    last_category = ""
    with open(PRICE_LIST_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            category = row.get("Категория", "").strip()
            if category:
                last_category = category  # запоминаем последнюю категорию
            items.append({
                "category": last_category,
                "service": row.get("Услуга", "").strip(),
                "price": row.get("Цена", "").strip(),
                "comment": row.get("Комментарий", "").strip(),
            })
    return items


morph = pymorphy3.MorphAnalyzer()


def normalize(text: str) -> str:
    """Нормализация строки для сравнения."""
    return re.sub(r"\s+", " ", text.lower().strip())


def lemmatize(text: str) -> list[str]:
    words = re.findall(r"[а-яё]+", text.lower())
    return [
        morph.parse(word)[0].normal_form
        for word in words
        if len(word) > 2
    ]

def expand_lemmas(words: list[str]) -> set[str]:
    expanded = set()
    for word in words:
        parsed = morph.parse(word)[0]
        expanded.add(parsed.normal_form)
        if "ADJF" in parsed.tag:
            for form in parsed.lexeme:
                if "NOUN" in form.tag:
                    expanded.add(form.normal_form)
        if "NOUN" in parsed.tag:
            for form in parsed.lexeme:
                if "ADJF" in form.tag:
                    expanded.add(form.normal_form)
    return expanded

def search_services(price_list: list[dict], query: str) -> list[dict]:
    if not query:
        return []

    query_lemmas = expand_lemmas(lemmatize(query))

    results = []
    print(query_lemmas)
    for item in price_list:
        service_lemmas = expand_lemmas(lemmatize(item["service"]))
        category_lemmas = expand_lemmas(lemmatize(item["category"]))
        if len([1 for i in set(query_lemmas) if i in (service_lemmas | category_lemmas)]) / len(set(query_lemmas)) > 0.5:
            results.append(item)

    return results
