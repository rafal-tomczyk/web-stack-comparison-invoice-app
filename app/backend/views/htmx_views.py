from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q

from ..models import Invoice, Client, Product
from ..forms.templates_forms.forms import ClientForm, ProductForm, InvoiceForm, \
    InvoiceItemFormSet, InvoiceItemForm


def is_hx(request) -> bool:
    return request.headers.get('HX-Request', 'false') == 'true'


class InvoiceDetailHTMXView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'htmx_templates/invoice_detail_htmx.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        return context


class ToggleInvoicePaidHTMXView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, company__user=request.user)
        invoice.paid = not invoice.paid
        invoice.save()
        return render(request, 'htmx_templates/_invoice_header.html', {'invoice': invoice})

class ClientDetailHTMXView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'htmx_templates/client_detail_htmx.html'
    context_object_name = 'client'

    def get_queryset(self):
        return Client.objects.filter(company__user=self.request.user)


class ClientCreateHTMXView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'htmx_templates/client_create_htmx.html'

    def form_valid(self, form):
        active_company_id = self.request.session.get('active_company_id')
        if not active_company_id:
            form.add_error(None, 'Nie wybrano aktywnej firmy.')
            return self.form_invalid(form)
        try:
            company = Company.objects.get(id=active_company_id, user=self.request.user)
        except Company.DoesNotExist:
            form.add_error(None, 'Aktywna firma nie istnieje.')
            return self.form_invalid(form)
        form.instance.company = company
        response = super().form_valid(form)
        return response

    def get_success_url(self):
        return reverse('htmx_clients')


# ==== Products (HTMX) ====
class ProductsListHTMXView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'htmx_templates/products_htmx.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        company_id = self.request.session.get('active_company_id')
        if not company_id:
            return Product.objects.none()
        queryset = Product.objects.filter(company_id=company_id, company__user=self.request.user)
        sort_param = self.request.GET.get('sort', '-created_at')
        return queryset.order_by(sort_param)

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('active_company_id'):
            if is_hx(request):
                return render(request, 'htmx_templates/_product_list.html', {
                    'products': [],
                    'is_paginated': False,
                    'page_obj': None,
                    'request': request,
                    'no_company_selected': True
                })
            return redirect('tmp_choose_company')
        return super().dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        if is_hx(self.request):
            # To zwraca tylko fragment, co jest super dla AJAX, ale ZŁE dla redirecta
            return render(self.request, 'htmx_templates/_invoice_list.html',
                          context)
        return super().render_to_response(context, **response_kwargs)

class ProductDetailHTMXView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = 'htmx_templates/product_detail_htmx.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.filter(company__user=self.request.user)


class ProductCreateHTMXView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'htmx_templates/product_create_htmx.html'

    def form_valid(self, form):
        active_company_id = self.request.session.get('active_company_id')
        if not active_company_id:
            form.add_error(None, 'Nie wybrano aktywnej firmy.')
            return self.form_invalid(form)
        try:
            form.instance.company = Company.objects.get(id=active_company_id, user=self.request.user)
        except Company.DoesNotExist:
            form.add_error(None, 'Aktywna firma nie istnieje.')
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('htmx_products')


class ProductUpdateHTMXView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'htmx_templates/product_create_htmx.html'

    def get_queryset(self):
        return Product.objects.filter(company__user=self.request.user)

    def get_success_url(self):
        return reverse('htmx_product_detail', kwargs={'pk': self.object.pk})


class ProductDeleteHTMXView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = 'htmx_templates/product_confirm_delete_htmx.html'
    success_url = reverse_lazy('htmx_products')

    def get_queryset(self):
        return Product.objects.filter(company__user=self.request.user)

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404, render
from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from django.db.models import Case, When, Value, CharField, Sum
from django.db.models.functions import Concat, TruncMonth, Round
from django.contrib.auth.decorators import login_required
from datetime import datetime

from ..models import Invoice, Client, Company, Product
from ..forms.templates_forms.forms import ClientForm, ProductForm


def is_hx(request) -> bool:
    return request.headers.get('HX-Request', 'false') == 'true'


