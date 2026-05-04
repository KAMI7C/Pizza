from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from .constants import PIZZA_BASE_PRICES


class Category(models.Model):
    name = models.CharField("Название", max_length=64)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Ингредиент для фильтрации меню и конструктора."""

    name = models.CharField("Название", max_length=128)
    slug = models.SlugField(unique=True)
    price_extra = models.DecimalField(
        "Доплата в конструкторе (BYN)", max_digits=8, decimal_places=2, default=Decimal("1.50")
    )
    image = models.ImageField("Картинка для куска", upload_to="ingredients/", blank=True)

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    class Spiciness(models.IntegerChoices):
        NONE = 0, "Без остроты"
        MILD = 1, "Слабо"
        MEDIUM = 2, "Средне"
        HOT = 3, "Остро"

    name = models.CharField("Название", max_length=128)
    slug = models.SlugField(unique=True)
    description = models.TextField("Описание / состав", blank=True)
    composition = models.TextField("Состав (текст для карточки)", blank=True)
    price = models.DecimalField("Цена (BYN)", max_digits=8, decimal_places=2)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products", verbose_name="Категория"
    )
    spiciness = models.PositiveSmallIntegerField(
        "Острота", choices=Spiciness.choices, default=Spiciness.NONE
    )
    image = models.ImageField("Изображение", upload_to="products/", blank=True)
    ingredients = models.ManyToManyField(
        Ingredient, blank=True, related_name="menu_products", verbose_name="Ингредиенты для фильтра"
    )
    popularity = models.PositiveIntegerField("Популярность (для сортировки)", default=0)
    in_stock = models.BooleanField("В наличии", default=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Promotion(models.Model):
    title = models.CharField("Заголовок", max_length=128)
    text = models.TextField("Текст акции")
    discount_percent = models.PositiveSmallIntegerField(
        "Скидка, %", null=True, blank=True, validators=[MaxValueValidator(100)]
    )
    image = models.ImageField("Баннер", upload_to="promotions/", blank=True)
    is_active = models.BooleanField("Активна", default=True)
    starts_at = models.DateTimeField("С", default=timezone.now)
    ends_at = models.DateTimeField("По", null=True, blank=True)

    class Meta:
        verbose_name = "Акция"
        verbose_name_plural = "Акции и скидки"
        ordering = ["-starts_at"]

    def __str__(self):
        return self.title

    def is_current(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    phone = models.CharField("Телефон", max_length=20, blank=True)
    is_blocked = models.BooleanField("Заблокирован", default=False)

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"Профиль {self.user.username}"


class SavedAddress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_addresses"
    )
    label = models.CharField("Название", max_length=64, default="Дом")
    address = models.CharField("Адрес", max_length=255)

    class Meta:
        verbose_name = "Сохранённый адрес"
        verbose_name_plural = "Сохранённые адреса"

    def __str__(self):
        return f"{self.label}: {self.address}"


class CustomPizza(models.Model):
    """Снимок пиццы из конструктора (привязка к позиции корзины/заказа)."""

    class Crust(models.TextChoices):
        THIN = "thin", "Тонкое"
        THICK = "thick", "Толстое"

    class Size(models.TextChoices):
        SMALL = "small", "Маленькая"
        MEDIUM = "medium", "Средняя"
        LARGE = "large", "Большая"

    crust = models.CharField("Тесто", max_length=16, choices=Crust.choices, default=Crust.THIN)
    size = models.CharField("Размер", max_length=16, choices=Size.choices, default=Size.MEDIUM)
    price_cached = models.DecimalField("Итоговая цена на момент добавления", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Собранная пицца"
        verbose_name_plural = "Собранные пиццы"

    def compute_price(self) -> Decimal:
        base = PIZZA_BASE_PRICES.get((self.crust, self.size), Decimal("0"))
        toppings = self.toppings.select_related("ingredient").all()
        extra = sum((t.ingredient.price_extra for t in toppings), Decimal("0"))
        return base + extra

    def __str__(self):
        return f"{self.get_crust_display()} / {self.get_size_display()} — {self.price_cached} BYN"


class CustomPizzaTopping(models.Model):
    pizza = models.ForeignKey(CustomPizza, on_delete=models.CASCADE, related_name="toppings")
    quarter = models.PositiveSmallIntegerField(
        "Четверть (1–4)", validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Топпинг на четверти"
        verbose_name_plural = "Топпинги"
        constraints = [
            models.UniqueConstraint(fields=["pizza", "quarter", "ingredient"], name="uniq_quarter_ingredient")
        ]

    def __str__(self):
        return f"Q{self.quarter}: {self.ingredient.name}"


class Cart(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def total(self) -> Decimal:
        agg = self.items.aggregate(s=Sum("line_total"))
        return agg["s"] or Decimal("0")

    def items_count(self) -> int:
        return self.items.aggregate(s=Sum("quantity"))["s"] or 0


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items"
    )
    custom_pizza = models.OneToOneField(
        CustomPizza,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cart_item",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция корзины"
        verbose_name_plural = "Позиции корзины"


class Order(models.Model):
    class Status(models.TextChoices):
        ACCEPTED = "accepted", "Принят"
        COOKING = "cooking", "Готовится"
        DELIVERING = "delivering", "В доставке"
        DELIVERED = "delivered", "Доставлен"
        CANCELLED = "cancelled", "Отменён"

    class DeliveryType(models.TextChoices):
        COURIER = "courier", "Курьер"
        PICKUP = "pickup", "Самовывоз"

    class PaymentType(models.TextChoices):
        ONLINE = "online", "Онлайн"
        CASH = "cash", "Наличными"
        CARD = "card", "Картой при получении"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    status = models.CharField(
        "Статус заказа", max_length=20, choices=Status.choices, default=Status.ACCEPTED
    )
    delivery_type = models.CharField("Доставка", max_length=16, choices=DeliveryType.choices)
    payment_type = models.CharField("Оплата", max_length=16, choices=PaymentType.choices)
    customer_name = models.CharField("Имя", max_length=120)
    phone = models.CharField("Телефон", max_length=20)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Адрес", max_length=255, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    total = models.DecimalField("Сумма (BYN)", max_digits=10, decimal_places=2)
    estimated_delivery_at = models.DateTimeField("Ориентировочное время доставки", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заказ #{self.pk} — {self.get_status_display()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    custom_pizza = models.OneToOneField(
        CustomPizza, on_delete=models.SET_NULL, null=True, blank=True, related_name="order_item"
    )
    title = models.CharField("Название позиции", max_length=200)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"
