# -*- coding: UTF-8 -*-
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.wallpapers.tags.view import WallpaperTagViewSet, NavigationTagViewSet

router = DefaultRouter()
router.register(r'', WallpaperTagViewSet, basename='wallpaper-tag')
# router.register(r'navigation_tag', NavigationTagViewSet, basename='navigation_tag')

urlpatterns = [
    path('', include(router.urls)),
]
