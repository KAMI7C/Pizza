from .utils import get_cart


def cart_summary(request):
    cart = get_cart(request)
    return {"cart_count": cart.items_count(), "cart_total": cart.total()}
