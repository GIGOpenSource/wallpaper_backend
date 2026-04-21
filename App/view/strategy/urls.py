# -*- coding: UTF-8 -*-
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.strategy.view import RecommendStrategyViewSet

router = DefaultRouter()
router.register(r"strategies", RecommendStrategyViewSet, basename="strategy")

urlpatterns = [
    path("", include(router.urls)),
]
