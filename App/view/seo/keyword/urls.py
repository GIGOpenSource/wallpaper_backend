#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/5/11
@description : 关键词研究URL路由
"""
from rest_framework.routers import SimpleRouter
from .view import KeywordResearchViewSet

router = SimpleRouter()
router.register(r'', KeywordResearchViewSet, basename='keyword')

urlpatterns = router.urls
