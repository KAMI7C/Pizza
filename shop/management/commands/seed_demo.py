from decimal import Decimal

from django.core.management.base import BaseCommand

from shop.models import Category, Ingredient, Product, Promotion


class Command(BaseCommand):
    help = "Начальные категории, ингредиенты и примеры товаров (Минск, BYN)."

    def handle(self, *args, **options):
        pizza_cat, _ = Category.objects.get_or_create(slug="pizza", defaults={"name": "Пицца"})
        drinks_cat, _ = Category.objects.get_or_create(slug="napitki", defaults={"name": "Напитки"})

        ings = [
            ("kolbasa", "Колбаса", "2.00"),
            ("griby", "Грибы", "1.80"),
            ("syrom", "Сыр моцарелла", "2.50"),
            ("perec", "Перец болгарский", "1.50"),
            ("bekon", "Бекон", "2.20"),
        ]
        ing_objs = []
        for slug, name, price in ings:
            o, _ = Ingredient.objects.get_or_create(
                slug=slug, defaults={"name": name, "price_extra": Decimal(price)}
            )
            ing_objs.append(o)

        def add_product(slug, name, price, desc, comp, spice, pop, cat):
            p, created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": desc,
                    "composition": comp,
                    "price": Decimal(price),
                    "category": cat,
                    "spiciness": spice,
                    "popularity": pop,
                },
            )
            if created:
                p.ingredients.set(ing_objs[:3])
            return p

        add_product(
            "margarita",
            "Маргарита",
            "18.90",
            "Классика на тонком тесте.",
            "Томатный соус, моцарелла, базилик.",
            Product.Spiciness.NONE,
            100,
            pizza_cat,
        )
        add_product(
            "pepperoni-hot",
            "Пепперони острая",
            "24.50",
            "Острая пицца с колбасой пепперони.",
            "Соус, сыр, пепперони, перец чили.",
            Product.Spiciness.HOT,
            90,
            pizza_cat,
        )
        add_product(
            "kola-05",
            "Кола 0,5 л",
            "3.50",
            "Холодный напиток.",
            "Газированный напиток 0,5 л.",
            Product.Spiciness.NONE,
            10,
            drinks_cat,
        )

        Promotion.objects.get_or_create(
            title="Скидка в будни",
            defaults={
                "text": "По будням с 12:00 до 16:00 — скидка 10% на пиццу из меню.",
                "discount_percent": 10,
                "is_active": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("Готово: категории, ингредиенты, товары и акция."))
