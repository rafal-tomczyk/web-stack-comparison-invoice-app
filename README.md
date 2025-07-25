# Web Stack Comparison – Invoicing Application

This repository contains a comparison of three approaches to building a simple invoicing web application. The project was created as part of a master's thesis analyzing performance, developer experience, and user satisfaction across different technology stacks.


---
## Compared Stacks

1. **Django (SSR)**  
   Classic server-side rendering approach using Django templates.

2. **Django + HTMX (Progressive Enhancement)**  
   A hybrid method that enhances server-side rendering with partial HTML updates over AJAX using HTMX.

3. **Django + React (CSR hybrid)**  
   A client-heavy solution using Django for the backend API and React for the frontend.

---
## Structure

my-invoices-project/        ← root repozytorium (tam gdzie jest .git)<br>
├── README.md               ← opis projektu <br>
├── requirements.txt        ← zależności Pythona<br>
├── Dockerfile              ← budowanie obrazu aplikacji Django<br>
├── docker-compose.yml      ← uruchomienie serwisów (Django + Postgres)<br>
├── manage.py               ← punkt wejścia do Django<br>
├── myproject/              ← konfiguracja projektu Django (settings, urls itd.)<br>
│   ├── __init__.py<br>
│   ├── settings.py<br>
│   ├── urls.py<br>
│   ├── wsgi.py<br>
│   └── asgi.py<br>
├── invoices_common/        ← wspólne modele i logika biznesowa<br>
│   ├── __init__.py<br>
│   └── ...<br>
├── invoices_django/        ← appka Django (template rendering)<br>
│   ├── __init__.py<br>
│   └── ...<br>
├── invoices_htmx/          ← appka Django + HTMX<br>
│   ├── __init__.py<br>
│   └── ...<br>
├── invoices_react/         ← appka Django + React frontend<br>
│   ├── __init__.py<br>
│   └── ...<br>
└── frontend_react/         ← opcjonalnie, surowy kod Reacta (jeśli nie budujesz go w invoices_react/static)<br>
    ├── package.json<br>
    └── src/<br>


---
# About the Thesis

The goal of this project is to determine which stack offers the best trade-off between development time, performance, maintainability, and user experience for small-scale business applications like invoicing tools.

Results were evaluated using:

Development time tracking \
Google Lighthouse performance audits \
End-user testing and surveys \
Codebase maintainability assessment

---
## Python and Django Versions

This project was developed and tested using the following environments:

| Framework     | Version           |
|---------------|-------------------|
| Django        | 5.2 (LTS)         |
| Python        | 3.12 or 3.13      |

### Requirements

- **Django 5.2** is a Long-Term Support (LTS) release that ensures stability and modern features.
- **Python 3.12** provides full compatibility with Django 5.2 and offers strong performance.
- **Python 3.13** is also supported by Django 5.2 but may require a newer environment and may include experimental features (e.g., JIT compiler).

**Recommendation**: Use **Python 3.12** for maximum stability. Use **Python 3.13** if you want to explore the latest language features.

---
# License

This project is part of an academic thesis. Feel free to use it for educational purposes.
