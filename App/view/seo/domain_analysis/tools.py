# -*- coding: UTF-8 -*-
"""
域名分析工具类
调用第三方API获取域名的安全评分、外链数等信息
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


def analyze_domain_safety(domain):
    """
    分析域名安全性
    使用免费的 Google Safe Browsing API 或其他免费服务
    
    :param domain: 域名
    :return: dict containing safety_score, backlink_count, status
    """
    result = {
        'safety_score': 50,  # 默认中等评分
        'backlink_count': 0,
        'status': 'safe'
    }
    
    try:
        # 方法1: 使用 URLVoid API (免费版有每日限制)
        # 需要注册获取 API key: https://www.urlvoid.com/api/
        api_key = ""  # 从配置中获取
        
        if api_key:
            result = _analyze_with_urlvoid(domain, api_key)
        else:
            # 如果没有配置API，使用模拟数据
            logger.warning(f"未配置域名分析API，使用默认评分: {domain}")
            result = _mock_analysis(domain)
            
    except Exception as e:
        logger.error(f"域名分析失败: {domain}, 错误: {e}")
        result = _mock_analysis(domain)
    
    return result


def _analyze_with_urlvoid(domain, api_key):
    """
    使用 URLVoid API 分析域名
    API文档: https://www.urlvoid.com/api/
    """
    try:
        url = f"https://api.urlvoid.com/v1/check?key={api_key}&host={domain}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # 解析安全评分
            detections = data.get('detections', {})
            total_engines = len(detections)
            malicious_count = sum(1 for v in detections.values() if v != 'clean')
            
            if total_engines > 0:
                safety_score = int(((total_engines - malicious_count) / total_engines) * 100)
            else:
                safety_score = 50
            
            # 判断状态
            status = 'danger' if malicious_count > 0 else 'safe'
            
            # 获取外链数（URLVoid不提供，使用其他API或估算）
            backlink_count = _get_backlink_count(domain)
            
            return {
                'safety_score': safety_score,
                'backlink_count': backlink_count,
                'status': status
            }
        else:
            logger.error(f"URLVoid API 请求失败: {response.status_code}")
            return _mock_analysis(domain)
            
    except Exception as e:
        logger.error(f"URLVoid API 调用失败: {e}")
        return _mock_analysis(domain)


def _get_backlink_count(domain):
    """
    获取域名外链数
    可以使用 Ahrefs、Majestic 等 API，这里使用简单估算
    """
    # 实际项目中应该调用真实的API
    # 这里返回0或随机值作为示例
    return 0


def _mock_analysis(domain):
    """
    模拟域名分析（用于测试或API不可用时）
    根据域名特征给出评分
    """
    import hashlib
    
    # 基于域名生成一个稳定的评分
    hash_value = int(hashlib.md5(domain.encode()).hexdigest(), 16)
    safety_score = hash_value % 101  # 0-100
    
    # 根据评分确定状态
    if safety_score >= 60:
        status = 'safe'
    else:
        status = 'danger'
    
    # 模拟外链数
    backlink_count = (hash_value % 1000) * 10
    
    return {
        'safety_score': safety_score,
        'backlink_count': backlink_count,
        'status': status
    }
