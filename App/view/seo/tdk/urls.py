#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/28
@description : 页面TDK路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.seo.tdk.view import PageTDKViewSet

router = DefaultRouter()
router.register(r'', PageTDKViewSet, basename='page-tdk')

urlpatterns = [
    path('', include(router.urls)),
]
