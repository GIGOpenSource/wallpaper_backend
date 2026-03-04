#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：NoBad 
@File    ：urls.py
@Author  ：Liang
@Date    ：2026/3/3 16:58
@description :
"""
from django.urls import path, include

from App.view.user import urls as user
from App.view.wechat import urls as wechat

urlpatterns = [
    path('', include(user)),
    path('wechat/', include(wechat)),
]
