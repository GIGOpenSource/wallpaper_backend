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
from App.view.notifications import urls as notifications
from App.view.site import urls as site
from App.view.dashboard import urls as dashboard

urlpatterns = [
    path('', include(user)),
    path('client/', include(customer)),
    path('wallpapers/', include(wallpapers)),
    path('notifications/', include(notifications)),
    path('site/', include(site)),
    path('dashboard/', include(dashboard)),

]
