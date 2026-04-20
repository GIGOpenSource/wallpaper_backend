# 面板统计模块

## 功能说明

提供系统整体统计数据的面板接口，包括：
- 总用户数量
- 总壁纸数量
- 总浏览量
- 总下载量
- 总点赞数
- 总收藏数
- 日活跃用户（最近24小时）
- 周活跃用户（最近7天）

## 缓存策略

**使用数据表存储每日统计数据**，每天8:00后第一次请求时查询数据库并更新当日记录。

具体逻辑：
1. 每天8:00后第一次请求会查询数据库并更新 `t_dashboard_stats` 表的当日记录
2. 之后的请求直接读取表中数据，不再查询业务表
3. 第二天8:00后的第一次请求再次触发更新

**优势：**
- ✅ 每天只查询一次数据库，大幅减轻服务器负担
- ✅ 保留历史统计数据，方便趋势分析
- ✅ 便于后续扩展更多统计维度和报表功能

## API 接口

### 获取面板统计数据

**接口地址：** `GET /api/dashboard/stats/overview/`

**请求参数：** 无

**响应示例：**
```json
{
  "code": 200,
  "message": "统计数据获取成功",
  "data": {
    "total_users": 1500,
    "total_wallpapers": 5000,
    "total_views": 100000,
    "total_downloads": 50000,
    "total_likes": 30000,
    "total_collections": 20000,
    "daily_active_users": 200,
    "weekly_active_users": 800,
    "last_update_time": "2026-04-20 08:00:00"
  }
}
```

**字段说明：**
- `total_users`: 总用户数量
- `total_wallpapers`: 总壁纸数量
- `total_views`: 总浏览量
- `total_downloads`: 总下载量
- `total_likes`: 总点赞数
- `total_collections`: 总收藏数
- `daily_active_users`: 日活跃用户数（最近24小时内有登录记录的用户）
- `weekly_active_users`: 周活跃用户数（最近7天内有登录记录的用户）
- `last_update_time`: 最后更新时间

## 技术实现

### 文件结构
```
App/view/dashboard/
├── __init__.py
├── urls.py          # 路由配置
├── view.py          # 视图逻辑
├── README.md        # 使用文档
└── test_dashboard.py # 测试脚本
```

### 数据模型

**表名：** `t_dashboard_stats`

**字段说明：**
- `stat_date`: 统计日期（唯一索引）
- `total_users`: 总用户数量
- `total_wallpapers`: 总壁纸数量
- `total_views`: 总浏览量
- `total_downloads`: 总下载量
- `total_likes`: 总点赞数
- `total_collections`: 总收藏数
- `daily_active_users`: 日活跃用户数
- `weekly_active_users`: 周活跃用户数
- `created_at`: 创建时间
- `updated_at`: 更新时间

### 核心特性

1. **数据表缓存**：使用 `DashboardStats` 模型存储每日统计数据
2. **定时刷新**：每天8点后第一次请求自动更新当日数据
3. **历史记录**：保留每日统计数据，支持历史趋势分析
4. **性能优化**：使用聚合查询一次性获取所有统计数据
5. **容错处理**：数据不存在时自动创建新记录

### 依赖模型
- `CustomerUser`: 客户用户模型
- `Wallpapers`: 壁纸模型
- `WallpaperLike`: 壁纸点赞模型
- `WallpaperCollection`: 壁纸收藏模型
- `DashboardStats`: 面板统计数据模型（新增）

## 注意事项

1. 确保已执行数据库迁移：`python manage.py migrate models`
2. 首次访问接口时会自动创建今日统计数据
3. 如需手动重新统计某日数据，可删除该日记录后再次访问接口
4. 可通过查询 `DashboardStats` 表获取历史统计数据进行趋势分析

## 扩展建议

1. **添加更多统计维度**：如新增用户上传数、评论数等
2. **定时任务**：可配置 APScheduler 在每天8:00自动更新统计数据
3. **数据可视化**：基于历史数据生成图表（折线图、柱状图等）
4. **导出功能**：支持导出 Excel/CSV 格式的统计报表
