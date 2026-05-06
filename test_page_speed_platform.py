# -*- coding: UTF-8 -*-
"""
页面速度平台支持测试脚本
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WallPaper.settings.pro')
django.setup()

from App.view.seo.page_speed.tools import test_page_speed, get_site_prefix
from models.models import PageSpeed


def test_platform_scanning():
    """测试不同平台的页面速度扫描"""
    print("=" * 60)
    print("测试1: 不同平台的页面速度扫描")
    print("=" * 60)
    
    test_path = "/markwallpapers/search"
    platforms = ['page', 'phone', 'pad']
    
    for platform in platforms:
        print(f"\n测试路径: {test_path}")
        print(f"平台类型: {platform}")
        
        result = test_page_speed(test_path, platform)
        
        print(f"  综合评分: {result['overall_score']}")
        print(f"  LCP: {result['lcp']}秒")
        print(f"  FID: {result['fid']}毫秒")
        print(f"  CLS: {result['cls']}")
        print(f"  加载时间: {result['load_time']}秒")
        print(f"  页面大小: {result['page_size']}KB")
        print(f"  问题数: {result['issue_count']}")
        print(f"  移动友好性: {result['mobile_friendly']}")
    
    print()


def test_database_operations():
    """测试数据库操作"""
    print("=" * 60)
    print("测试2: 数据库操作（多平台）")
    print("=" * 60)
    
    # 清理测试数据
    PageSpeed.objects.filter(page_path="/test_platform").delete()
    print("已清理测试数据")
    
    test_path = "/test_platform"
    site_prefix = get_site_prefix()
    full_url = f"{site_prefix}{test_path}"
    
    platforms = ['page', 'phone', 'pad']
    
    for platform in platforms:
        print(f"\n创建 {platform} 平台记录...")
        
        result = test_page_speed(test_path, platform)
        
        page_speed = PageSpeed.objects.create(
            page_path=test_path,
            platform=platform,
            full_url=full_url,
            overall_score=result['overall_score'],
            mobile_friendly=result.get('mobile_friendly'),
            lcp=result['lcp'],
            fid=result['fid'],
            cls=result['cls'],
            load_time=result['load_time'],
            page_size=result['page_size'],
            issue_count=result['issue_count']
        )
        
        print(f"  ID: {page_speed.id}")
        print(f"  平台: {page_speed.get_platform_display()}")
        print(f"  评分: {page_speed.overall_score}")
        print(f"  移动友好: {page_speed.get_mobile_friendly_display() if page_speed.mobile_friendly else 'N/A'}")
    
    # 查询所有平台的记录
    print(f"\n查询所有平台记录:")
    records = PageSpeed.objects.filter(page_path=test_path).order_by('platform')
    for record in records:
        print(f"  - {record.get_platform_display()}: 评分={record.overall_score}, "
              f"加载时间={record.load_time}秒, "
              f"移动友好={record.get_mobile_friendly_display() if record.mobile_friendly else 'N/A'}")
    
    # 按平台筛选
    print(f"\n只查询手机端记录:")
    phone_records = PageSpeed.objects.filter(page_path=test_path, platform='phone')
    print(f"  找到 {phone_records.count()} 条记录")
    
    # 删除测试数据
    PageSpeed.objects.filter(page_path=test_path).delete()
    print(f"\n已删除所有测试数据")
    
    remaining = PageSpeed.objects.filter(page_path=test_path).count()
    print(f"剩余测试记录: {remaining}")
    print()


def test_unique_constraint():
    """测试唯一约束"""
    print("=" * 60)
    print("测试3: 唯一约束测试")
    print("=" * 60)
    
    test_path = "/test_unique"
    site_prefix = get_site_prefix()
    full_url = f"{site_prefix}{test_path}"
    
    # 创建第一条记录 (page)
    print("\n创建桌面端记录...")
    result = test_page_speed(test_path, 'page')
    page_speed1 = PageSpeed.objects.create(
        page_path=test_path,
        platform='page',
        full_url=full_url,
        overall_score=result['overall_score'],
        lcp=result['lcp'],
        fid=result['fid'],
        cls=result['cls'],
        load_time=result['load_time'],
        page_size=result['page_size'],
        issue_count=result['issue_count']
    )
    print(f"  成功创建: {page_speed1}")
    
    # 尝试创建相同的记录（应该更新而不是创建新的）
    print("\n尝试再次创建桌面端记录（应触发更新）...")
    result = test_page_speed(test_path, 'page')
    page_speed2, created = PageSpeed.objects.update_or_create(
        page_path=test_path,
        platform='page',
        defaults={
            'full_url': full_url,
            'overall_score': result['overall_score'],
            'lcp': result['lcp'],
            'fid': result['fid'],
            'cls': result['cls'],
            'load_time': result['load_time'],
            'page_size': result['page_size'],
            'issue_count': result['issue_count']
        }
    )
    print(f"  是否创建新记录: {created}")
    print(f"  记录ID: {page_speed2.id}")
    
    # 创建手机端记录（应该成功，因为platform不同）
    print("\n创建手机端记录（应成功，platform不同）...")
    result = test_page_speed(test_path, 'phone')
    page_speed3 = PageSpeed.objects.create(
        page_path=test_path,
        platform='phone',
        full_url=full_url,
        overall_score=result['overall_score'],
        mobile_friendly=result.get('mobile_friendly'),
        lcp=result['lcp'],
        fid=result['fid'],
        cls=result['cls'],
        load_time=result['load_time'],
        page_size=result['page_size'],
        issue_count=result['issue_count']
    )
    print(f"  成功创建: {page_speed3}")
    
    # 统计
    count = PageSpeed.objects.filter(page_path=test_path).count()
    print(f"\n同一页面路径的不同平台记录数: {count}")
    
    # 清理
    PageSpeed.objects.filter(page_path=test_path).delete()
    print("已清理测试数据")
    print()


def test_statistics():
    """测试统计功能"""
    print("=" * 60)
    print("测试4: 统计功能（按平台）")
    print("=" * 60)
    
    from django.db.models import Avg
    
    # 整体统计
    print("\n整体统计:")
    total = PageSpeed.objects.count()
    avg_score = PageSpeed.objects.aggregate(avg=Avg('overall_score'))['avg'] or 0
    print(f"  总记录数: {total}")
    print(f"  平均评分: {round(avg_score, 2)}")
    
    # 按平台统计
    for platform in ['page', 'phone', 'pad']:
        queryset = PageSpeed.objects.filter(platform=platform)
        count = queryset.count()
        if count > 0:
            avg = queryset.aggregate(avg=Avg('overall_score'))['avg'] or 0
            excellent = queryset.filter(overall_score__gte=90).count()
            needs_improvement = queryset.filter(overall_score__lt=70).count()
            
            print(f"\n{platform} 平台统计:")
            print(f"  记录数: {count}")
            print(f"  平均评分: {round(avg, 2)}")
            print(f"  优秀页面: {excellent}")
            print(f"  待优化: {needs_improvement}")
    
    print()


if __name__ == "__main__":
    print("\n开始测试页面速度平台支持功能...\n")
    
    try:
        test_platform_scanning()
        test_database_operations()
        test_unique_constraint()
        test_statistics()
        
        print("=" * 60)
        print("所有测试完成！")
        print("=" * 60)
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
