"""
URL configuration for catalog_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('catalog_app.urls')),
    path('', include('book_app.urls')),
    path('beauty/', include('beauty_app.urls')),
    path('electronics/', include('electronics_app.urls')),
    path('fashion/', include('fashion_app.urls')),
    path('grocery/', include('grocery_app.urls')),
    path('household/', include('household_app.urls')),
    path('laptop/', include('laptop_app.urls')),
    path('mobile/', include('mobile_app.urls')),
    path('sports/', include('sports_app.urls')),
]