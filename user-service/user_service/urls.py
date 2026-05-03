from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('auth_app.urls')),
    path('', include('customer_app.urls')),
    path('', include('manager_app.urls')),
    path('', include('staff_app.urls')),
]
