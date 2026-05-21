from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.seo.check.view import WallpaperCheckViewSet

router = DefaultRouter()
router.register(r'', WallpaperCheckViewSet, basename='wallpaper-check')

urlpatterns = [
    path('', include(router.urls)),
]
