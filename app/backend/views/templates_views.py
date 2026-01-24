import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F, Max, Case, When, Value, CharField
from django.db.models.functions import Concat
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login
from django.contrib import messages
from django.template.loader import get_template
from django.urls import reverse
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, \
    CreateView
from rest_framework.reverse import reverse_lazy
from weasyprint import HTML

from ..forms.templates_forms.forms import RegisterForm, LoginForm, ProductForm, \
    ClientForm, InvoiceForm, InvoiceItemFormSet, CompanyForm
from django.db.models.functions import Round, TruncMonth
from django.db.models import Q

from ..models import Client, Company, User, Invoice, Product, InvoiceItem
from django.http import JsonResponse, HttpResponse

logger = logging.getLogger(__name__)

class BaseSecuredView(LoginRequiredMixin):
    login_url = 'tmp_login'
    redirect_field_name = None


def index(request):
    return render(request, "frontend_templates/index.html")


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect("tmp_choose_company")
    else:
        form = LoginForm()
    return render(
        request,
        "frontend_templates/login.html",
        {"form": form})

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("/templates/home")
    else:
        form = RegisterForm()
    return render(
        request,
        "frontend_templates/register.html",
        {"form": form}
    )

def get_top_products(company, limit=5):
    return (
        Product.objects.filter(company=company)
        .annotate(
            total_revenue=Round(Sum(F("invoiceitem__quantity") * F("invoiceitem__net_price")), precision=2),
            total_quantity=Sum("invoiceitem__quantity")
        )
        .filter(total_revenue__isnull=False)
        .order_by("-total_revenue")[:limit]
    )



@login_required()
def home(request):
    active_company = None
    invoices, top_products, top_clients = [], [], []
    monthly_revenue: float = 0
    yearly_revenue: float = 0
    monthly_revenues_json = {}

    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            active_company = Company.objects.get(id=company_id, user=request.user)
            invoices = active_company.get_latest_invoices()
            top_products = active_company.get_top_products()
            top_clients = active_company.get_top_clients()

            monthly_revenues_json = active_company.get_monthly_revenues_json()
            monthly_revenue = active_company.get_current_monthly_revenue()
            yearly_revenue = active_company.get_yearly_revenue()

        except Company.DoesNotExist:
            active_company = None

    return render(
        request,
        "frontend_templates/home_authenticated.html",
        {
            "active_company": active_company,
            "invoices": invoices,
            "top_products": top_products,
            "top_clients": top_clients,
            "monthly_revenues": monthly_revenues_json,
            "monthly_revenue": monthly_revenue,
            "yearly_revenue": yearly_revenue
        }
    )

@login_required()
def choose_company(request):
    user_companies = Company.objects.filter(user=request.user)
    if request.method == "POST":
        company_id = request.POST.get("company_id")
        if user_companies.filter(id=company_id).exists():
            request.session['active_company_id'] = company_id
            return redirect("tmp_home")
        else:
            pass
    return render(
        request,
        "frontend_templates/choose_company.html",
        {"companies": user_companies}
    )


def handle_form_valid(view, form):
    active_company_id = view.request.session.get('active_company_id')
    if not active_company_id:
        form.add_error(None, "Nie wybrano aktywnej firmy.")
        return view.form_invalid(form)
    try:
        company = Company.objects.get(id=active_company_id)
    except Company.DoesNotExist:
        form.add_error(None, "Aktywna firma nie istnieje.")
        return view.form_invalid(form)

    form.instance.company = company
    return super(view.__class__, view).form_valid(form)

class CompanyCreateView(BaseSecuredView, CreateView):
    model = Company
    template_name = "frontend_templates/company_create.html"
    form_class = CompanyForm
    success_url = reverse_lazy('tmp_choose_company')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class ClientsListView(BaseSecuredView, ListView):
    model = Client
    template_name = "frontend_templates/clients.html"
    context_object_name = "clients"
    paginate_by = 10


    def get_queryset(self):
        company_id: int = self.request.session.get('active_company_id')
        if not company_id:
            return Client.objects.none()

        queryset = Client.objects.filter(company__user=self.request.user, company_id=company_id)

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(surname__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(nip__icontains=search_query)
            )

        queryset = queryset.annotate(
            full_name_or_company=Case(
                When(client_company_name__isnull=False,
                     then='client_company_name'),
                default=Concat('name', Value(' '), 'surname',
                               output_field=CharField()),
                output_field=CharField(),
            )
        )
        sort_param = self.request.GET.get('sort', '-id')
        return queryset.order_by(sort_param)

class ClientCreateView(BaseSecuredView, CreateView):
    model = Client
    template_name = "frontend_templates/client_create.html"
    form_class = ClientForm
    success_url = reverse_lazy('tmp_clients')

    def form_valid(self, form):
        return handle_form_valid(self, form)

class ClientDetailView(BaseSecuredView, DetailView):
    model = Client
    template_name = "frontend_templates/client_detail.html"
    context_object_name = "client"

    def get_queryset(self):
        return Client.objects.filter(company__user=self.request.user)

