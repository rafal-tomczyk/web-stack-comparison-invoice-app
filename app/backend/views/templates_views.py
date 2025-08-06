from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import ListView

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
            return redirect("/templates/home")
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

def get_clients_for_user(user):
    return Client.objects.filter(company__user=user)

def home(request):
    if not request.user.is_authenticated:
        return render(request, "frontend_templates/home_public.html")

    clients = get_clients_for_user(request.user)
    return render(
        request,
        "frontend_templates/home_authenticated.html",
        {"clients": clients}
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
        return Product.objects.filter(company__user=self.request.user)
