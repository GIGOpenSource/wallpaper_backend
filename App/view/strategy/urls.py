# -*- coding: UTF-8 -*-
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.strategy.view import RecommendStrategyViewSet, StrategyContentViewSet

router = DefaultRouter()
router.register(r"strategies", RecommendStrategyViewSet, basename="strategy")
router.register(r"state_contents", StrategyContentViewSet, basename="state_content")


urlpatterns = [
    path("", include(router.urls)),
]
