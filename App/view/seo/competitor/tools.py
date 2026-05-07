# -*- coding: UTF-8 -*-
"""
竞争对手工具类
调用第三方API获取竞争对手的SEO数据
"""
import requests
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


def extract_domain(url):
    """
    从URL中提取域名
    :param url: 完整URL
    :return: 域名
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # 去除 www. 前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain.lower()
    except Exception as e:
        logger.error(f"提取域名失败: {url}, 错误: {e}")
        return None


def fetch_competitor_data(domain):
    """
    获取竞争对手的SEO数据
    可以对接 GSC、Ahrefs、SEMrush 等第三方API
    
    :param domain: 域名
    :return: dict containing domain_authority, monthly_traffic, keyword_count, backlink_count, growth_trend
    """
    result = {
        'domain_authority': 0,
        'monthly_traffic': 0,
        'keyword_count': 0,
        'backlink_count': 0,
        'growth_trend': 'stable'
    }
    
    try:
        # 这里可以集成真实的第三方API
        # 例如：Ahrefs API, SEMrush API, Moz API 等
        
        # 示例：使用 Moz API 获取域名权重
        # result['domain_authority'] = get_domain_authority_from_moz(domain)
        
        # 示例：使用 SimilarWeb API 获取流量数据
        # result['monthly_traffic'] = get_traffic_from_similarweb(domain)
        
        # 示例：使用 Ahrefs API 获取关键词和外链数据
        # result['keyword_count'] = get_keywords_from_ahrefs(domain)
        # result['backlink_count'] = get_backlinks_from_ahrefs(domain)
        
        # 目前使用模拟数据
        logger.warning(f"未配置第三方API，使用默认数据: {domain}")
        result = _mock_competitor_data(domain)
            
    except Exception as e:
        logger.error(f"获取竞争对手数据失败: {domain}, 错误: {e}")
        result = _mock_competitor_data(domain)
    
    return result


def _mock_competitor_data(domain):
    """
    模拟竞争对手数据（用于测试或API不可用时）
    根据域名生成一些合理的模拟数据
    """
    import hashlib
    
    # 基于域名生成稳定的模拟数据
    hash_value = int(hashlib.md5(domain.encode()).hexdigest(), 16)
    
    # 模拟域名权重 (0-100)
    domain_authority = hash_value % 101
    
    # 模拟月流量 (1000-1000000)
    monthly_traffic = 1000 + (hash_value % 999000)
    
    # 模拟关键词数 (10-10000)
    keyword_count = 10 + (hash_value % 9990)
    
    # 模拟外链数 (100-50000)
    backlink_count = 100 + (hash_value % 49900)
    
    # 模拟增长趋势
    trend_value = hash_value % 3
    if trend_value == 0:
        growth_trend = 'up'
    elif trend_value == 1:
        growth_trend = 'stable'
    else:
        growth_trend = 'down'
    
    return {
        'domain_authority': domain_authority,
        'monthly_traffic': monthly_traffic,
        'keyword_count': keyword_count,
        'backlink_count': backlink_count,
        'growth_trend': growth_trend
    }
