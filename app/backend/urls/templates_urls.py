from django.urls import path, reverse_lazy
from ..views import templates_views
from django.contrib.auth.views import LogoutView

from ..views.templates_views import ClientsListView, InvoicesListView, \
    ProductsListView

urlpatterns = [
    #auth
    path("register/", templates_views.register, name="tmp_register"),
    path("login/", templates_views.login_view, name="tmp_login"),
    path("logout/", LogoutView.as_view(next_page=reverse_lazy("tmp_login")),
         name="tmp_logout"),

    #index
    path("", templates_views.index, name="tmp_index"),
    path("home/", templates_views.home, name="tmp_home"),

    #dashboard
    path("clients/", ClientsListView.as_view(), name="tmp_clients"),
    path("invoices/", InvoicesListView.as_view(), name="tmp_invoices"),
    path("products/", ProductsListView.as_view(), name="tmp_products")
]
