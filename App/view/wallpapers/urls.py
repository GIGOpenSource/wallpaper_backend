#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：crushcheck
@File    ：urls.py
@Author  ：LHB
@Date    ：2026/01/26 15:10
@description :
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.wallpapers.view import WallpapersViewSet, NavigationTagViewSet

router = DefaultRouter()
router.register(r'wallpaper', WallpapersViewSet, basename='wallpaper')
router.register(r'navigation_tag', NavigationTagViewSet, basename='navigation_tag')
urlpatterns = [
    path('', include(router.urls)),

]
