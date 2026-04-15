#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/15
@description : 消息通知路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.notifications.view import NotificationViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
