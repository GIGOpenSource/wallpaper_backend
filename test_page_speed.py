# -*- coding: UTF-8 -*-
"""
页面速度功能测试脚本
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WallPaper.settings.pro')
django.setup()

from App.view.seo.page_speed.tools import test_page_speed, get_site_prefix
from models.models import PageSpeed


def test_get_site_prefix():
    """测试获取网站前缀"""
    print("=" * 50)
    print("测试1: 获取网站前缀")
    print("=" * 50)
    prefix = get_site_prefix()
    print(f"网站前缀: {prefix}")
    print()


def test_page_speed_scan():
    """测试页面速度扫描"""
    print("=" * 50)
    print("测试2: 页面速度扫描")
    print("=" * 50)
    
    test_paths = [
        "/markwallpapers/search",
        "/markwallpapers/detail/123",
        "/",
    ]
    
    for path in test_paths:
        print(f"\n测试路径: {path}")
        result = test_page_speed(path)
        print(f"  综合评分: {result['overall_score']}")
        print(f"  LCP: {result['lcp']}秒")
        print(f"  FID: {result['fid']}毫秒")
        print(f"  CLS: {result['cls']}")
        print(f"  加载时间: {result['load_time']}秒")
        print(f"  页面大小: {result['page_size']}KB")
        print(f"  问题数: {result['issue_count']}")
    print()


def test_database_operations():
    """测试数据库操作"""
    print("=" * 50)
    print("测试3: 数据库操作")
    print("=" * 50)
    
    # 清理测试数据
    PageSpeed.objects.filter(page_path__startswith="/test_").delete()
    print("已清理测试数据")
    
    # 创建测试记录
    test_path = "/test_page_speed_1"
    site_prefix = get_site_prefix()
    full_url = f"{site_prefix}{test_path}"
    
    result = test_page_speed(test_path)
    
    page_speed = PageSpeed.objects.create(
        page_path=test_path,
        full_url=full_url,
        overall_score=result['overall_score'],
        lcp=result['lcp'],
        fid=result['fid'],
        cls=result['cls'],
        load_time=result['load_time'],
        page_size=result['page_size'],
        issue_count=result['issue_count']
    )
    
    print(f"\n创建记录成功:")
    print(f"  ID: {page_speed.id}")
    print(f"  页面路径: {page_speed.page_path}")
    print(f"  完整URL: {page_speed.full_url}")
    print(f"  综合评分: {page_speed.overall_score}")
    
    # 查询记录
    records = PageSpeed.objects.filter(page_path__startswith="/test_")
    print(f"\n查询到 {records.count()} 条测试记录")
    
    # 更新记录
    page_speed.remark = "测试备注"
    page_speed.save()
    print(f"\n更新记录成功，备注: {page_speed.remark}")
    
    # 删除记录
    page_speed.delete()
    print(f"\n删除记录成功")
    
    remaining = PageSpeed.objects.filter(page_path__startswith="/test_").count()
    print(f"剩余测试记录: {remaining}")
    print()


def test_statistics():
    """测试统计功能"""
    print("=" * 50)
    print("测试4: 统计功能")
    print("=" * 50)
    
    from django.db.models import Avg
    
    total = PageSpeed.objects.count()
    avg_score = PageSpeed.objects.aggregate(avg=Avg('overall_score'))['avg'] or 0
    excellent = PageSpeed.objects.filter(overall_score__gte=90).count()
    needs_improvement = PageSpeed.objects.filter(overall_score__lt=70).count()
    
    print(f"总页面数: {total}")
    print(f"平均评分: {round(avg_score, 2)}")
    print(f"优秀页面数（>=90）: {excellent}")
    print(f"待优化页面数（<70）: {needs_improvement}")
    print()


if __name__ == "__main__":
    print("\n开始测试页面速度功能...\n")
    
    try:
        test_get_site_prefix()
        test_page_speed_scan()
        test_database_operations()
        test_statistics()
        
        print("=" * 50)
        print("所有测试完成！")
        print("=" * 50)
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
