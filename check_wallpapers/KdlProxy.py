# proxy_tunnel.py
import requests
import warnings

# 屏蔽SSL警告
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

class KdlTunnelProxy:
    # 快代理隧道配置
    PROXY_USER = "f2855151637"
    PROXY_PWD = "z1ag28gi"
    PROXY_HOST_LIST = [
        "v353.kdlfps.com",
        "us.v353.kdlfps.com",
        "as.v353.kdlfps.com"
    ]
    PROXY_PORT = "18866"
    TIMEOUT = 20
    HEADERS_BASE = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Connection": "close"
    }

    def __init__(self):
        self.proxy_url = None
        self.proxies = None
        self.current_host = None

    def switch_proxy_node(self, host_index: int = 0):
        """切换隧道节点，0全球/1美洲/2亚洲"""
        if host_index >= len(self.PROXY_HOST_LIST):
            host_index = 0
        self.current_host = self.PROXY_HOST_LIST[host_index]
        self.proxy_url = f"http://{self.PROXY_USER}:{self.PROXY_PWD}@{self.current_host}:{self.PROXY_PORT}"
        self.proxies = {
            "http": self.proxy_url,
            "https": self.proxy_url
        }

    def get_export_ip(self) -> str:
        """走代理访问httpbin，返回当前隧道出口IP，验证代理是否生效"""
        if self.proxies is None:
            self.switch_proxy_node()
        resp = requests.get(
            url="http://httpbin.org/ip",
            proxies=self.proxies,
            headers=self.HEADERS_BASE,
            timeout=self.TIMEOUT,
            verify=False
        )
        if resp.status_code != 200:
            raise ConnectionError(f"代理节点{self.current_host}失效，状态码:{resp.status_code}")
        export_ip = resp.json()["origin"]
        return export_ip

    def head_check_url(self, target_url: str, allow_redirects=True):
        """HEAD检测链接状态码，用于404判断"""
        try:
            resp = requests.head(
                url=target_url,
                proxies=self.proxies,
                headers=self.HEADERS_BASE,
                timeout=self.TIMEOUT,
                allow_redirects=allow_redirects,
                verify=False
            )
            return resp.status_code
        except requests.RequestException as e:
            raise RuntimeError(f"链接访问异常: {str(e)}")

    def get_request(self, target_url: str):
        """GET请求完整页面"""
        resp = requests.get(
            url=target_url,
            proxies=self.proxies,
            headers=self.HEADERS_BASE,
            timeout=self.TIMEOUT,
            verify=False
        )
        return resp