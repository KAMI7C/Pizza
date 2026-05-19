from copy import deepcopy
from decimal import Decimal

from django.db import transaction

from .constants import PIZZA_BASE_PRICES
from .models import (
    Cart,
    CartItem,
    CustomPizza,
    CustomPizzaTopping,
    Ingredient,
    Order,
    OrderItem,
    Product,
)

BUILDER_SESSION_KEY = "pizza_builder"

DEFAULT_BUILDER = {
    "crust": "thin",
    "size": "medium",
    "toppings": [],  # [{"q": 1, "iid": 3}, ...] уникальные пары (q, iid)
}

MAX_CART_ITEM_QUANTITY = 100


def _session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def get_cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, defaults={"session_key": ""})
        return cart
    key = _session_key(request)
    cart, _ = Cart.objects.get_or_create(user=None, session_key=key, defaults={})
    return cart


def _clone_custom_pizza(old: CustomPizza) -> CustomPizza:
    new_pizza = CustomPizza.objects.create(
        crust=old.crust, size=old.size, price_cached=old.price_cached
    )
    for top in old.toppings.select_related("ingredient").all():
        CustomPizzaTopping.objects.create(pizza=new_pizza, quarter=top.quarter, ingredient=top.ingredient)
    new_pizza.price_cached = new_pizza.compute_price()
    new_pizza.save(update_fields=["price_cached"])
    return new_pizza


def merge_session_cart_into_user(request, user, session_key=None):
    """После входа: объединить гостевую корзину с корзиной пользователя."""
    if session_key is None:
        session_key = request.session.session_key
    if not session_key:
        return
    guest = Cart.objects.filter(user=None, session_key=session_key).first()
    if not guest or not guest.items.exists():
        return
    user_cart, _ = Cart.objects.get_or_create(user=user, defaults={"session_key": ""})
    with transaction.atomic():
        for item in guest.items.select_related("product", "custom_pizza").all():
            if item.product_id:
                existing = user_cart.items.filter(product_id=item.product_id, custom_pizza__isnull=True).first()
                if existing:
                    existing.quantity += item.quantity
                    existing.unit_price = item.product.price
                    existing.line_total = existing.unit_price * existing.quantity
                    existing.save()
                    item.delete()
                else:
                    CartItem.objects.filter(pk=item.pk).update(cart=user_cart)
            elif item.custom_pizza_id:
                new_pizza = _clone_custom_pizza(item.custom_pizza)
                CartItem.objects.create(
                    cart=user_cart,
                    product=None,
                    custom_pizza=new_pizza,
                    quantity=item.quantity,
                    unit_price=new_pizza.price_cached,
                    line_total=new_pizza.price_cached * item.quantity,
                )
                item.delete()
        guest.delete()


def get_builder_state(request):
    data = deepcopy(DEFAULT_BUILDER)
    saved = request.session.get(BUILDER_SESSION_KEY)
    if isinstance(saved, dict):
        data["crust"] = saved.get("crust", data["crust"])
        data["size"] = saved.get("size", data["size"])
        tops = saved.get("toppings") or []
        if isinstance(tops, list):
            data["toppings"] = tops
    return data


def set_builder_state(request, state):
    request.session[BUILDER_SESSION_KEY] = state
    request.session.modified = True


def builder_topping_key(q: int, iid: int) -> tuple:
    return (int(q), int(iid))


def builder_price(state) -> Decimal:
    base = PIZZA_BASE_PRICES.get((state["crust"], state["size"]), Decimal("0"))
    ids = {t.get("iid") for t in state.get("toppings", []) if t.get("iid")}
    if not ids:
        return base
    extras = Ingredient.objects.filter(id__in=ids).values_list("price_extra", flat=True)
    return base + sum((Decimal(str(x)) for x in extras), Decimal("0"))


def add_builder_topping(request, quarter: int, ingredient_id: int):
    state = get_builder_state(request)
    key = builder_topping_key(quarter, ingredient_id)
    pairs = {(t.get("q"), t.get("iid")) for t in state["toppings"]}
    if key not in pairs:
        state["toppings"].append({"q": quarter, "iid": ingredient_id})
    set_builder_state(request, state)


def remove_builder_topping(request, quarter: int, ingredient_id: int):
    state = get_builder_state(request)
    state["toppings"] = [t for t in state["toppings"] if (t.get("q"), t.get("iid")) != (quarter, ingredient_id)]
    set_builder_state(request, state)


def clear_builder(request):
    request.session[BUILDER_SESSION_KEY] = deepcopy(DEFAULT_BUILDER)
    request.session.modified = True


