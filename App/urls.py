#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/4/9 16:32
@description :
"""
from django.urls import path, include

from App.view.user import urls as user
from App.view.customer import urls as customer
from App.view.wallpapers import urls as wallpapers

urlpatterns = [
    path('', include(user)),
    path('client/', include(customer)),
    path('wallpapers/', include(wallpapers)),
]
