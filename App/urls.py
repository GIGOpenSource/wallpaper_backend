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
from App.view.strategy import urls as strategy
from App.view.operation_log import urls as operation_log
from App.view.seo import urls as seo
from App.view.track import urls as track

urlpatterns = [
    path('', include(user)),
    path('client/', include(customer)),
    path('wallpapers/', include(wallpapers)),
    path('notifications/', include(notifications)),
    path('site/', include(site)),
    path('dashboard/', include(dashboard)),
    path('strategy/', include(strategy)),
    path('operation_log/', include(operation_log)),
    path('seo/', include(seo)),
    path('track/', include(track)),

]
