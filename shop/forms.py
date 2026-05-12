from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from .models import Order, SavedAddress, UserProfile

PHONE_REGEX = r"^\+375\d{9}$"
PHONE_VALIDATOR = RegexValidator(
    regex=PHONE_REGEX,
    message="Неправильный формат номера. Используйте: +375XXXXXXXXX",
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        label="Email",
        required=True,
        error_messages={"invalid": "Неправильный формат email."},
    )
    phone = forms.CharField(
        label="Телефон",
        max_length=20,
        required=False,
        validators=[PHONE_VALIDATOR],
        help_text="Формат: +375XXXXXXXXX",
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = "Минимум 6 символов и хотя бы одна цифра."
        self.fields["password1"].error_messages.update(
            {
                "required": "Введите пароль.",
            }
        )
        self.fields["password2"].error_messages.update(
            {
                "required": "Повторите пароль.",
            }
        )

    def clean_password1(self):
        password = self.cleaned_data.get("password1", "")
        if len(password) < 6:
            raise forms.ValidationError("Пароль должен быть не короче 6 символов.")
        if not any(ch.isdigit() for ch in password):
            raise forms.ValidationError("Пароль должен содержать хотя бы одну цифру.")
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            if hasattr(user, "profile"):
                user.profile.phone = self.cleaned_data.get("phone") or ""
                user.profile.save()
        return user


class ProfileForm(forms.ModelForm):
    email = forms.EmailField(
        label="Email",
        error_messages={"invalid": "Неправильный формат email."},
    )

    class Meta:
        model = UserProfile
        fields = ("phone",)
        help_texts = {
            "phone": "Формат: +375XXXXXXXXX",
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["phone"].validators.append(PHONE_VALIDATOR)
        if user:
            self.fields["email"].initial = user.email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return phone
        PHONE_VALIDATOR(phone)
        return phone

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit and self.user:
            self.user.email = self.cleaned_data["email"]
            self.user.save()
            profile.save()
        return profile


class SavedAddressForm(forms.ModelForm):
    address = forms.CharField(
        label="Адрес",
        max_length=255,
        error_messages={"required": "Введите адрес доставки."},
    )

    class Meta:
        model = SavedAddress
        fields = ("label", "address")

    def clean_address(self):
        address = (self.cleaned_data.get("address") or "").strip()
        if not any(ch.isdigit() for ch in address):
            raise forms.ValidationError("В адресе должен быть номер дома (хотя бы одна цифра).")
        return address


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(label="Имя", max_length=120)
    phone = forms.CharField(
        label="Телефон",
        max_length=20,
        validators=[PHONE_VALIDATOR],
        help_text="Формат: +375XXXXXXXXX",
        error_messages={"required": "Введите номер телефона."},
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        error_messages={"invalid": "Неправильный формат email."},
    )
    delivery_type = forms.ChoiceField(label="Доставка", choices=Order.DeliveryType.choices)
    payment_type = forms.ChoiceField(label="Оплата", choices=Order.PaymentType.choices)
    address = forms.CharField(label="Адрес доставки", max_length=255, required=False)
    comment = forms.CharField(label="Комментарий к заказу", widget=forms.Textarea, required=False)

    def clean(self):
        data = super().clean()
        address = (data.get("address") or "").strip()
        if data.get("delivery_type") == Order.DeliveryType.COURIER and not address:
            self.add_error("address", "Укажите адрес для доставки курьером.")
            return data
        if address and not any(ch.isdigit() for ch in address):
            self.add_error("address", "В адресе должен быть номер дома (хотя бы одна цифра).")
        return data
