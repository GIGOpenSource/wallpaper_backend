#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/5/6
@description : 页面速度管理路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.seo.page_speed.view import PageSpeedViewSet

router = DefaultRouter()
router.register(r'', PageSpeedViewSet, basename='page_speed')

urlpatterns = [
    path('', include(router.urls)),
]
