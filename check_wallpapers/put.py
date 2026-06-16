from KdlProxy import KdlTunnelProxy

class ProxyTester:
    def __init__(self):
        self.proxy = KdlTunnelProxy()

    def test_proxy_effect(self, test_url: str = "https://w.wallhaven.cc/full/p2/wallhaven-p2m7ve.jpg"):
        """
        完整测试代理链路
        1. 切换全球节点
        2. 获取隧道出口IP（证明流量走代理）
        3. 访问壁纸目标图，返回状态码
        """
        print("="*60)
        print("🔍 开始验证快代理隧道是否生效")
        print("="*60)

        # 1. 切换当前遍历的节点
        print(f"✅ 当前使用隧道节点：{self.proxy.current_host}")

        try:
            # 2. 获取代理出口IP，核心验证：拿到海外IP=流量走代理
            export_ip = self.proxy.get_export_ip()
            print(f"✅ 代理隧道出口IP（真实访问外网IP）：{export_ip}")

            # 3. 访问壁纸图片
            status_code = self.proxy.head_check_url(test_url)
            print(f"✅ 访问壁纸地址 [{test_url}] 状态码：{status_code}")

            return {
                "proxy_node": self.proxy.current_host,
                "export_ip": export_ip,
                "target_status": status_code,
                "success": True
            }

        except ConnectionError as e:
            print(f"❌ 代理节点失效：{str(e)}")
            return {"success": False, "msg": str(e)}
        except RuntimeError as e:
            print(f"❌ 壁纸图片访问失败：{str(e)}")
            return {"success": False, "msg": str(e)}

    def test_switch_all_nodes(self):
        """循环测试全部3个节点，自动切换可用节点"""
        print("\n" + "="*60)
        print("🔄 循环测试所有隧道节点")
        print("="*60)
        for idx, host in enumerate(self.proxy.PROXY_HOST_LIST):
            print(f"\n--- 正在测试节点{idx}：{host} ---")
            self.proxy.switch_proxy_node(idx)
            res = self.test_proxy_effect()
            if res["success"]:
                print(f"🎉 节点 {host} 可用，出口IP：{res['export_ip']}，壁纸访问正常！")
                return res
            else:
                print(f"⚠️ 节点 {host} 不可用，切换下一个")
        print("\n❌ 所有节点全部失效！等待3-5分钟重试")
        return {"success": False, "msg": "全部隧道节点连接失败"}


if __name__ == "__main__":
    tester = ProxyTester()
    # 自动遍历3个节点，找到可用隧道并测试壁纸链接
    result = tester.test_switch_all_nodes()
    print("\n📋 最终测试汇总：", result)