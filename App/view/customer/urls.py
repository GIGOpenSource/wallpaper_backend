# -*- coding: UTF-8 -*-
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.customer.view import CustomerUserViewSet
from tool.uploader_data import UploadResourceView
router = DefaultRouter()
router.register(r"users", CustomerUserViewSet, basename="customer_user")

urlpatterns = [
    path("", include(router.urls)),
    path("upload-image/", UploadResourceView.as_view(), name="upload-common-image"),

]
