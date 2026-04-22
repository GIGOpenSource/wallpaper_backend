import logging
from django.http import HttpResponseForbidden
from tool.token_tools import _redis  # 确保 RedisTool 导入路径正确

logger = logging.getLogger('')

class IPLogMiddleware:
    """IP访问日志 + 1分钟计数 + 自动封禁"""
    def __init__(self, get_response):
        self.get_response = get_response
        self.redis_prefix = "ip_access:"
        self.ban_prefix = "ip_ban:"
        self.ban_seconds = 3600  # 封禁1小时

        # 固定统计窗口为1分钟（60秒），仅阈值不同
        self.normal_limit = {'count': 999999999, 'seconds': 60}   # 正常路径：60次/分钟
        self.malicious_limit = {'count': 999, 'seconds': 60} # 恶意路径：5次/分钟

        # 恶意路径列表
        self.malicious_paths = [
            '/evox/about', '/HNAP1', '/favicon.ico', '/robots.txt',
            '/+CSCOL+/Java.jar', '/admin', '/phpmyadmin', '/mysql',
            '/wp-admin', '/blog', '/test', '/login', '/user'
        ]

        # 白名单路径（不进行访问限制）
        self.whitelist_paths = [
            '/api/trialcase/check_joined/'
        ]
    def __call__(self, request):
        request_path = request.path_info.lower()
        if self._is_whitelist_path(request_path):
            # 白名单路径直接放行，不进行任何限制检查
            response = self.get_response(request)
            return response
        # 1. 提取真实IP
        real_ip = self._get_real_ip(request)
        if real_ip == "未知IP":
            logger.warning("无法获取IP，拒绝访问")
            return HttpResponseForbidden("非法访问：无法识别IP")

        # 2. 检查是否已封禁
        ban_key = f"{self.ban_prefix}{real_ip}"
        if _redis.getKey(ban_key):
            logger.warning(f"封禁IP访问：{real_ip} | 路径: {request.path_info}")
            return HttpResponseForbidden(f"IP {real_ip} 已被封禁1小时")

        # 3. 判断路径类型
        is_malicious = self._is_malicious_path(request_path)
        limit_rule = self.malicious_limit if is_malicious else self.normal_limit
        access_key = f"{self.redis_prefix}{'malicious' if is_malicious else 'normal'}:{real_ip}"

        # 4. 调用 setIncrKey，强制传60秒过期时间（核心！）
        current_count = _redis.setIncrKey(access_key, ex=limit_rule['seconds'])

        # 5. 触发封禁
        if current_count > limit_rule['count']:
            _redis.setKey(ban_key, "banned", ex=self.ban_seconds)
            logger.warning(
                f"IP封禁：{real_ip} | 类型: {'恶意路径' if is_malicious else '正常路径'} | "
                f"次数: {current_count} | 阈值: {limit_rule['count']}"
            )
            return HttpResponseForbidden(f"IP {real_ip} 访问过于频繁，已被封禁1小时")

        # 6. 输出日志
        logger.info(
            f"访问日志 | IP: {real_ip} | 次数: {current_count} | 类型: {'恶意路径' if is_malicious else '正常路径'} | "
            f"方法: {request.method} | 路径: {request_path} | User-Agent: {request.META.get('HTTP_USER_AGENT', '无')[:200]}"
        )

        response = self.get_response(request)
        return response

    def _get_real_ip(self, request):
        """提取真实IP（兼容代理）"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').strip()
        if x_forwarded_for:
            ip_list = [ip.strip() for ip in x_forwarded_for.split(',') if ip.strip()]
            return ip_list[0] if ip_list else '未知IP'
        real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
        return real_ip if real_ip else request.META.get('REMOTE_ADDR', '未知IP').strip()

    def _is_malicious_path(self, path):
        """判断恶意路径（精确+模糊匹配）"""
        if path in self.malicious_paths:
            return True
        for malicious_path in self.malicious_paths:
            if path.startswith(malicious_path):
                return True
        return False

    def _is_whitelist_path(self, path):
        """判断是否为白名单路径"""
        return path in self.whitelist_paths