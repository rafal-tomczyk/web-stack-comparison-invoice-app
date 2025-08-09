from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from rest_framework.reverse import reverse_lazy

from ..forms.templates_forms.forms import RegisterForm

from ..models import Client, Company, User, Invoice, Product


def index(request):
    return render(request, "frontend_templates/index.html")


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect("tmp_choose_company")
    else:
        form = AuthenticationForm()
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
            total_revenue=Sum(F("invoiceitem__quantity") * F("invoiceitem__net_price")),
            total_quantity=Sum("invoiceitem__quantity")
        )
        .filter(total_revenue__isnull=False)
        .order_by("-total_revenue")[:limit]
    )

@login_required()
def home(request):
    active_company = None
    invoices, top_products, top_clients = [], [], []
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            active_company = Company.objects.get(id=int(company_id), user=request.user)
            invoices = Invoice.objects.filter(company=company_id).order_by(
                "-issue_date")[:10]

            top_products = get_top_products(active_company)

            top_clients = (
                Client.objects.filter(company=active_company)
                .annotate(total_spent=Sum("invoices__total_gross"))
                .filter(total_spent__isnull=False)
                .order_by("-total_spent")[:5]
            )
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


class ClientsListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "frontend_templates/clients.html"
    context_object_name = "clients"

    def get_queryset(self):
        return Client.objects.filter(company__user=self.request.user)


class InvoicesListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = "frontend_templates/invoices.html"
    context_object_name = "invoices"

    def get_queryset(self):
        return Invoice.objects.filter(company__user=self.request.user)


class ProductsListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "frontend_templates/products.html"
    context_object_name = "products"

    def get_queryset(self):
        company_id = self.request.session.get('active_company_id')
        if company_id:
            return Product.objects.filter(company_id=company_id, company__user=self.request.user)
        return Product.objects.none()


class ProductsDetailView(DetailView):
    model = Product
    template_name = "frontend_templates/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.filter(company__user=self.request.user)

class ProductUpdateView(UpdateView):
    model = Product
    fields = ['name', 'description', 'unit_type', 'net_price', 'tax_rate']
    template_name = "frontend_templates/product_form.html"

    def get_success_url(self):
        return reverse("tmp_product_detail", kwargs={"pk": self.object.pk})

class ProductDeleteView(DeleteView):
    model = Product
    template_name = "frontend_templates/product_confirm_delete.html"
    success_url = reverse_lazy("tmp_products")
