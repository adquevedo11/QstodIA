from django.shortcuts import render
from django.views.decorators.cache import never_cache


@never_cache
def license_expired(request):
    return render(request, 'dojo/license_expired.html', status=403)
