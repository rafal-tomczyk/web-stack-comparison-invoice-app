from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from ..forms.templates_forms.forms import RegisterForm

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

def home(request):
    return render(request, "frontend_templates/home.html")