@transaction.atomic
def cart_add_product(request, product: Product, quantity: int = 1):
    cart = get_cart(request)
    if not product.in_stock:
        return False, "Товар временно недоступен"
    line = cart.items.filter(product=product, custom_pizza__isnull=True).first()
    if line:
        if line.quantity + quantity > MAX_CART_ITEM_QUANTITY:
            return False, f"Максимальное количество для одной позиции — {MAX_CART_ITEM_QUANTITY}."
        line.quantity += quantity
        line.unit_price = product.price
        line.line_total = line.unit_price * line.quantity
        line.save()
    else:
        if quantity > MAX_CART_ITEM_QUANTITY:
            return False, f"Максимальное количество для одной позиции — {MAX_CART_ITEM_QUANTITY}."
        CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            unit_price=product.price,
            line_total=product.price * quantity,
        )
    return True, None


@transaction.atomic
def cart_add_custom_from_session(request):
    state = get_builder_state(request)
    if not state["toppings"]:
        return False, "Добавьте хотя бы один ингредиент"
    filled_quarters = {int(t.get("q")) for t in state["toppings"] if t.get("q") in (1, 2, 3, 4)}
    if filled_quarters != {1, 2, 3, 4}:
        return False, "Заполните ингредиентами все 4 куска пиццы"
    cart = get_cart(request)
    pizza = CustomPizza.objects.create(
        crust=state["crust"],
        size=state["size"],
        price_cached=Decimal("0"),
    )
    for t in state["toppings"]:
        q, iid = int(t["q"]), int(t["iid"])
        ing = Ingredient.objects.filter(pk=iid).first()
        if not ing:
            continue
        CustomPizzaTopping.objects.get_or_create(pizza=pizza, quarter=q, ingredient=ing)
    pizza.price_cached = pizza.compute_price()
    pizza.save(update_fields=["price_cached"])
    CartItem.objects.create(
        cart=cart,
        product=None,
        custom_pizza=pizza,
        quantity=1,
        unit_price=pizza.price_cached,
        line_total=pizza.price_cached,
    )
    clear_builder(request)
    return True, None


@transaction.atomic
def place_order_from_cart(
    *,
    cart: Cart,
    user,
    customer_name: str,
    phone: str,
    email: str,
    delivery_type: str,
    payment_type: str,
    address: str,
    comment: str,
):
    if not cart.items.exists():
        return None, "Корзина пуста"
    total = cart.total()
    order = Order.objects.create(
        user=user if user and user.is_authenticated else None,
        customer_name=customer_name,
        phone=phone,
        email=email or "",
        delivery_type=delivery_type,
        payment_type=payment_type,
        address=address or "",
        comment=comment,
        total=total,
    )
    for item in cart.items.select_related("product", "custom_pizza"):
        if item.product_id:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                custom_pizza=None,
                title=item.product.name,
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )
        else:
            old = item.custom_pizza
            new_pizza = CustomPizza.objects.create(
                crust=old.crust,
                size=old.size,
                price_cached=old.price_cached,
            )
            for top in old.toppings.select_related("ingredient").all():
                CustomPizzaTopping.objects.create(
                    pizza=new_pizza, quarter=top.quarter, ingredient=top.ingredient
                )
            OrderItem.objects.create(
                order=order,
                product=None,
                custom_pizza=new_pizza,
                title=f"Своя пицца ({new_pizza.get_size_display()}, {new_pizza.get_crust_display()})",
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=item.line_total,
            )
    cart.items.all().delete()
    cart.delete()
    return order, None


def repeat_order_to_cart(request, order: Order):
    """Скопировать позиции заказа в текущую корзину (новые объекты для кастомных)."""
    cart = get_cart(request)
    for oi in order.items.select_related("product", "custom_pizza"):
        if oi.product_id and oi.product.in_stock:
            cart_add_product(request, oi.product, quantity=oi.quantity)
        elif oi.custom_pizza_id:
            old = oi.custom_pizza
            new_pizza = CustomPizza.objects.create(
                crust=old.crust,
                size=old.size,
                price_cached=old.price_cached,
            )
            for top in old.toppings.select_related("ingredient").all():
                CustomPizzaTopping.objects.create(
                    pizza=new_pizza, quarter=top.quarter, ingredient=top.ingredient
                )
            new_pizza.price_cached = new_pizza.compute_price()
            new_pizza.save(update_fields=["price_cached"])
            CartItem.objects.create(
                cart=cart,
                product=None,
                custom_pizza=new_pizza,
                quantity=oi.quantity,
                unit_price=new_pizza.price_cached,
                line_total=new_pizza.price_cached * oi.quantity,
            )
