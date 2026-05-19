from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect


class BlockedUserMiddleware:
    """Выход заблокированного пользователя из аккаунта."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = request.user
        if u.is_authenticated:
            profile = getattr(u, "profile", None)
            if profile and profile.is_blocked:
                logout(request)
                messages.error(request, "Доступ к аккаунту ограничен. Обратитесь в пиццерию.")
                return redirect("shop:home")
        return self.get_response(request)
