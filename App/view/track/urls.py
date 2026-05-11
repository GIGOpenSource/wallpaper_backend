#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
埋点功能 URL 配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from App.view.track.view import TrackViewSet

router = DefaultRouter()
router.register(r'', TrackViewSet, basename='track')

urlpatterns = [
    path('', include(router.urls)),
]
