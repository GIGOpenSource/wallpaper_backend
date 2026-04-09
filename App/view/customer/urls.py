# -*- coding: UTF-8 -*-
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.customer.view import CustomerUserViewSet

router = DefaultRouter()
router.register(r"users", CustomerUserViewSet, basename="customer_user")

urlpatterns = [
    path("", include(router.urls)),
]
