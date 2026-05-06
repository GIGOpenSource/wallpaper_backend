# 页面速度功能 - 快速开始

## 1. 数据库迁移

```bash
python manage.py makemigrations models
python manage.py migrate models
```

## 2. 配置API密钥（可选）

在 `WallPaper/settings/pro.py` 中添加：

```python
PAGESPEED_API_KEY = 'your_google_api_key'
```

**不配置也可以运行，会使用模拟数据测试。**

## 3. 启动服务

```bash
python manage.py runserver
```

## 4. 测试接口

### 方式一：使用测试脚本

```bash
python test_page_speed.py
```

### 方式二：使用curl命令

```bash
# 测试新页面
curl -X POST http://localhost:8000/api/seo/page_speed/test/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -d '{"page_path": "/markwallpapers/search"}'

# 获取列表
curl -X GET http://localhost:8000/api/seo/page_speed/ \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"

# 获取统计
curl -X GET http://localhost:8000/api/seo/page_speed/statistics/ \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### 方式三：使用Swagger文档

访问: http://localhost:8000/api/docs/

找到 "页面速度管理" 标签，可以直接在浏览器中测试所有接口。

## 5. 核心接口速查

| 接口 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 测试页面 | POST | `/api/seo/page_speed/test/` | 传入页面路径，自动测试并保存 |
| 获取列表 | GET | `/api/seo/page_speed/` | 支持筛选和分页 |
| 获取详情 | GET | `/api/seo/page_speed/{id}/` | 查看单个页面详情 |
| 创建记录 | POST | `/api/seo/page_speed/` | 创建时自动测试 |
| 更新记录 | PUT/PATCH | `/api/seo/page_speed/{id}/` | 更新备注等信息 |
| 删除记录 | DELETE | `/api/seo/page_speed/{id}/` | 删除记录 |
| 统计数据 | GET | `/api/seo/page_speed/statistics/` | 获取整体统计 |

## 6. 典型使用流程

### 场景1：测试新开发的页面

```bash
POST /api/seo/page_speed/test/
{
  "page_path": "/markwallpapers/new-page"
}
```

系统会：
1. 自动拼接完整URL：`https://www.markwallpapers.com/markwallpapers/new-page`
2. 调用PageSpeed API进行测试
3. 保存测试结果到数据库
4. 返回详细的性能指标

### 场景2：查看所有待优化的页面

```bash
GET /api/seo/page_speed/?max_score=70
```

返回所有评分低于70分的页面，优先优化这些页面。

### 场景3：监控重要页面的性能变化

定期测试关键页面：
- 首页: `/`
- 搜索页: `/markwallpapers/search`
- 详情页: `/markwallpapers/detail/{id}`

通过统计接口查看整体趋势。

## 7. 返回数据说明

```json
{
  "id": 1,
  "page_path": "/markwallpapers/search",           // 页面路径
  "full_url": "https://www.markwallpapers.com/...", // 完整URL
  "overall_score": 85,                              // 综合评分(0-100)
  "lcp": 2.5,                                       // LCP(秒) - 加载性能
  "fid": 50.0,                                      // FID(毫秒) - 交互性
  "cls": 0.1,                                       // CLS - 视觉稳定性
  "load_time": 3.2,                                 // 加载时间(秒)
  "page_size": 1500.5,                              // 页面大小(KB)
  "issue_count": 3,                                 // 问题数
  "tested_at": "2026-05-06T10:00:00Z",             // 测试时间
  "created_at": "2026-05-06T10:00:00Z",            // 创建时间
  "remark": null                                    // 备注
}
```

## 8. 下一步

- 查看详细文档: `PageSpeed功能说明.md`
- 查看使用说明: `init_page_speed.py`
- 访问Swagger文档进行交互式测试

## 9. 常见问题

**Q: 为什么返回的是模拟数据？**
A: 没有配置 `PAGESPEED_API_KEY`，系统自动使用模拟数据。这不影响功能测试。

**Q: 如何获取管理员Token？**
A: 通过登录接口获取，或使用已有的管理员账号Token。

**Q: 可以批量测试多个页面吗？**
A: 可以编写脚本循环调用 `/test/` 接口。

---

**就这么简单！** 🎉

现在你可以开始使用页面速度管理功能了。
