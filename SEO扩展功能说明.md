# SEO 扩展功能 API 使用指南

## 📋 目录
- [新增 SEO 数据维度](#新增-seo-数据维度)
- [API 端点列表](#api-端点列表)
- [配置说明](#配置说明)
- [使用示例](#使用示例)

---

## 🎯 新增 SEO 数据维度

除了原有的**健康度评分、热门搜索、热门页面、国家地区、设备类型**外，现在还支持：

### 1. **搜索类型分析 (Search Types)**
- Web 搜索表现
- 图片搜索表现
- 视频搜索表现
- 新闻搜索表现
- 各类型的点击量、展示量、CTR、平均排名对比

### 2. **性能趋势分析 (Performance Trend)**
- 按天/周/月的时间序列数据
- 点击量趋势图
- 展示量趋势图
- CTR 变化趋势
- 排名变化趋势
- 支持自定义时间粒度

### 3. **按排名范围查询 (Queries by Position)**
- 排名 1-3（首页顶部）
- 排名 4-10（首页）
- 排名 11-20（第二页）
- 排名 21-50（第三到五页）
- 排名 51-100（后续页面）
- 识别优化机会（高展示低排名的关键词）

### 4. **移动可用性 (Mobile Usability)**
- 视口配置问题
- 字体大小可读性
- 触摸元素间距
- 内容宽度溢出
- 需要 PageSpeed Insights API

### 5. **核心网页指标 (Core Web Vitals)**
- **LCP** (Largest Contentful Paint) - 最大内容绘制时间
- **FID** (First Input Delay) - 首次输入延迟
- **CLS** (Cumulative Layout Shift) - 累积布局偏移
- **FCP** (First Contentful Paint) - 首次内容绘制
- **Speed Index** - 速度指数
- 综合性能评分
- 需要 PageSpeed Insights API

### 6. **Sitemap 状态 (Sitemap Status)**
- 已提交的 Sitemap 列表
- 每个 Sitemap 的类型
- 待处理状态
- 最后提交时间
- 错误和警告数量

### 7. **索引覆盖率 (Index Coverage)**
- 索引状态摘要
- 被排除的页面原因
- 建议查看 GSC UI 获取详细数据

---

## 🔌 API 端点列表

### 基础信息
- **Base URL**: `/api/seo/`
- **认证**: 需要管理员权限 (`IsAdmin`)
- **方法**: GET

### 端点详情

#### 1. 搜索类型分析
```
GET /api/seo/search-types?site_url=https://example.com/&days=30
```

**参数**:
- `site_url` (必填): 网站 URL
- `days` (可选): 统计天数，默认 30

**返回示例**:
```json
{
  "code": 200,
  "message": "搜索类型数据获取成功",
  "data": [
    {
      "search_type": "web",
      "total_clicks": 15000,
      "total_impressions": 500000,
      "avg_ctr": 3.0,
      "avg_position": 8.5
    },
    {
      "search_type": "image",
      "total_clicks": 5000,
      "total_impressions": 200000,
      "avg_ctr": 2.5,
      "avg_position": 12.3
    }
  ]
}
```

---

#### 2. 性能趋势
```
GET /api/seo/performance-trend?site_url=https://example.com/&days=90&granularity=week
```

**参数**:
- `site_url` (必填): 网站 URL
- `days` (可选): 统计天数，默认 30
- `granularity` (可选): 粒度 `day`/`week`/`month`，默认 `day`

**返回示例**:
```json
{
  "code": 200,
  "message": "性能趋势数据获取成功（粒度：week）",
  "data": [
    {
      "date": "2024-01-01",
      "end_date": "2024-01-07",
      "clicks": 1200,
      "impressions": 45000,
      "ctr": 2.67,
      "position": 9.5
    }
  ]
}
```

---

#### 3. 按排名范围查询
```
GET /api/seo/queries-by-position?site_url=https://example.com/&position_range=4-10&days=30
```

**参数**:
- `site_url` (必填): 网站 URL
- `position_range` (可选): 排名范围 `1-3`/`4-10`/`11-20`/`21-50`/`51-100`，默认 `1-10`
- `days` (可选): 统计天数，默认 30

**返回示例**:
```json
{
  "code": 200,
  "message": "排名 4-10 的查询数据获取成功",
  "data": [
    {
      "query": "iphone wallpaper hd",
      "clicks": 850,
      "impressions": 15000,
      "ctr": 5.67,
      "position": 6.2,
      "opportunity": "high"
    }
  ]
}
```

**opportunity 字段说明**:
- `high`: 高展示量但排名较低，有较大优化空间
- `medium`: 中等优化机会

---

#### 4. 移动可用性
```
GET /api/seo/mobile-usability?site_url=https://example.com/
```

**参数**:
- `site_url` (必填): 网站 URL

**返回示例**:
```json
{
  "code": 200,
  "message": "发现 3 个移动可用性问题",
  "data": [
    {
      "id": "viewport",
      "title": "未配置视口",
      "description": "页面没有配置视口元标签",
      "score": 0,
      "severity": "critical"
    }
  ]
}
```

**注意**: 需要配置 `GOOGLE_PAGESPEED_API_KEY`

---

#### 5. Core Web Vitals
```
GET /api/seo/core-web-vitals?site_url=https://example.com/
```

**参数**:
- `site_url` (必填): 网站 URL

**返回示例**:
```json
{
  "code": 200,
  "message": "Core Web Vitals 数据获取成功",
  "data": {
    "lcp": 2500,
    "fid": 100,
    "cls": 0.1,
    "fcp": 1800,
    "speed_index": 3200,
    "performance_score": 85
  }
}
```

**指标说明**:
- **LCP**: < 2500ms 为良好
- **FID**: < 100ms 为良好
- **CLS**: < 0.1 为良好
- **performance_score**: 0-100 分

**注意**: 需要配置 `GOOGLE_PAGESPEED_API_KEY`

---

#### 6. Sitemap 状态
```
GET /api/seo/sitemap-status?site_url=https://example.com/
```

**参数**:
- `site_url` (必填): 网站 URL

**返回示例**:
```json
{
  "code": 200,
  "message": "获取到 2 个 Sitemap 状态",
  "data": [
    {
      "path": "https://example.com/sitemap.xml",
      "type": "sitemap",
      "is_pending": false,
      "is_sitemap_index": false,
      "last_submitted": "2024-01-15T10:30:00Z",
      "errors": 0,
      "warnings": 2
    }
  ]
}
```

---

#### 7. 索引覆盖率
```
GET /api/seo/index-coverage?site_url=https://example.com/
```

**参数**:
- `site_url` (必填): 网站 URL

**返回示例**:
```json
{
  "code": 200,
  "message": "索引覆盖率信息获取成功",
  "data": {
    "note": "Index Coverage API 需要通过 Search Console UI 查看",
    "recommendation": "建议定期在 GSC 中检查\"索引\"报告"
  }
}
```

**注意**: Google Search Console API v1 不直接提供索引覆盖率数据，建议在 GSC UI 中查看。

---

## ⚙️ 配置说明

### 1. Google PageSpeed Insights API Key

用于获取 Core Web Vitals 和移动可用性数据。

**获取步骤**:
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用 "PageSpeed Insights API"
4. 创建 API Key
5. 将 API Key 添加到 `.env` 文件：

```env
GOOGLE_PAGESPEED_API_KEY=your_actual_api_key_here
```

### 2. 第三方 SEO 工具 API Keys（可选）

如需使用关键词研究和外链管理功能，需配置：

```env
# SEMrush API
SEMRUSH_API_KEY=your_semrush_api_key

# Ahrefs API
AHREFS_API_KEY=your_ahrefs_api_key

# Majestic API
MAJESTIC_API_KEY=your_majestic_api_key
```

---

## 💡 使用示例

### 场景 1: 完整的 SEO 仪表盘

```python
import requests

base_url = "http://localhost:8000/api/seo"
headers = {"Authorization": "Bearer YOUR_ADMIN_TOKEN"}

# 1. 基础仪表盘
dashboard = requests.get(f"{base_url}/dashboard/", 
                        params={"site_url": "https://example.com/", "days": 30},
                        headers=headers)

# 2. 性能趋势（最近 90 天，按周）
trend = requests.get(f"{base_url}/performance-trend/",
                    params={"site_url": "https://example.com/", "days": 90, "granularity": "week"},
                    headers=headers)

# 3. 搜索类型分布
search_types = requests.get(f"{base_url}/search-types/",
                           params={"site_url": "https://example.com/", "days": 30},
                           headers=headers)

# 4. Core Web Vitals
vitals = requests.get(f"{base_url}/core-web-vitals/",
                     params={"site_url": "https://example.com/"},
                     headers=headers)
```

### 场景 2: 识别优化机会

```python
# 找出排名 4-10 但有高展示量的关键词
queries = requests.get(f"{base_url}/queries-by-position/",
                      params={
                          "site_url": "https://example.com/",
                          "position_range": "4-10",
                          "days": 30
                      },
                      headers=headers)

# 筛选出高机会关键词
high_opportunity = [
    q for q in queries.json()['data'] 
    if q['opportunity'] == 'high'
]

print(f"发现 {len(high_opportunity)} 个高优化机会关键词")
for q in high_opportunity[:5]:
    print(f"- {q['query']}: 展示 {q['impressions']}, 排名 {q['position']}")
```

### 场景 3: 移动端优化检查

```python
# 检查移动可用性
mobile_issues = requests.get(f"{base_url}/mobile-usability/",
                            params={"site_url": "https://example.com/"},
                            headers=headers)

# 检查 Core Web Vitals
vitals = requests.get(f"{base_url}/core-web-vitals/",
                     params={"site_url": "https://example.com/"},
                     headers=headers)

# 生成报告
issues = mobile_issues.json()['data']
vitals_data = vitals.json()['data']

print("=== 移动端优化报告 ===")
print(f"\n移动可用性问题: {len(issues)} 个")
for issue in issues:
    print(f"  - [{issue['severity']}] {issue['title']}")

print(f"\nCore Web Vitals:")
print(f"  LCP: {vitals_data.get('lcp', 0)}ms ({'✅' if vitals_data.get('lcp', 0) < 2500 else '❌'})")
print(f"  FID: {vitals_data.get('fid', 0)}ms ({'✅' if vitals_data.get('fid', 0) < 100 else '❌'})")
print(f"  CLS: {vitals_data.get('cls', 0)} ({'✅' if vitals_data.get('cls', 0) < 0.1 else '❌'})")
```

### 场景 4: Sitemap 监控

```python
# 检查 Sitemap 状态
sitemaps = requests.get(f"{base_url}/sitemap-status/",
                       params={"site_url": "https://example.com/"},
                       headers=headers)

for sitemap in sitemaps.json()['data']:
    if sitemap['errors'] > 0:
        print(f"⚠️ Sitemap {sitemap['path']} 有 {sitemap['errors']} 个错误")
    if sitemap['warnings'] > 0:
        print(f"⚡ Sitemap {sitemap['path']} 有 {sitemap['warnings']} 个警告")
```

---

## 📊 数据可视化建议

### 1. 性能趋势图
使用折线图展示 `performance-trend` 数据：
- X 轴：日期
- Y 轴：点击量/展示量
- 双 Y 轴：CTR 和排名

### 2. 搜索类型饼图
使用饼图展示 `search-types` 数据：
- 各搜索类型的点击量占比
- 各搜索类型的展示量占比

### 3. 排名分布柱状图
使用堆叠柱状图展示 `queries-by-position` 数据：
- X 轴：排名范围
- Y 轴：关键词数量
- 颜色：优化机会等级

### 4. Core Web Vitals 仪表盘
使用仪表盘组件展示：
- LCP、FID、CLS 三个核心指标
- 绿色/黄色/红色区域标识好坏
- 历史趋势对比

---

## 🔍 最佳实践

### 1. 定期监控
- **每日**: 检查性能趋势、Core Web Vitals
- **每周**: 分析排名变化、新关键词机会
- **每月**: 全面 SEO 审计、Sitemap 检查

### 2. 优化优先级
1. 修复移动可用性问题（高严重性）
2. 优化 Core Web Vitals（LCP > 2500ms 的页面）
3. 提升高展示低排名关键词（opportunity: high）
4. 处理 Sitemap 错误和警告

### 3. 数据缓存
由于 API 调用有限制，建议：
- 缓存趋势数据（每小时更新）
- 缓存 Core Web Vitals（每天更新）
- 实时查询热门搜索和排名

---

## ❓ 常见问题

### Q1: 为什么某些 API 返回空数据？
**A**: 可能原因：
- 网站在 GSC 中没有足够的数据
- API Key 未正确配置
- 网站未在 GSC 中验证

### Q2: Core Web Vitals 数据不准确？
**A**: PageSpeed Insights 提供的是实验室数据（Lab Data），与实际用户体验（Field Data）可能有差异。建议结合 GSC 的 Core Web Vitals 报告使用。

### Q3: 如何获取历史数据？
**A**: Google Search Console API 最多提供 16 个月的历史数据。更早期的数据需要在 GSC UI 中导出。

### Q4: 索引覆盖率为什么无法获取？
**A**: GSC API v1 不提供索引覆盖率的详细数据。建议使用：
- GSC UI 手动查看
- 第三方 SEO 工具（如 SEMrush、Ahrefs）
- 定期爬取自己的网站检测索引状态

---

## 📞 技术支持

如有问题，请检查：
1. `.env` 配置文件是否正确
2. API Key 是否有效且有足够配额
3. 网站是否已在 GSC 中验证
4. 网络连接和代理设置

---

**更新时间**: 2024-04-23  
**版本**: v2.0
