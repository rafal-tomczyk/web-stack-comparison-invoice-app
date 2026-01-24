from django.contrib import messages
from django.shortcuts import redirect
from django.urls import resolve, reverse, NoReverseMatch

class CompanyRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            'tmp_login_view',
            'tmp_register',
            'tmp_choose_company',
            'tmp_company_add',
            'tmp_index',
            'admin:index',
            'tmp_logout',
        ]

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                current_url_name = resolve(request.path_info).url_name
            except:
                current_url_name = None

            is_exempt = False
            if current_url_name:
                is_exempt = current_url_name in self.exempt_urls

            if not is_exempt and not request.session.get('active_company_id'):
                messages.info(request, "Wybierz firmę, aby kontynuować.")

                try:
                    return redirect(reverse('tmp_choose_company'))
                except NoReverseMatch:
                    return redirect('tmp_home')


        response = self.get_response(request)
        return response
