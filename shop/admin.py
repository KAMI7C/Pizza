from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Cart,
    CartItem,
    Category,
    CustomPizza,
    CustomPizzaTopping,
    Ingredient,
    Order,
    OrderItem,
    Product,
    Promotion,
    SavedAddress,
    UserProfile,
)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Профиль пиццерии"


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "price_extra")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


class CustomPizzaToppingInline(admin.TabularInline):
    model = CustomPizzaTopping
    extra = 0


@admin.register(CustomPizza)
class CustomPizzaAdmin(admin.ModelAdmin):
    list_display = ("id", "crust", "size", "price_cached")
    inlines = (CustomPizzaToppingInline,)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ("unit_price", "line_total")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session_key", "updated_at")
    inlines = (CartItemInline,)
    search_fields = ("session_key", "user__username")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "spiciness", "popularity", "in_stock")
    list_filter = ("category", "spiciness", "in_stock")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("ingredients",)
    search_fields = ("name", "composition")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "discount_percent", "starts_at", "ends_at")
    list_filter = ("is_active",)


@admin.register(SavedAddress)
class SavedAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "address")
    search_fields = ("address", "user__username")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("title", "unit_price", "line_total")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "phone", "status", "delivery_type", "total", "created_at")
    list_editable = ("status",)
    list_filter = ("status", "delivery_type", "payment_type")
    search_fields = ("phone", "customer_name", "email", "address")
    readonly_fields = ("created_at", "updated_at", "total")
    inlines = (OrderItemInline,)
    fieldsets = (
        (None, {"fields": ("user", "status", "total")}),
        ("Клиент", {"fields": ("customer_name", "phone", "email")}),
        ("Доставка и оплата", {"fields": ("delivery_type", "payment_type", "address", "estimated_delivery_at")}),
        ("Комментарий", {"fields": ("comment",)}),
        ("Даты", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "is_blocked")
    list_filter = ("is_blocked",)
    search_fields = ("user__username", "phone")
