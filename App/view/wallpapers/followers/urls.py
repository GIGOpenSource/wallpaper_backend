#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/15
@description : 粉丝与关注功能路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.wallpapers.followers.view import UserFollowViewSet

router = DefaultRouter()
router.register(r'', UserFollowViewSet, basename='user-follow')

urlpatterns = [
    path('', include(router.urls)),
]
