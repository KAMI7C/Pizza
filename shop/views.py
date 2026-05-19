from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST

from .constants import CRUST_LABELS, SIZE_LABELS
from .forms import CheckoutForm, ProfileForm, RegisterForm, SavedAddressForm
from .models import Category, Ingredient, Order, Product, Promotion, SavedAddress
from .utils import (
    add_builder_topping,
    builder_price,
    cart_add_custom_from_session,
    cart_add_product,
    clear_builder,
    get_builder_state,
    get_cart,
    merge_session_cart_into_user,
    place_order_from_cart,
    remove_builder_topping,
    repeat_order_to_cart,
    set_builder_state,
)


def home(request):
    promotions = [p for p in Promotion.objects.all() if p.is_current()]
    categories = Category.objects.all()
    category_slug = request.GET.get("category")
    search_q = (request.GET.get("q") or "").strip()
    products = Product.objects.filter(in_stock=True).select_related("category").prefetch_related("ingredients")

    if category_slug:
        products = products.filter(category__slug=category_slug)
    if search_q:
        products = products.filter(name__icontains=search_q)

    ing_id = request.GET.get("ingredient")
    ingredient_id = None
    if ing_id:
        try:
            ingredient_id = int(ing_id)
            products = products.filter(ingredients__id=ingredient_id)
        except ValueError:
            pass

    spice = request.GET.get("spiciness")
    if spice is not None and spice != "":
        try:
            products = products.filter(spiciness=int(spice))
        except ValueError:
            pass

    pmin_raw = request.GET.get("price_min")
    pmax_raw = request.GET.get("price_max")
    pmin = None
    pmax = None
    if pmin_raw not in (None, ""):
        try:
            pmin = Decimal(str(pmin_raw))
        except (InvalidOperation, ValueError):
            pmin = None
    if pmax_raw not in (None, ""):
        try:
            pmax = Decimal(str(pmax_raw))
        except (InvalidOperation, ValueError):
            pmax = None
    if pmin is not None and pmax is not None and pmin > pmax:
        pmin, pmax = pmax, pmin
    if pmin is not None:
        products = products.filter(price__gte=pmin)
    if pmax is not None:
        products = products.filter(price__lte=pmax)

    sort = request.GET.get("sort") or "popular"
    if sort == "price_up":
        products = products.order_by("price", "name")
    elif sort == "price_down":
        products = products.order_by("-price", "name")
    elif sort == "spice":
        products = products.order_by("-spiciness", "name")
    else:
        products = products.order_by("-popularity", "name")

    ingredients = Ingredient.objects.all()
    context = {
        "promotions": promotions,
        "categories": categories,
        "products": products.distinct(),
        "ingredients": ingredients,
        "current_category": category_slug,
        "current_sort": sort,
        "ingredient_id": ingredient_id,
        "current_spiciness": spice,
        "search_q": search_q,
        "delivery_blurb": (
            "Доставка по Минску — от 5 BYN. "
            "Заказ от 35 BYN — бесплатно в пределах МКАД. "
            "Телефон: +375 (29) 123-45-67. "
            "Самовывоз: пр-т Независимости, 95 (ст. м. «Площадь Якуба Коласа»)."
        ),
    }
    if _is_ajax(request):
        return render(request, "shop/_home_menu.html", context)
    return render(request, "shop/home.html", context)


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, in_stock=True)
    qty = int(request.POST.get("quantity") or 1)
    ok, err = cart_add_product(request, product, quantity=max(1, qty))
    if ok:
        messages.success(request, f"«{product.name}» добавлена в корзину.")
    else:
        messages.error(request, err or "Не удалось добавить товар.")
    ref = request.META.get("HTTP_REFERER")
    return redirect(ref or reverse("shop:home"))


def cart_view(request):
    cart = get_cart(request)
    cart_items = cart.items.select_related("product", "custom_pizza").prefetch_related(
        "custom_pizza__toppings__ingredient"
    )
    return render(request, "shop/cart.html", {"cart": cart, "cart_items": cart_items})


@require_POST
def cart_update(request, item_id):
    cart = get_cart(request)
    item = get_object_or_404(cart.items, pk=item_id)
    qty = int(request.POST.get("quantity") or 1)
    if qty < 1:
        item.delete()
        messages.info(request, "Позиция удалена.")
    elif qty > 100:
        messages.error(request, "Максимальное количество для одной позиции — 100.")
    else:
        item.quantity = qty
        item.line_total = item.unit_price * qty
        item.save()
        messages.success(request, "Количество обновлено.")
    return redirect("shop:cart")


