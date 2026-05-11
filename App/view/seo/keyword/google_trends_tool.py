#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project ：wallpaper
@File    ：google_trends_tool.py
@Author  ：Liang
@Date    ：2026/5/11
@description : Google Trends关键词趋势分析工具
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class GoogleTrendsTool:
    """Google Trends关键词趋势分析工具
    
    使用pytrends库调用Google Trends数据
    注意：需要安装 pytrends: pip install pytrends
    """
    
    def __init__(self):
        self.trend_req = None
        self._initialize_pytrends()
    
    def _initialize_pytrends(self):
        """初始化pytrends连接"""
        try:
            from pytrends.request import TrendReq
            # 设置请求间隔，避免被限制
            self.trend_req = TrendReq(hl='en-US', tz=360)
        except ImportError:
            raise ImportError("请安装pytrends: pip install pytrends")
    
    def get_interest_over_time(
        self,
        keywords: List[str],
        geo: str = '',
        timeframe: str = 'today 12-m',
        gprop: str = ''
    ) -> Dict:
        """
        获取关键词随时间的兴趣趋势
        
        Args:
            keywords: 关键词列表，最多5个
            geo: 国家/地区代码，如'US', 'CN', ''表示全球
            timeframe: 时间范围
                - 'now 1-H' (过去1小时)
                - 'now 4-H' (过去4小时)
                - 'now 7-d' (过去7天)
                - 'today 1-m' (过去30天)
                - 'today 3-m' (过去90天)
                - 'today 12-m' (过去12个月)
                - 'today+5-y' (过去5年)
                - 'all' (从2004年开始)
                - 'YYYY-MM-DD YYYY-MM-DD' (自定义日期范围)
            gprop: 搜索类型
                - '' (网页搜索，默认)
                - 'images' (图片搜索)
                - 'news' (新闻搜索)
                - 'youtube' (YouTube搜索)
                - 'froogle' (Google购物)
        
        Returns:
            {
                'timeline_data': [
                    {'date': '2026-01-01', 'keyword1': 85, 'keyword2': 60},
                    ...
                ],
                'averages': {'keyword1': 75.5, 'keyword2': 55.2}
            }
        """
        try:
            # 构建payload
            self.trend_req.build_payload(
                kw_list=keywords[:5],  # 最多5个关键词
                geo=geo,
                timeframe=timeframe,
                gprop=gprop
            )
            
            # 获取兴趣随时间变化的数据
            interest_over_time_df = self.trend_req.interest_over_time()
            
            if interest_over_time_df.empty:
                return {
                    'timeline_data': [],
                    'averages': {},
                    'message': '未找到数据'
                }
            
            # 转换为字典格式
            timeline_data = []
            for date, row in interest_over_time_df.iterrows():
                data_point = {'date': date.strftime('%Y-%m-%d')}
                for keyword in keywords:
                    if keyword in row.index:
                        data_point[keyword] = int(row[keyword])
                timeline_data.append(data_point)
            
            # 计算平均值（排除isPartial列）
            averages = {}
            for keyword in keywords:
                if keyword in interest_over_time_df.columns:
                    averages[keyword] = round(
                        interest_over_time_df[keyword].mean(), 2
                    )
            
            return {
                'timeline_data': timeline_data,
                'averages': averages,
                'keywords': keywords,
                'geo': geo or 'Worldwide',
                'timeframe': timeframe,
                'gprop': gprop or 'web'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'timeline_data': [],
                'averages': {}
            }
    
    def get_related_queries(
        self,
        keyword: str,
        geo: str = '',
        timeframe: str = 'today 12-m',
        gprop: str = ''
    ) -> Dict:
        """
        获取相关查询（热门查询和上升查询）
        
        Args:
            keyword: 单个关键词
            geo: 国家/地区代码
            timeframe: 时间范围
            gprop: 搜索类型
        
        Returns:
            {
                'top': [
                    {'query': 'related keyword', 'value': 100},
                    ...
                ],
                'rising': [
                    {'query': 'rising keyword', 'value': '+350%'},
                    ...
                ]
            }
        """
        try:
            self.trend_req.build_payload(
                kw_list=[keyword],
                geo=geo,
                timeframe=timeframe,
                gprop=gprop
            )
            
            # 获取相关查询
            related_queries_dict = self.trend_req.related_queries()
            
            result = {
                'keyword': keyword,
                'geo': geo or 'Worldwide',
                'timeframe': timeframe,
                'gprop': gprop or 'web',
                'top': [],
                'rising': []
            }
            
            if keyword in related_queries_dict:
                # 热门查询（top queries）
                top_df = related_queries_dict[keyword]['top']
                if top_df is not None and not top_df.empty:
                    result['top'] = [
                        {
                            'query': row['query'],
                            'value': int(row['value'])
                        }
                        for _, row in top_df.head(20).iterrows()
                    ]
                
                # 上升查询（rising queries）
                rising_df = related_queries_dict[keyword]['rising']
                if rising_df is not None and not rising_df.empty:
                    result['rising'] = [
                        {
                            'query': row['query'],
                            'value': str(row['value'])  # 可能是 "Breakout" 或数字
                        }
                        for _, row in rising_df.head(20).iterrows()
                    ]
            
            return result
            
        except Exception as e:
            return {
                'error': str(e),
                'keyword': keyword,
                'top': [],
                'rising': []
            }
    
    def get_interest_by_region(
        self,
        keywords: List[str],
        geo: str = '',
        timeframe: str = 'today 12-m',
        gprop: str = ''
    ) -> List[Dict]:
        """
        获取按地区划分的兴趣度
        
        Args:
            keywords: 关键词列表
            geo: 国家/地区代码（如果指定，则返回该国家的地区数据）
            timeframe: 时间范围
            gprop: 搜索类型
        
        Returns:
            [
                {'region': 'California', 'keyword1': 100, 'keyword2': 80},
                ...
            ]
        """
        try:
            self.trend_req.build_payload(
                kw_list=keywords[:5],
                geo=geo,
                timeframe=timeframe,
                gprop=gprop
            )
            
            interest_by_region_df = self.trend_req.interest_by_region(
                resolution='REGION' if geo else 'COUNTRY'
            )
            
            if interest_by_region_df.empty:
                return []
            
            # 转换为字典格式
            result = []
            for region, row in interest_by_region_df.iterrows():
                data_point = {'region': region}
                for keyword in keywords:
                    if keyword in row.index:
                        data_point[keyword] = int(row[keyword])
                result.append(data_point)
            
            # 按第一个关键词的值排序
            if keywords and keywords[0] in result[0]:
                result.sort(key=lambda x: x.get(keywords[0], 0), reverse=True)
            
            return result[:50]  # 返回前50个地区
            
        except Exception as e:
            return []
    
    def compare_keywords(
        self,
        keywords: List[str],
        geo: str = '',
        timeframe: str = 'today 12-m'
    ) -> Dict:
        """
        比较多个关键词的趋势
        
        Args:
            keywords: 要比较的关键词列表（2-5个）
            geo: 国家/地区代码
            timeframe: 时间范围
        
        Returns:
            {
                'comparison_data': [...],
                'averages': {...},
                'winner': 'keyword with highest average'
            }
        """
        if len(keywords) < 2 or len(keywords) > 5:
            return {
                'error': '需要提供2-5个关键词进行比较'
            }
        
        trend_data = self.get_interest_over_time(
            keywords=keywords,
            geo=geo,
            timeframe=timeframe
        )
        
        if 'error' in trend_data:
            return trend_data
        
        # 找出平均兴趣度最高的关键词
        averages = trend_data.get('averages', {})
        winner = max(averages, key=averages.get) if averages else None
        
        return {
            **trend_data,
            'winner': winner,
            'comparison_summary': {
                f'{kw}': avg for kw, avg in averages.items()
            }
        }
    
    def get_trending_searches(
        self,
        geo: str = 'US',
        category: str = 'all'
    ) -> List[Dict]:
        """
        获取当前热门搜索（每日趋势）
        
        Args:
            geo: 国家/地区代码
            category: 分类（all, business, entertainment, etc.）
        
        Returns:
            [
                {
                    'title': 'trending topic',
                    'traffic': '500K+',
                    'articles': [...]
                },
                ...
            ]
        """
        try:
            from pytrends.exceptions import ResponseError
            
            self.trend_req.build_payload(kw_list=['test'])
            
            # 获取每日趋势
            trending_searches_df = self.trend_req.trending_searches(pn=geo)
            
            if trending_searches_df.empty:
                return []
            
            result = []
            for _, row in trending_searches_df.head(20).iterrows():
                result.append({
                    'title': row[0] if len(row) > 0 else '',
                    'traffic': row[1] if len(row) > 1 else 'N/A'
                })
            
            return result
            
        except Exception as e:
            return []
