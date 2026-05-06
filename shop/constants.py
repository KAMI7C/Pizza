"""Базовые цены конструктора (BYN) — тесто + размер, без топпингов."""
from decimal import Decimal


PIZZA_BASE_PRICES = {
    ("thin", "small"): Decimal("12.00"),
    ("thin", "medium"): Decimal("16.00"),
    ("thin", "large"): Decimal("20.00"),
    ("thick", "small"): Decimal("13.50"),
    ("thick", "medium"): Decimal("18.00"),
    ("thick", "large"): Decimal("22.50"),
}

SIZE_LABELS = {"small": "Маленькая", "medium": "Средняя", "large": "Большая"}
CRUST_LABELS = {"thin": "Тонкое", "thick": "Толстое"}