class InvoicesListHTMXView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'htmx_templates/invoices_htmx.html'
    context_object_name = 'invoices'
    paginate_by = 10

    def get_queryset(self):
        company_id = self.request.session.get('active_company_id')
        if not company_id:
            return self.model.objects.none()

        queryset = self.model.objects.filter(company__user=self.request.user, company_id=company_id)
        sort_param = self.request.GET.get('sort', '-issue_date')

        if sort_param.lstrip('-') == 'number':
            reverse_sort = sort_param.startswith('-')
            queryset = sorted(
                queryset,
                key=lambda inv: (
                    int(inv.number.split('/')[2]),
                    int(inv.number.split('/')[1]),
                    int(inv.number.split('/')[0])
                ),
                reverse=reverse_sort
            )
        else:
            queryset = queryset.order_by(sort_param)
        return queryset

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('active_company_id'):
            if is_hx(request):
                return render(request, 'htmx_templates/_invoice_list.html', {
                    'invoices': [],
                    'is_paginated': False,
                    'page_obj': None,
                    'request': request,
                    'no_company_selected': True
                })
            return redirect('tmp_choose_company')
        return super().dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        if is_hx(self.request):
            return render(self.request, 'htmx_templates/_invoice_list.html', context)
        return super().render_to_response(context, **response_kwargs)


class InvoiceDetailHTMXView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'htmx_templates/invoice_detail_htmx.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        return context


class ToggleInvoicePaidHTMXView(LoginRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk, company__user=request.user)
        invoice.paid = not invoice.paid
        invoice.save()
        return render(request, 'htmx_templates/_invoice_header.html', {'invoice': invoice})


# ==== HTMX Home ====
@login_required
def htmx_home(request):
    active_company = None
    monthly_revenue = 0
    yearly_revenue = 0
    monthly_revenues_json = {}

    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            active_company = Company.objects.get(id=company_id, user=request.user)

            monthly_revenues_json = active_company.get_monthly_revenues_json()
            monthly_revenue = active_company.get_current_monthly_revenue()
            yearly_revenue = active_company.get_yearly_revenue()
        except Company.DoesNotExist:
            active_company = None

    return render(
        request,
        'htmx_templates/home_authenticated_htmx.html',
        {
            'active_company': active_company,
            'monthly_revenues': monthly_revenues_json,
            'monthly_revenue': monthly_revenue,
            'yearly_revenue': yearly_revenue,
        }
    )

def htmx_home_top_products(request):
    company = get_active_company(request)
    products = company.get_top_products() if company else []
    return render(
        request,
        'htmx_templates/partials/home/_top_products.html',
        { 'top_products': products }
    )

def htmx_home_top_clients(request):
    company = get_active_company(request)
    top_clients = company.get_top_clients() if company else []
    return render(
        request,
        'htmx_templates/partials/home/_top_clients.html',
        { 'top_clients': top_clients }
    )

def htmx_home_latest_invoices(request):
    company = get_active_company(request)
    invoices = company.get_latest_invoices() if company else []
    return render(
        request,
        'htmx_templates/partials/home/_latest_invoices.html',
        {"invoices": invoices}
    )

def htmx_home_calendar(request):
    return render(request, 'htmx_templates/partials/home/_calendar.html')

def get_active_company(request):
    company_id = request.session.get("active_company_id")
    if not company_id:
        return None
    return Company.objects.filter(id=company_id, user=request.user).first()