@require_POST
def cart_remove(request, item_id):
    cart = get_cart(request)
    item = get_object_or_404(cart.items, pk=item_id)
    item.delete()
    messages.info(request, "Удалено из корзины.")
    return redirect("shop:cart")


def checkout(request):
    if not request.user.is_authenticated:
        messages.warning(request, "Чтобы оформить заказ, войдите в аккаунт или зарегистрируйтесь.")
        return redirect("shop:login")
    cart = get_cart(request)
    if not cart.items.exists():
        messages.warning(request, "Корзина пуста.")
        return redirect("shop:cart")
    initial = {}
    if request.user.is_authenticated:
        initial["customer_name"] = request.user.get_full_name() or request.user.username
        initial["email"] = request.user.email
        if hasattr(request.user, "profile"):
            initial["phone"] = request.user.profile.phone
    if request.method == "POST":
        form = CheckoutForm(request.POST, user=request.user)
        if form.is_valid():
            order, err = place_order_from_cart(
                cart=cart,
                user=request.user if request.user.is_authenticated else None,
                customer_name=form.cleaned_data["customer_name"],
                phone=form.cleaned_data["phone"],
                email=form.cleaned_data.get("email") or "",
                delivery_type=form.cleaned_data["delivery_type"],
                payment_type=form.cleaned_data["payment_type"],
                address=form.cleaned_data.get("address") or "",
                comment=form.cleaned_data.get("comment") or "",
            )
            if order:
                if not request.user.is_authenticated:
                    request.session["last_order_id"] = order.pk
                messages.success(request, f"Заказ №{order.pk} принят. Спасибо!")
                return redirect("shop:order_detail", pk=order.pk)
            messages.error(request, err or "Ошибка оформления.")
    else:
        form = CheckoutForm(initial=initial, user=request.user)
    return render(request, "shop/checkout.html", {"form": form, "cart": get_cart(request)})


def _constructor_context(request, active_quarter=None):
    ingredients = Ingredient.objects.all()
    state = get_builder_state(request)
    price = builder_price(state)
    if active_quarter is None:
        try:
            active_quarter = int(request.GET.get("quarter", 1))
        except (TypeError, ValueError):
            active_quarter = 1
    if active_quarter not in (1, 2, 3, 4):
        active_quarter = 1
    toppings_by_q = {1: [], 2: [], 3: [], 4: []}
    for t in state["toppings"]:
        ing = ingredients.filter(pk=t.get("iid")).first()
        if ing:
            toppings_by_q[int(t["q"])].append(ing)
    quarters = []
    filled_quarters = set()
    for i in (1, 2, 3, 4):
        tops = toppings_by_q[i]
        image_urls = [ing.image.url for ing in tops if ing.image]
        if tops:
            filled_quarters.add(i)
        quarters.append({"num": i, "tops": tops, "image_urls": image_urls})
    active_toppings = toppings_by_q[active_quarter]
    return {
        "ingredients": ingredients,
        "state": state,
        "price": price,
        "quarters": quarters,
        "active_quarter": active_quarter,
        "active_toppings": active_toppings,
        "all_quarters_filled": filled_quarters == {1, 2, 3, 4},
        "crust_labels": CRUST_LABELS,
        "size_labels": SIZE_LABELS,
    }


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def constructor(request):
    context = _constructor_context(request)
    return render(request, "shop/constructor.html", context)


def constructor_fragment(request):
    context = _constructor_context(request)
    return render(request, "shop/_constructor_content.html", context)


@require_POST
def constructor_set_options(request):
    state = get_builder_state(request)
    crust = request.POST.get("crust")
    size = request.POST.get("size")
    try:
        active_quarter = int(request.POST.get("quarter") or 1)
    except ValueError:
        active_quarter = 1
    if crust in ("thin", "thick"):
        state["crust"] = crust
    if size in ("small", "medium", "large"):
        state["size"] = size
    set_builder_state(request, state)
    if _is_ajax(request):
        return render(request, "shop/_constructor_content.html", _constructor_context(request, active_quarter))
    return redirect("shop:constructor")


