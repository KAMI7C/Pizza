from django.urls import path

from . import views

app_name = "shop"

urlpatterns = [
    path("", views.home, name="home"),
    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/item/<int:item_id>/update/", views.cart_update, name="cart_update"),
    path("cart/item/<int:item_id>/remove/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("constructor/", views.constructor, name="constructor"),
    path("constructor/fragment/", views.constructor_fragment, name="constructor_fragment"),
    path("constructor/options/", views.constructor_set_options, name="constructor_options"),
    path("constructor/topping/add/", views.constructor_add_topping, name="constructor_add_topping"),
    path("constructor/topping/remove/", views.constructor_remove_topping, name="constructor_remove_topping"),
    path("constructor/add-to-cart/", views.constructor_add_to_cart, name="constructor_add_to_cart"),
    path("constructor/reset/", views.constructor_reset, name="constructor_reset"),
    path("login/", views.ShopLoginView.as_view(), name="login"),
    path("logout/", views.ShopLogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("profile/addresses/new/", views.saved_address_create, name="address_create"),
    path("profile/addresses/<int:pk>/delete/", views.saved_address_delete, name="address_delete"),
    path("orders/", views.orders_list, name="orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/repeat/", views.repeat_order, name="repeat_order"),
    path("pop/",views.pop,name="pop"),

]
