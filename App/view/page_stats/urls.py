from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .view import PageStatsViewSet

router = DefaultRouter()
router.register(r'', PageStatsViewSet, basename='page_stats')

urlpatterns = router.urls
