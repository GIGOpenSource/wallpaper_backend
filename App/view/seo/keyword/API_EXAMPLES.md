# Google Trends关键词研究API使用示例

## 安装依赖
```bash
pip install pytrends
```

## API接口列表

### 1. 关键词兴趣趋势
**接口**: `GET /api/seo/keyword/interest_over_time/`

**参数**:
- `keywords`: 关键词，多个用逗号分隔（最多5个）
- `geo`: 国家/地区代码（留空表示全球）
- `timeframe`: 时间范围
- `gprop`: 搜索类型（web/images/news/youtube/froogle）

**示例**:
```bash
# 全球网页搜索趋势
curl "http://localhost:8000/api/seo/keyword/interest_over_time/?keywords=Cartoon,Anime&timeframe=today 12-m"

# 美国图片搜索趋势
curl "http://localhost:8000/api/seo/keyword/interest_over_time/?keywords=Wallpaper&geo=US&timeframe=now 7-d&gprop=images"

# 自定义日期范围
curl "http://localhost:8000/api/seo/keyword/interest_over_time/?keywords=SEO&timeframe=2026-01-01 2026-05-01"
```

**返回数据**:
```json
{
  "code": 200,
  "message": "获取兴趣趋势成功",
  "data": {
    "timeline_data": [
      {"date": "2026-01-01", "Cartoon": 85, "Anime": 60},
      {"date": "2026-01-08", "Cartoon": 90, "Anime": 65}
    ],
    "averages": {"Cartoon": 75.5, "Anime": 55.2},
    "keywords": ["Cartoon", "Anime"],
    "geo": "Worldwide",
    "timeframe": "today 12-m",
    "gprop": "web"
  }
}
```

---

### 2. 相关查询分析
**接口**: `GET /api/seo/keyword/related_queries/`

**参数**:
- `keyword`: 要分析的关键词（必需）
- `geo`: 国家/地区代码
- `timeframe`: 时间范围
- `gprop`: 搜索类型

**示例**:
```bash
# 获取Cartoon的相关查询
curl "http://localhost:8000/api/seo/keyword/related_queries/?keyword=Cartoon&geo=US&timeframe=today 1-m"

# YouTube搜索的相关查询
curl "http://localhost:8000/api/seo/keyword/related_queries/?keyword=Wallpaper&gprop=youtube"
```

**返回数据**:
```json
{
  "code": 200,
  "message": "获取相关查询成功",
  "data": {
    "keyword": "Cartoon",
    "geo": "US",
    "timeframe": "today 1-m",
    "gprop": "web",
    "top": [
      {"query": "cartoon network", "value": 100},
      {"query": "cartoon wallpaper", "value": 85},
      {"query": "disney cartoon", "value": 70}
    ],
    "rising": [
      {"query": "ai cartoon generator", "value": "+350%"},
      {"query": "cartoon ai art", "value": "+250%"},
      {"query": "cartoon style transfer", "value": "Breakout"}
    ]
  }
}
```

---

### 3. 地区兴趣分布
**接口**: `GET /api/seo/keyword/interest_by_region/`

**参数**:
- `keywords`: 关键词，多个用逗号分隔
- `geo`: 国家代码（如US），留空返回国家级别数据
- `timeframe`: 时间范围

**示例**:
```bash
# 全球各国兴趣分布
curl "http://localhost:8000/api/seo/keyword/interest_by_region/?keywords=Wallpaper,Cartoon"

# 美国各州兴趣分布
curl "http://localhost:8000/api/seo/keyword/interest_by_region/?keywords=Wallpaper&geo=US"
```

**返回数据**:
```json
{
  "code": 200,
  "message": "获取地区分布成功",
  "data": {
    "regions": [
      {"region": "United States", "Wallpaper": 100, "Cartoon": 80},
      {"region": "Canada", "Wallpaper": 85, "Cartoon": 70},
      {"region": "United Kingdom", "Wallpaper": 75, "Cartoon": 65}
    ],
    "keywords": ["Wallpaper", "Cartoon"],
    "geo": "Worldwide"
  }
}
```

---

### 4. 关键词对比
**接口**: `GET /api/seo/keyword/compare_keywords/`

**参数**:
- `keywords`: 要比较的关键词，用逗号分隔（2-5个）
- `geo`: 国家/地区代码
- `timeframe`: 时间范围

**示例**:
```bash
curl "http://localhost:8000/api/seo/keyword/compare_keywords/?keywords=Wallpaper,Background,Image&geo=US&timeframe=today 12-m"
```

**返回数据**:
```json
{
  "code": 200,
  "message": "关键词对比完成",
  "data": {
    "timeline_data": [...],
    "averages": {"Wallpaper": 75.5, "Background": 60.2, "Image": 50.8},
    "winner": "Wallpaper",
    "comparison_summary": {
      "Wallpaper": 75.5,
      "Background": 60.2,
      "Image": 50.8
    }
  }
}
```

---

### 5. 热门搜索
**接口**: `GET /api/seo/keyword/trending_searches/`

**参数**:
- `geo`: 国家/地区代码（默认US）
- `category`: 分类（默认all）

**示例**:
```bash
curl "http://localhost:8000/api/seo/keyword/trending_searches/?geo=US"
```

**返回数据**:
```json
{
  "code": 200,
  "message": "获取热门搜索成功",
  "data": {
    "trending_searches": [
      {"title": "AI Technology", "traffic": "500K+"},
      {"title": "Spring Festival", "traffic": "200K+"}
    ],
    "geo": "US",
    "category": "all"
  }
}
```

---

## 参数说明

### timeframe 时间范围格式
- `now 1-H` - 过去1小时
- `now 4-H` - 过去4小时
- `now 7-d` - 过去7天
- `today 1-m` - 过去30天
- `today 3-m` - 过去90天
- `today 12-m` - 过去12个月
- `today+5-y` - 过去5年
- `all` - 从2004年开始
- `YYYY-MM-DD YYYY-MM-DD` - 自定义日期范围

### geo 国家/地区代码
- 留空或 `''` - 全球
- `US` - 美国
- `CN` - 中国
- `GB` - 英国
- `JP` - 日本
- 更多代码参考ISO 3166-1标准

### gprop 搜索类型
- `''` 或 `'web'` - 网页搜索（默认）
- `'images'` - 图片搜索
- `'news'` - 新闻搜索
- `'youtube'` - YouTube搜索
- `'froogle'` - Google购物

---

## Python调用示例

```python
import requests

# 1. 获取关键词趋势
response = requests.get(
    'http://localhost:8000/api/seo/keyword/interest_over_time/',
    params={
        'keywords': 'Cartoon,Anime',
        'geo': 'US',
        'timeframe': 'today 12-m',
        'gprop': 'images'
    }
)
print(response.json())

# 2. 获取相关查询
response = requests.get(
    'http://localhost:8000/api/seo/keyword/related_queries/',
    params={
        'keyword': 'Wallpaper',
        'geo': '',
        'timeframe': 'today 1-m'
    }
)
data = response.json()
print("热门查询:", data['data']['top'])
print("上升查询:", data['data']['rising'])
```

---

## 注意事项

1. **频率限制**: Google Trends有请求频率限制，建议每次请求间隔2-3秒
2. **数据准确性**: 返回的是相对兴趣度（0-100），不是绝对搜索量
3. **地域覆盖**: 某些国家/地区可能没有足够的数据
4. **关键词数量**: 单次最多支持5个关键词对比
5. **语言设置**: 目前默认为英语(hl='en-US')
