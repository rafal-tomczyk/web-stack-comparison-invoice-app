from django.urls import path, reverse_lazy
from ..views import templates_views
from django.contrib.auth.views import LogoutView
from uuid import UUID

from ..views.templates_views import ClientsListView, InvoicesListView, \
    ProductsListView, ProductsDetailView, ProductUpdateView, ProductDeleteView, \
    choose_company, ProductCreateView, ClientCreateView, ClientDetailView

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
    path("invoices/", InvoicesListView.as_view(), name="tmp_invoices"),
    path("choose-company/", templates_views.choose_company, name="tmp_choose_company"),

    #clients
    path("clients/", ClientsListView.as_view(), name="tmp_clients"),
    path("clients/add/", ClientCreateView.as_view(), name="tmp_client_add"),
    path("clients/<int:pk>/", ClientDetailView.as_view(), name="tmp_client_detail"),

    #products
    path("products/", ProductsListView.as_view(), name="tmp_products"),
    path("products/<uuid:pk>", ProductsDetailView.as_view(), name="tmp_product_detail"),
    path("products/add/", ProductCreateView.as_view(), name="tmp_product_add"),
    path("products/<uuid:pk>/edit/", ProductUpdateView.as_view(),
         name="tmp_product_edit"),
    path("products/<uuid:pk>/delete/", ProductDeleteView.as_view(),
         name="tmp_product_delete"),

]
