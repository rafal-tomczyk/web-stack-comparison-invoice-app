from django.urls import path
from ..views import templates_views
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path("", templates_views.index, name="index"),
    path("register/", templates_views.register, name="register"),
    path("login/", templates_views.login_view, name="login"),
    path("logout/", LogoutView.as_view(next_page="/templates/login/"), name="logout"),
    path("home/", templates_views.home, name="home"),
]
