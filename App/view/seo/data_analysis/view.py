# -*- coding: UTF-8 -*-
"""
SEO数据分析仪表视图
智能缓存机制：每10次请求调用一次GSC接口，减少API调用频率
"""
from datetime import datetime, timedelta
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import serializers
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from django.utils import timezone
from models.models import SEODashboardStats
from tool.base_views import BaseViewSet
from tool.permissions import IsAdmin
from tool.utils import ApiResponse, CustomPagination


@extend_schema(tags=["SEO数据分析"])
class SEODashboardStatsViewSet(ViewSet):
    """
    SEO数据分析仪表 ViewSet
    智能缓存机制：每10次请求调用一次GSC接口，其他时候复用数据库数据
    
    工作流程：
    1. 接收 site_url 和 start_timestamp/end_timestamp 参数
    2. 计算统计日期范围
    3. 检查数据库中是否存在该日期的记录
    4. 如果存在且 request_count < 10，直接返回数据库数据并增加计数
    5. 如果不存在或 request_count >= 10，调用GSC接口获取新数据，重置计数为1
    6. 返回数据时同时包含本周增量字段
    """
    permission_classes = [IsAdmin]
    
    GSC_CALL_THRESHOLD = 1  # GSC调用阈值：每10次请求调用一次

    @extend_schema(
        summary="SEO数据分析（智能缓存）",
        description="""获取SEO数据分析，包含：
        - Google收录趋势
        - 关键词排名
        - 着陆页分析
        - 地区国家数据
        - 本周增量对比
        
        智能缓存机制：
        - 同一网站+日期的数据，每10次请求才调用一次GSC接口
        - 其他请求直接复用数据库中的旧数据
        - 自动计算并返回本周增量字段
        """,
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL，如: https://www.markwallpapers.com/"),
            OpenApiParameter(name="start_timestamp", type=int, required=True, description="开始时间戳（秒），如: 1712361600"),
            OpenApiParameter(name="end_timestamp", type=int, required=True, description="结束时间戳（秒），如: 1714953600"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='data-analysis')
    def data_analysis(self, request):
        """
        SEO 数据分析接口（带智能缓存）
        """
        from seo.seo_tools import gsc_tool
        
        # 1. 验证参数
        site_url = request.query_params.get('site_url')
        start_timestamp = request.query_params.get('start_timestamp')
        end_timestamp = request.query_params.get('end_timestamp')
        
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
        if not start_timestamp:
            return ApiResponse(code=400, message="请提供 start_timestamp 参数")
        if not end_timestamp:
            return ApiResponse(code=400, message="请提供 end_timestamp 参数")
        
        # 2. 转换时间戳为日期
        try:
            start_timestamp = int(start_timestamp)
            end_timestamp = int(end_timestamp)
            start_date = datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%d')
            end_date = datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d')
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        except (ValueError, TypeError, OSError) as e:
            return ApiResponse(code=400, message=f"时间戳格式错误: {str(e)}")
        
        # 确保 URL 格式正确
        if not site_url.endswith('/'):
            site_url += '/'
        
        # 3. 检查数据库中的记录
        today = datetime.now().date()
        db_record = SEODashboardStats.objects.filter(
            site_url=site_url,
            stat_date=today
        ).first()
        
        should_call_gsc = False
        
        if not db_record:
            # 没有记录，需要调用GSC
            should_call_gsc = True
        elif db_record.request_count >= self.GSC_CALL_THRESHOLD:
            # 达到阈值，需要调用GSC并重置计数
            should_call_gsc = True
        else:
            # 使用缓存数据
            should_call_gsc = False
        
        # 4. 如果需要调用GSC，获取最新数据
        if should_call_gsc:
            try:
                # 调用GSC接口获取数据
                inclusion_trend = gsc_tool.get_inclusion_trend(site_url, start_date, end_date)
                keyword_rankings = gsc_tool.get_keyword_rankings(site_url, start_date, end_date, limit=50)
                
                # 获取着陆页分析
                landing_pages = gsc_tool.get_top_pages(site_url, days=30, limit=20)
                landing_page_analysis = []
                for page in landing_pages:
                    ctr = page['ctr']
                    position = page['position']
                    estimated_bounce_rate = max(20, min(80, 50 + (position - 5) * 5))
                    estimated_avg_time = max(10, min(300, ctr * 10 + 30))
                    estimated_conversion_rate = max(0.1, min(5, ctr * 0.1))
                    
                    landing_page_analysis.append({
                        'page': page['page'],
                        'visits': page['clicks'],
                        'bounce_rate': round(estimated_bounce_rate, 2),
                        'avg_time_on_page': round(estimated_avg_time, 2),
                        'conversion_rate': round(estimated_conversion_rate, 2)
                    })
                
                # 获取地区国家数据
                days = (end_dt - start_dt).days + 1
                country_data = gsc_tool.get_country_data(site_url, days=days, limit=20)
                country_data_simplified = [
                    {
                        'country': item['country'],
                        'clicks': item['clicks'],
                        'impressions': item['impressions'],
                        'ctr': item['ctr']
                    }
                    for item in country_data
                ]
                
                # 从GSC数据中提取核心指标（简化估算）
                total_clicks = sum(item['clicks'] for item in inclusion_trend) if inclusion_trend else 0
                total_impressions = sum(item['impressions'] for item in inclusion_trend) if inclusion_trend else 0
                avg_position = sum(item['position'] for item in inclusion_trend) / len(inclusion_trend) if inclusion_trend else 0
                
                # 创建或更新数据库记录
                if db_record:
                    # 更新现有记录，重置计数为1
                    db_record.total_indexed = total_impressions
                    db_record.seo_traffic = total_clicks
                    db_record.avg_ranking = round(avg_position, 2)
                    db_record.request_count = 1
                    db_record.last_gsc_update = timezone.now()
                    db_record.save()
                else:
                    # 创建新记录
                    db_record = SEODashboardStats.objects.create(
                        site_url=site_url,
                        stat_date=today,
                        total_indexed=total_impressions,
                        seo_traffic=total_clicks,
                        avg_ranking=round(avg_position, 2),
                        backlink_count=0,  # 外链数量需要从其他API获取，这里默认为0
                        request_count=1,
                        last_gsc_update=timezone.now()
                    )
                
                cache_status = "fresh"
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                return ApiResponse(code=500, message=f"GSC接口调用失败: {str(e)}")
        else:
            # 使用缓存数据，增加计数
            db_record.request_count += 1
            db_record.save()
            
            # 从数据库构建返回数据（简化版）
            inclusion_trend = []
            keyword_rankings = []
            landing_page_analysis = []
            country_data_simplified = []
            
            cache_status = "cached"
        
        # 5. 计算本周增量
        week_ago_date = today - timedelta(days=7)
        week_ago_record = SEODashboardStats.objects.filter(
            site_url=site_url,
            stat_date=week_ago_date
        ).first()
        
        # 计算增量
        total_indexed_increment = 0
        seo_traffic_increment = 0
        avg_ranking_increment = 0.0
        backlink_count_increment = 0
        
        if db_record and week_ago_record:
            total_indexed_increment = db_record.total_indexed - week_ago_record.total_indexed
            seo_traffic_increment = db_record.seo_traffic - week_ago_record.seo_traffic
            avg_ranking_increment = round(week_ago_record.avg_ranking - db_record.avg_ranking, 2)
            backlink_count_increment = db_record.backlink_count - week_ago_record.backlink_count
        
        # 6. 构建响应数据
        response_data = {
            'inclusion_trend': inclusion_trend,
            'keyword_rankings': keyword_rankings,
            'landing_page_analysis': landing_page_analysis,
            'country_data': country_data_simplified,
            'dashboard_stats': {
                'stat_date': str(db_record.stat_date) if db_record else None,
                'total_indexed': db_record.total_indexed if db_record else 0,
                'seo_traffic': db_record.seo_traffic if db_record else 0,
                'avg_ranking': db_record.avg_ranking if db_record else 0.0,
                'backlink_count': db_record.backlink_count if db_record else 0,
                'total_indexed_weekly_increment': total_indexed_increment,
                'seo_traffic_weekly_increment': seo_traffic_increment,
                'avg_ranking_weekly_increment': avg_ranking_increment,
                'backlink_count_weekly_increment': backlink_count_increment,
            },
            'cache_info': {
                'status': cache_status,
                'request_count': db_record.request_count if db_record else 0,
                'next_gsc_call_at': self.GSC_CALL_THRESHOLD - (db_record.request_count if db_record else 0),
                'last_gsc_update': str(db_record.last_gsc_update) if db_record and db_record.last_gsc_update else None,
            }
        }
        
        message = "数据分析成功"
        if cache_status == "cached":
            message += f"（使用缓存数据，第{db_record.request_count}次请求）"
        else:
            message += "（已更新GSC数据）"
        
        return ApiResponse(data=response_data, message=message)

    @extend_schema(
        summary="SEO数据面板（8个核心指标）",
        description="""获取SEO数据面板的8个核心指标：
        - total_indexed: 总收录量
        - seo_traffic: SEO流量
        - avg_ranking: 平均排名
        - backlink_count: 外链数量
        - total_indexed_weekly_increment: 总收录量本周增量
        - seo_traffic_weekly_increment: SEO流量本周增量
        - avg_ranking_weekly_increment: 平均排名本周增量
        - backlink_count_weekly_increment: 外链数量本周增量
        
        数据来源：
        - 从数据库 SEODashboardStats 表中读取
        - 如果没有数据，返回全0
        """,
        parameters=[
            OpenApiParameter(name="site_url", type=str, required=True, description="网站URL，如: https://www.markwallpapers.com/"),
        ],
    )
    @action(detail=False, methods=['get'], url_path='dashboard')
    def dashboard(self, request):
        """
        SEO数据面板接口
        返回8个核心指标值
        """
        # 1. 验证参数
        site_url = request.query_params.get('site_url')
        
        if not site_url:
            return ApiResponse(code=400, message="请提供 site_url 参数")
        
        # 确保 URL 格式正确
        if not site_url.endswith('/'):
            site_url += '/'
        
        # 2. 获取今天的记录
        today = datetime.now().date()
        db_record = SEODashboardStats.objects.filter(
            site_url=site_url,
            stat_date=today
        ).first()
        
        # 3. 获取7天前的记录用于计算增量
        week_ago_date = today - timedelta(days=7)
        week_ago_record = SEODashboardStats.objects.filter(
            site_url=site_url,
            stat_date=week_ago_date
        ).first()
        
        # 4. 计算增量
        total_indexed_increment = 0
        seo_traffic_increment = 0
        avg_ranking_increment = 0.0
        backlink_count_increment = 0
        
        if db_record and week_ago_record:
            total_indexed_increment = db_record.total_indexed - week_ago_record.total_indexed
            seo_traffic_increment = db_record.seo_traffic - week_ago_record.seo_traffic
            avg_ranking_increment = round(week_ago_record.avg_ranking - db_record.avg_ranking, 2)
            backlink_count_increment = db_record.backlink_count - week_ago_record.backlink_count
        
        # 5. 构建返回数据（8个核心值）
        response_data = {
            'total_indexed': db_record.total_indexed if db_record else 0,
            'seo_traffic': db_record.seo_traffic if db_record else 0,
            'avg_ranking': db_record.avg_ranking if db_record else 0.0,
            'backlink_count': db_record.backlink_count if db_record else 0,
            'total_indexed_weekly_increment': total_indexed_increment,
            'seo_traffic_weekly_increment': seo_traffic_increment,
            'avg_ranking_weekly_increment': avg_ranking_increment,
            'backlink_count_weekly_increment': backlink_count_increment,
        }
        
        return ApiResponse(data=response_data, message="面板数据获取成功")
