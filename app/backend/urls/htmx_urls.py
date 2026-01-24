from django.urls import path
from ..views.htmx_views import (
    InvoiceDetailHTMXView,
    ToggleInvoicePaidHTMXView,
    ClientDetailHTMXView,
    ClientCreateHTMXView,
    ProductsListHTMXView,
    ProductDetailHTMXView,
    ProductCreateHTMXView,
    ProductUpdateHTMXView,
    ProductDeleteHTMXView,
    htmx_home, htmx_home_top_products, htmx_home_top_clients,
    htmx_home_latest_invoices, htmx_home_calendar, htmx_generic_list,
    htmx_invoice_add, htmx_invoice_add_item, htmx_invoice_item_autofill,
    htmx_home_chart,
)


urlpatterns = [
    # Home (HTMX)
    path("home/", htmx_home, name="htmx_home"),
    path("home/section/top-products/", htmx_home_top_products, name="htmx_home_top_products"),
    path("home/section/top-clients/", htmx_home_top_clients, name="htmx_home_top_clients"),
    path("home/section/latest-invoices/", htmx_home_latest_invoices, name="htmx_home_latest_invoices"),
    path("home/section/calendar/", htmx_home_calendar, name="htmx_home_calendar"),
    path("home/section/chart/", htmx_home_chart, name="htmx_home_chart"),

    # Section wrappers for SPA swaps
    path("<str:kind>/", htmx_generic_list, name="htmx_list"),

    # Invoices
    path("invoices/<uuid:pk>/", InvoiceDetailHTMXView.as_view(), name="htmx_invoice_detail"),
    path("invoices/<uuid:pk>/toggle-paid/", ToggleInvoicePaidHTMXView.as_view(), name="htmx_toggle_invoice_paid"),
    path("invoices/create/", htmx_invoice_add, name="htmx_invoice_add"),
    path("invoices/add-item/", htmx_invoice_add_item, name="htmx_invoice_add_item"),
    path("invoices/autofill/", htmx_invoice_item_autofill, name="htmx_invoice_item_autofill"),

    # Clients (HTMX)
    path("clients/add/", ClientCreateHTMXView.as_view(), name="htmx_client_add"),
    path("clients/<uuid:pk>/", ClientDetailHTMXView.as_view(), name="htmx_client_detail"),

    # Products (HTMX)
    path("products/", ProductsListHTMXView.as_view(), name="htmx_products"),
    path("products/add/", ProductCreateHTMXView.as_view(), name="htmx_product_add"),
    path("products/<uuid:pk>", ProductDetailHTMXView.as_view(), name="htmx_product_detail"),
    path("products/<uuid:pk>/edit/", ProductUpdateHTMXView.as_view(), name="htmx_product_edit"),
    path("products/<uuid:pk>/delete/", ProductDeleteHTMXView.as_view(), name="htmx_product_delete"),
]
