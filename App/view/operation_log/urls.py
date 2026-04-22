
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from App.view.operation_log.view import OperationLogViewSet
router = DefaultRouter()

router.register(r'operation_log', OperationLogViewSet, basename='operation_log')

urlpatterns = [
    path('', include(router.urls)),
]