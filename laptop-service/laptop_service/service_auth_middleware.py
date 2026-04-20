import os
from django.http import JsonResponse


class ServiceAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.shared_token = os.getenv('SERVICE_SHARED_TOKEN', '')

    def __call__(self, request):
        if request.path.startswith('/health/') or request.path.startswith('/admin/'):
            return self.get_response(request)
        if self.shared_token and request.headers.get('X-Service-Token', '') != self.shared_token:
            return JsonResponse({'error': 'Unauthorized service request.'}, status=401)
        return self.get_response(request)
