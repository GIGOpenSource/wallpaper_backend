#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/15
@description : 评论功能路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.wallpapers.comments.view import WallpaperCommentViewSet

router = DefaultRouter()
router.register(r'', WallpaperCommentViewSet, basename='wallpaper-comment')

urlpatterns = [
    path('', include(router.urls)),
]
