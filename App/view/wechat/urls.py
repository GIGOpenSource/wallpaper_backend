#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：NoBad 
@File    ：urls.py
@Author  ：LYP
@Date    ：2025/10/30 13:26 
@description :
"""
from django.urls import path, include
from . import view
from rest_framework.routers import DefaultRouter

from .view import checkWechatUserDeletionStatus, getUnlimitedQRCode

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
    path("login", view.getWechatOpenId),
    path("getUserPhone", view.getUserPhone),
    path("updataUserInfo", view.updataUserInfo),
    path("getUserInfo", view.getUserInfo),
    path("getAcquireNewUsers",view.getAcquireNewUsers),
    path("apklogin",view.getApkWechatOpenId),
    path("wx_account_check_del",checkWechatUserDeletionStatus),
    path("wx_get_QRcode",getUnlimitedQRCode)
]
