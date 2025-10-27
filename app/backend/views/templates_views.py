import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F
from django.forms import inlineformset_factory
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login
from django.urls import reverse
from django.views.generic import ListView, DetailView, UpdateView, DeleteView, \
    CreateView
from rest_framework.reverse import reverse_lazy

from ..forms.templates_forms.forms import RegisterForm, LoginForm, ProductForm, \
    ClientForm, InvoiceForm
from django.db.models.functions import Round, TruncMonth

from ..models import Client, Company, User, Invoice, Product, InvoiceItem

logger = logging.getLogger(__name__)


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
    monthly_revenues: list[float] = [0] * 12
    monthly_revenues_json = {}
    company_id = request.session.get('active_company_id')
    if company_id:
        try:
            active_company = Company.objects.get(id=int(company_id), user=request.user)
            # Last invoices
            invoices = Invoice.objects.filter(company=company_id).order_by(
                "-issue_date")[:10]

            # Top products
            top_products = get_top_products(active_company)

            # Top Clients
            top_clients = (
                Client.objects.filter(company=active_company)
                .annotate(total_spent=Sum("invoices__total_gross"))
                .filter(total_spent__isnull=False)
                .order_by("-total_spent")[:5]
            )

            # Monthly revenue
            now = datetime.now()
            revenues = Invoice.objects.filter(
                company=active_company,
                issue_date__year=now.year
            ).annotate(
                month=TruncMonth('issue_date')
            ).values('month').annotate(
                total_revenue=Sum('total_gross')
            ).order_by('month')

            for revenue in revenues:
                month_index = revenue['month'].month - 1
                monthly_revenues[month_index] = revenue['total_revenue'] or 0
                monthly_revenues_json = json.dumps(monthly_revenues,
                                                   default=str)

            monthly_revenue = monthly_revenues[now.month - 1]

            # Yearly revenue
            yearly_revenue = Invoice.objects.filter(
                company=active_company,
                issue_date__year=now.year
            ).aggregate(total_revenue=Sum('total_gross'))['total_revenue'] or 0


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


class ClientsListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = "frontend_templates/clients.html"
    context_object_name = "clients"
    paginate_by = 10

    def get_queryset(self):
        company_id: int = self.request.session.get('active_company_id')
        if company_id:
            return Client.objects.filter(company__user=self.request.user, company_id=company_id)
        return Client.objects.none()

class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    template_name = "frontend_templates/client_create.html"
    form_class = ClientForm
    success_url = reverse_lazy('tmp_clients')

    def form_valid(self, form):
        return handle_form_valid(self, form)

class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = "frontend_templates/client_detail.html"
    context_object_name = "client"

    def get_queryset(self):
        return Client.objects.filter(company__user=self.request.user)

class InvoicesListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'frontend_templates/invoices.html'
    context_object_name = 'invoices'
    paginate_by = 10

    def get_queryset(self):
        invoices = list(Invoice.objects.filter(company__user=self.request.user))
        invoices.sort(key=lambda inv: (
            int(inv.number.split('/')[2]),
            int(inv.number.split('/')[1]),
            int(inv.number.split('/')[0])
        ), reverse=True)

        return invoices


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'frontend_templates/invoice_detail.html'
    context_object_name = 'invoice'

InvoiceItemFormSet = inlineformset_factory(
    Invoice, InvoiceItem,
    fields=['product', 'quantity', 'net_price', 'tax_rate'],
    extra=1, can_delete=True
)

class InvoiceCreateView(CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'frontend_templates/invoice_create.html'
    success_url = reverse_lazy('tmp_invoices')

    def get_active_company_id(self):
        """Helper method to extract active company ID from session."""
        logging.log(level=1, msg="Getting active company ID")
        return self.request.session.get('active_company_id')

    def check_active_company(self, form):
        """Validates active company and adds errors if necessary."""
        active_company_id = self.get_active_company_id()
        if not active_company_id:
            form.add_error(None, "Nie wybrano aktywnej firmy.")
            return None
        try:
            return Company.objects.get(id=active_company_id)
        except Company.DoesNotExist:
            form.add_error(None, "Aktywna firma nie istnieje.")
            return None

    def get_form_kwargs(self):
        """Adds the company to the form kwargs."""
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_active_company_id()
        return kwargs

    def get_context_data(self, **kwargs):
        """Extends context to add formset for InvoiceItem."""
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['item_formset'] = InvoiceItemFormSet(self.request.POST,
                                                        instance=self.object)
        else:
            context['item_formset'] = InvoiceItemFormSet(instance=self.object)
        return context


    def form_valid(self, form):
        """Validates the form and ensures active company existence."""
        company = self.check_active_company(form)
        if not company:
            logger.warning("Trying to save without active company.")
            form.add_error(None, 'Nie wybrano aktywnej firmy')
            return self.form_invalid(form)

        self.object = form.save(commit=False)
        self.object.company = company
        self.object.save()

        logger.info("Invoice saved with number: %s", self.object.number)

        item_formset = InvoiceItemFormSet(self.request.POST,
                                          instance=self.object)
        if item_formset.is_valid():
            item_formset.save()
            self.object.update_totals()

        else:
            return self.form_invalid(form)

        logger.info("Invoice saved successfully with number: %s",
                    self.object.number)
        return super().form_valid(form)


class ProductsListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "frontend_templates/products.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):
        company_id: int = self.request.session.get('active_company_id')
        if company_id:
            return Product.objects.filter(company_id=company_id, company__user=self.request.user)
        return Product.objects.none()


class ProductsDetailView(DetailView):
    model = Product
    template_name = "frontend_templates/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        return Product.objects.filter(company__user=self.request.user)

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'frontend_templates/product_create.html'
    success_url = reverse_lazy('tmp_products')

    def form_valid(self, form):
        return handle_form_valid(self, form)

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "frontend_templates/product_create.html"

    def get_success_url(self):
        return reverse("tmp_product_detail", kwargs={"pk": self.object.pk})

class ProductDeleteView(DeleteView):
    model = Product
    template_name = "frontend_templates/product_confirm_delete.html"
    success_url = reverse_lazy("tmp_products")

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