@login_required
def htmx_generic_list(request, kind):
    company = get_active_company(request)
    if not company:
        return HttpResponse("Brak firmy", status=400)

    CONFIG = {
        "invoices": {
            "get_queryset": lambda: get_invoice_queryset(request),
            "header_template": "htmx_templates/partials/list/header/invoice_header.html",
            "row_template": "htmx_templates/partials/list/row/invoice_row.html",
            "title": "Faktury",
            "list_title": "Lista Faktur",
            "add_url": reverse("htmx_invoice_add"),
            "search_fields": [
                ("all", "Wszystkie pola"),
                ("number", "Numer faktury"),
                ("client__name", "Imię klienta"),
                ("client__surname", "Nazwisko klienta"),
                ("client__client_company_name", "Firma klienta"),
            ]
        },
        "clients": {
            "get_queryset": lambda: get_client_queryset(request),
            "header_template": "htmx_templates/partials/list/header/client_header.html",
            "row_template": "htmx_templates/partials/list/row/client_row.html",
            "title": "Klienci",
            "list_title": "Lista klientów",
            "add_url": reverse("tmp_client_add"),
            "search_fields": [
                ("all", "Wszystkie pola"),
                ("name", "Imię"),
                ("surname", "Nazwisko"),
                ("email", "Email"),
                ("nip", "NIP"),
                ("client_company_name", "Nazwa firmy"),
            ]
        },
        "products": {
            "get_queryset": lambda: get_product_queryset(request),
            "header_template": "htmx_templates/partials/list/header/product_header.html",
            "row_template": "htmx_templates/partials/list/row/product_row.html",
            "title": "Produkty",
            "list_title": "Lista produktów",
            "add_url": reverse("tmp_product_add"),
            "search_fields": [
                ("all", "Wszystkie pola"),
                ("name", "Nazwa"),
                ("description", "Opis"),
            ]
        }
    }

    cfg = CONFIG.get(kind)
    if not cfg:
        return HttpResponse(status=404)


    objects = cfg["get_queryset"]()

    paginator = Paginator(objects, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "htmx_templates/base_list.html",
        {
            **cfg,
            "objects": page_obj,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
        },
    )


