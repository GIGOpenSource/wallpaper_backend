#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/5/7
@description : SEO日常巡查
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.seo.inspection.view import SEOInspectionViewSet

router = DefaultRouter()
router.register(r'inspection', SEOInspectionViewSet, basename='seo_inspection')

urlpatterns = [
    path('', include(router.urls)),
]