@require_POST
def constructor_add_topping(request):
    q = int(request.POST.get("quarter") or 0)
    iid = int(request.POST.get("ingredient_id") or 0)
    if q in (1, 2, 3, 4) and Ingredient.objects.filter(pk=iid).exists():
        add_builder_topping(request, q, iid)
    if _is_ajax(request):
        return render(request, "shop/_constructor_content.html", _constructor_context(request, q))
    return redirect(f"{reverse('shop:constructor')}?quarter={q}")


@require_POST
def constructor_remove_topping(request):
    q = int(request.POST.get("quarter") or 0)
    iid = int(request.POST.get("ingredient_id") or 0)
    if q in (1, 2, 3, 4):
        remove_builder_topping(request, q, iid)
    if _is_ajax(request):
        return render(request, "shop/_constructor_content.html", _constructor_context(request, q))
    return redirect(f"{reverse('shop:constructor')}?quarter={q}")


@require_POST
def constructor_add_to_cart(request):
    ok, err = cart_add_custom_from_session(request)
    if ok:
        if _is_ajax(request):
            return JsonResponse({"ok": True, "redirect_url": reverse("shop:cart")})
        messages.success(request, "Собранная пицца добавлена в корзину.")
        return redirect("shop:cart")
    if _is_ajax(request):
        return JsonResponse({"ok": False, "error": err or "Не удалось добавить."}, status=400)
    messages.error(request, err or "Не удалось добавить.")
    return redirect("shop:constructor")


@require_POST
def constructor_reset(request):
    clear_builder(request)
    if _is_ajax(request):
        return render(request, "shop/_constructor_content.html", _constructor_context(request, 1))
    messages.info(request, "Конструктор сброшен.")
    return redirect("shop:constructor")


class ShopLoginView(LoginView):
    template_name = "shop/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        old_session_key = self.request.session.session_key
        response = super().form_valid(form)
        merge_session_cart_into_user(self.request, self.request.user, session_key=old_session_key)
        return response


class ShopLogoutView(LogoutView):
    next_page = reverse_lazy("shop:home")


def register(request):
    if request.user.is_authenticated:
        return redirect("shop:profile")
    if request.method == "POST":
        f = RegisterForm(request.POST)
        if f.is_valid():
            user = f.save()
            old_session_key = request.session.session_key
            login(request, user)
            merge_session_cart_into_user(request, user, session_key=old_session_key)
            messages.success(request, "Добро пожаловать!")
            return redirect("shop:profile")
    else:
        f = RegisterForm()
    return render(request, "shop/register.html", {"form": f})


@login_required
def profile(request):
    profile_form = ProfileForm(instance=request.user.profile, user=request.user)
    if request.method == "POST" and "save_profile" in request.POST:
        profile_form = ProfileForm(request.POST, instance=request.user.profile, user=request.user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Профиль сохранён.")
            return redirect("shop:profile")
    orders = Order.objects.filter(user=request.user)[:20]
    addresses = request.user.saved_addresses.all()
    return render(
        request,
        "shop/profile.html",
        {"profile_form": profile_form, "orders": orders, "addresses": addresses},
    )


@login_required
def saved_address_create(request):
    if request.method == "POST":
        form = SavedAddressForm(request.POST)
        if form.is_valid():
            addr = form.save(commit=False)
            addr.user = request.user
            addr.save()
            messages.success(request, "Адрес сохранён.")
            return redirect("shop:profile")
    else:
        form = SavedAddressForm()
    return render(request, "shop/address_form.html", {"form": form, "title": "Новый адрес"})


@login_required
def saved_address_delete(request, pk):
    addr = get_object_or_404(SavedAddress, pk=pk, user=request.user)
    addr.delete()
    messages.info(request, "Адрес удалён.")
    return redirect("shop:profile")


@login_required
def orders_list(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, "shop/order_list.html", {"orders": orders})


def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    allowed = False
    if request.user.is_authenticated:
        allowed = order.user_id == request.user.id or request.user.is_staff
    elif request.session.get("last_order_id") == order.pk:
        allowed = True
    if not allowed:
        raise Http404()
    return render(request, "shop/order_detail.html", {"order": order})


@login_required
@require_POST
def repeat_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    repeat_order_to_cart(request, order)
    messages.success(request, "Позиции из заказа добавлены в корзину (если были в наличии).")
    return redirect("shop:cart")

def pop(request):
    return render(request,"shop/pop.html")

