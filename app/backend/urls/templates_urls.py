from django.urls import path
from ..views import templates_views
from django.contrib.auth.views import LogoutView


urlpatterns = [
    path("", templates_views.index, name="tmp_index"),
    path("register/", templates_views.register, name="tmp_register"),
    path("login/", templates_views.login_view, name="tmp_login"),
    path("logout/", LogoutView.as_view(next_page="/templates/login/"), name="tmp_logout"),
    path("home/", templates_views.home, name="tmp_home"),
]
