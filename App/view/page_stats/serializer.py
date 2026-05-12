from rest_framework import serializers
from models.models import PageStats

class PageStatsSerializer(serializers.ModelSerializer):
    """页面统计序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PageStats
        fields = [
            'id', 'page_name', 'page_path', 'page_type', 'device_type',
            'visit_count', 'avg_stay_time', 'bounce_rate', 'seo_score',
            'status', 'status_display', 'last_updated', 'created_at'
        ]
        read_only_fields = fields