class InvoicesListView(BaseSecuredView, ListView):
    model = Invoice
    template_name = 'frontend_templates/invoices.html'
    context_object_name = 'invoices'
    paginate_by = 10

    def get_queryset(self):
        company_id: int = self.request.session.get('active_company_id')
        if not company_id:
            return Invoice.objects.none()

        queryset = self.model.objects.filter(company__user=self.request.user, company_id=company_id)
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(number__icontains=search_query) |
                Q(client__name__icontains=search_query)
            )
        sort_param = self.request.GET.get('sort', '-issue_date')

        if sort_param.lstrip('-') == 'number':
            reverse = sort_param.startswith('-')
            queryset = sorted(
                queryset,
                key=lambda inv: (
                    int(inv.number.split('/')[2]),
                    int(inv.number.split('/')[1]),
                    int(inv.number.split('/')[0])
                ),
                reverse=reverse
            )

        else:
            queryset = queryset.order_by(sort_param)

        return queryset

class InvoiceDetailView(BaseSecuredView, DetailView):
    model = Invoice
    template_name = 'frontend_templates/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['items'] = self.object.items.all()
        return context

class InvoiceCreateView(BaseSecuredView, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'frontend_templates/invoice_create.html'
    success_url = reverse_lazy('tmp_invoices')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        company_id = self.request.session.get('active_company_id')
        if company_id:
            form.fields['client'].queryset = Client.objects.filter(
                company_id=company_id,
                company__user=self.request.user
            )
        else:
            form.fields['client'].queryset = Client.objects.none()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company_id = self.request.session.get('active_company_id')

        # Use an unsaved Invoice instance to properly initialize the inline formset
        temp_invoice = Invoice()

        if self.request.POST:
            context['item_formset'] = InvoiceItemFormSet(self.request.POST, instance=temp_invoice, prefix='items')
        else:
            context['item_formset'] = InvoiceItemFormSet(instance=temp_invoice, prefix='items')

        for form in context['item_formset'].forms:
            form.fields['product'].queryset = Product.objects.filter(company_id=company_id)

        return context

    def form_valid(self, form):
        company_id = self.request.session.get('active_company_id')
        form.instance.company = Company.objects.get(id=company_id)

        context = self.get_context_data()
        item_formset = context['item_formset']


        if item_formset.is_valid():
            invoice = form.save()

            item_formset.instance = invoice
            item_formset.save()

            invoice.update_totals()
            if self.request.headers.get("HX-Request") == "true":
                response = HttpResponse()
                response["HX-Redirect"] = reverse("htmx_home") + "?view=invoices"
                return response

            return redirect(self.success_url)
        return self.form_invalid(form)


class ProductsListView(BaseSecuredView, ListView):
    model = Product
    template_name = "frontend_templates/products.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):
        company_id: int = self.request.session.get('active_company_id')
        if not company_id:
            return Product.objects.none()
        
        queryset = Product.objects.filter(
            company_id=company_id,
            company__user=self.request.user
        )

        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        sort_param = self.request.GET.get('sort', '-created_at')
        return queryset.order_by(sort_param)

class ProductsDetailView(BaseSecuredView, DetailView):
    model = Product
    template_name = "frontend_templates/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.filter(company__user=self.request.user)

class ProductCreateView(BaseSecuredView, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'frontend_templates/product_create.html'
    success_url = reverse_lazy('tmp_products')

    def form_valid(self, form):
        return handle_form_valid(self, form)

class ProductUpdateView(BaseSecuredView, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "frontend_templates/product_create.html"

    def get_success_url(self):
        return reverse("tmp_product_detail", kwargs={"pk": self.object.pk})

class ProductDeleteView(BaseSecuredView, DeleteView):
    model = Product
    template_name = "frontend_templates/product_confirm_delete.html"
    success_url = reverse_lazy("tmp_products")




@login_required
def product_data(request, pk):
    product = Product.objects.get(pk=pk)
    return JsonResponse({
        'net_price': str(product.net_price),
        'tax_rate': str(product.tax_rate)
    })


@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.company.user != request.user:
        return HttpResponse('Brak uprawnień do tej faktury', status=403)

    context = {
        'invoice': invoice,
    }

    template = get_template('frontend_templates/invoice_pdf.html')
    html_string = template.render(context)

    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment;filename="faktura_{invoice.number}.pdf"'

    return response


@login_required
def toggle_invoice_paid(request, pk):
    if request.method != "POST":
        return redirect('tmp_invoice_detail', pk=pk)

    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.company.user != request.user:
        messages.error(request, 'Nie masz uprawnień do zmiany statusu tej faktury.')

    invoice.paid = not invoice.paid
    invoice.save()

    status = "opłacona" if invoice.paid else "nieopłacona"
    messages.success(request, f'Faktura {invoice.number} została oznaczona jako {status}.')

    return redirect('tmp_invoice_detail', pk=pk)