def get_invoice_queryset(request):
    company_id = request.session.get("active_company_id")
    if not company_id:
        return Invoice.objects.none()

    qs = Invoice.objects.filter(
        company__user=request.user,
        company_id=company_id
    )

    search_query = request.GET.get('search')
    if search_query:
        qs = qs.filter(
            Q(number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(client__surname__icontains=search_query) |
            Q(client__client_company_name__icontains=search_query)
        )

    sort_param = request.GET.get("sort", "-issue_date")

    if sort_param.lstrip("-") == "number":
        reverse = sort_param.startswith("-")
        return sorted(
            qs,
            key=lambda inv: (
                int(inv.number.split("/")[2]),
                int(inv.number.split("/")[1]),
                int(inv.number.split("/")[0]),
            ),
            reverse=reverse,
        )

    return qs.order_by(sort_param)


def get_client_queryset(request):
    company_id = request.session.get("active_company_id")
    if not company_id:
        return Client.objects.none()

    qs = Client.objects.filter(
        company__user=request.user,
        company_id=company_id
    )

    search_query = request.GET.get('search')
    if search_query:
        qs = qs.filter(
            Q(name__icontains=search_query) |
            Q(surname__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(nip__icontains=search_query) |
            Q(client_company_name__icontains=search_query)
        )

    qs = qs.annotate(
        full_name_or_company=Case(
            When(
                client_company_name__isnull=False,
                then="client_company_name",
            ),
            default=Concat(
                "name",
                Value(" "),
                "surname",
                output_field=CharField(),
            ),
            output_field=CharField(),
        )
    )

    sort_param = request.GET.get("sort", "-id")

    return qs.order_by(sort_param)


def get_product_queryset(request):
    company_id = request.session.get("active_company_id")
    if not company_id:
        return Product.objects.none()

    qs = Product.objects.filter(
        company__user=request.user,
        company_id=company_id
    )

    search_query = request.GET.get('search')
    if search_query:
        qs = qs.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    sort_param = request.GET.get('sort', '-created_at')
    return qs.order_by(sort_param)

def htmx_invoice_add(request):
    company_id = request.session.get("active_company_id")
    if not company_id:
        return HttpResponse("Brak aktywnej firmy", status=400)

    try:
        company = Company.objects.get(id=company_id, user=request.user)
    except Company.DoesNotExist:
        return HttpResponse("Firma nie istnieje", status=400)

    if request.method == "POST":
        form = InvoiceForm(request.POST)
        item_formset = InvoiceItemFormSet(request.POST, prefix="items")

        # Ustaw queryset dla klientów
        form.fields['client'].queryset = Client.objects.filter(
            company_id=company_id, company__user=request.user
        )

        # Ustaw queryset produktów dla wszystkich formularzy w formsecie
        for f in item_formset.forms:
            f.fields["product"].queryset = Product.objects.filter(
                company_id=company_id)

        if form.is_valid() and item_formset.is_valid():
            # Zapisz fakturę
            invoice = form.save(commit=False)
            invoice.company = company
            invoice.save()

            # Zapisz pozycje faktury
            item_formset.instance = invoice
            item_formset.save()

            # Przelicz totale
            invoice.update_totals()

            # Po zapisaniu przekieruj do listy faktur przez HTMX
            if is_hx(request):
                # Pobierz URL listy faktur
                list_url = reverse("htmx_list", kwargs={"kind": "invoices"})

                # Dodaj nagłówek, który zmieni URL w pasku przeglądarki
                response = HttpResponse(status=200)
                response['HX-Push-Url'] = list_url

                # Wywołaj widok listy generycznej ręcznie
                return htmx_generic_list(request, kind="invoices")

            return redirect("htmx_list", kind="invoices")
        else:
            # Jeśli są błędy walidacji, pokaż formularz z błędami
            print("Form errors:", form.errors)  # Debug
            print("Formset errors:", item_formset.errors)  # Debug
            print("Non-form errors:", item_formset.non_form_errors)  # Debug
    else:
        # GET - pokaż pusty formularz
        form = InvoiceForm()
        form.fields['client'].queryset = Client.objects.filter(
            company_id=company_id, company__user=request.user
        )

        item_formset = InvoiceItemFormSet(prefix="items")

    # Ustaw queryset produktów dla wszystkich formularzy w formsecie
    for f in item_formset.forms:
        f.fields["product"].queryset = Product.objects.filter(
            company_id=company_id)

    return render(
        request,
        "htmx_templates/invoice_create_htmx.html",
        {
            "form": form,
            "item_formset": item_formset,
        },
    )


def htmx_home_chart(request):
    monthly_revenue = 0
    yearly_revenue = 0
    monthly_revenues_json = {}

    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            active_company = Company.objects.get(id=company_id, user=request.user)
            # Tu są te ciężkie zapytania SQL:
            monthly_revenues_json = active_company.get_monthly_revenues_json()
            monthly_revenue = active_company.get_current_monthly_revenue()
            yearly_revenue = active_company.get_yearly_revenue()
        except Company.DoesNotExist:
            pass

    return render(
        request,
        'htmx_templates/partials/home/_chart.html',
        {
            'monthly_revenues': monthly_revenues_json,
            'monthly_revenue': monthly_revenue,
            'yearly_revenue': yearly_revenue,
        }
    )


def htmx_invoice_add_item(request):
    """Dodaje nowy wiersz pozycji faktury"""
    company_id = request.session.get("active_company_id")
    if not company_id:
        return HttpResponse(status=400)

    # Pobierz aktualny index z parametrów URL
    current_forms = request.GET.get('total_forms', '0')
    new_index = int(current_forms)

    # Utwórz pusty formset i pobierz empty_form
    formset = InvoiceItemFormSet(prefix="items")
    form = formset.empty_form

    # Zastąp __prefix__ prawdziwym indeksem
    form.prefix = f"items-{new_index}"

    # Ustaw queryset produktów
    form.fields["product"].queryset = Product.objects.filter(
        company_id=company_id, company__user=request.user
    )

    # Ustaw domyślną ilość
    form.fields['quantity'].initial = 1

    return render(
        request,
        "htmx_templates/partials/create/invoice_item_row_htmx.html",
        # ZMIANA: używamy _htmx wersji
        {
            "form": form,
            "new_index": new_index,
        }
    )


# ... existing code ...
def htmx_invoice_item_autofill(request):
    """Automatyczne wypełnianie pól po wyborze produktu"""
    product_id = request.GET.get("product_id")
    prefix = request.GET.get("prefix")

    if not product_id or not prefix:
        return HttpResponse(status=400)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return HttpResponse(status=404)

    # Utwórz formularz z wypełnionymi danymi
    form = InvoiceItemForm(
        initial={
            "product": product.id,
            "net_price": product.net_price,
            "tax_rate": product.tax_rate,
            "quantity": 1,
        },
        prefix=prefix,
    )

    # Ustaw queryset
    company_id = request.session.get("active_company_id")
    form.fields["product"].queryset = Product.objects.filter(
        company_id=company_id)

    return render(
        request,
        "htmx_templates/partials/create/invoice_item_row_htmx.html",
        # ZMIANA: używamy _htmx wersji
        {
            "form": form,
        }
    )
# ... existing code ...
