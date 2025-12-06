# 贵金属项目数据库设计指南

## 目录
1. [数据库选择理由](#数据库选择理由)
2. [核心表设计](#核心表设计)
3. [性能优化策略](#性能优化策略)
4. [数据保留和合规](#数据保留和合规)
5. [查询优化实践](#查询优化实践)
6. [备份和恢复](#备份和恢复)

---

## 数据库选择理由

### PostgreSQL + TimescaleDB 组合优势

| 维度 | 选择 | 理由 |
|------|------|------|
| **时间序列处理** | TimescaleDB | 自动分块、压缩、性能提升 100 倍+ |
| **事务支持** | PostgreSQL | ACID 保证，金融应用必需 |
| **复杂查询** | PostgreSQL | 支持 JOIN、GROUP BY、Window Function |
| **成本** | 开源免费 | 0 许可证费用 |
| **扩展性** | 水平+垂直 | 支持分片和副本 |

### 与 InfluxDB 对比

| 特性 | PostgreSQL+TimescaleDB | InfluxDB |
|------|-------|---------|
| **ACID 事务** | ✓ | ✗ |
| **复杂分析查询** | ✓ (JOIN, GROUP BY) | △ (基础聚合) |
| **高基数数据** | ✓ | ✗ (性能下降) |
| **历史数据分析** | ✓ | △ |
| **备份/恢复** | ✓ (标准 SQL) | △ (定制工具) |

**结论**：TimescaleDB 对贵金属项目更优，因为需要复杂的情绪分析、相关性计算和金融级别的数据一致性。

---

## 核心表设计

### 1. 时序数据表设计原则

```sql
-- 超表 (Hypertable) 设计模式：
-- 必须包含时间列作为主键的一部分（最左列）
CREATE TABLE price_data (
    time TIMESTAMPTZ NOT NULL,        -- 必须在最左
    symbol TEXT NOT NULL,              -- 分区列
    close FLOAT8 NOT NULL,
    ...
    PRIMARY KEY (symbol, time)
);
```

**为什么？**
- TimescaleDB 按 `time` 自动分块（chunks）
- 按 `symbol` 分区减少查询扫描范围
- 时间聚合查询性能提升 1000 倍

### 2. 分块策略

```
推荐配置：
- price_data: 7 天分块（1 分钟数据）
- news_articles: 1 天分块（数据更新频繁）
- etf_flows: 7 天分块（日级数据）

计算公式：
  chunk_size = (平均行宽 × 每秒插入数 × 秒数/分块)
  目标: 10 万-500 万行/chunk
```

### 3. 分区策略 (Partitioning)

```sql
-- 多维分区优化
CREATE HYPERTABLE price_data (
    time TIMESTAMPTZ,
    symbol TEXT,  -- 第二分区维度
    ...
    partitioning_column => 'symbol',
    number_partitions => 8  -- 建议 = CPU 核心数/2
);
```

**性能提升**：
- 单维查询 (symbol='GLD') → 性能提升 50-100%
- 减少内存扫描范围
- 支持并行查询处理

### 4. 索引策略

```sql
-- 必需索引
CREATE INDEX idx_price_time_symbol ON price_data (time DESC, symbol);
CREATE INDEX idx_news_symbol_time ON news_articles (symbol, time DESC);
CREATE INDEX idx_etf_flows_time ON etf_flows (time DESC);

-- 搜索索引（用于新闻搜索）
CREATE INDEX idx_news_title_search ON news_articles 
  USING GIN (to_tsvector('english', title));

-- 情绪索引
CREATE INDEX idx_news_sentiment ON news_articles (sentiment_score DESC);
```

**索引成本**：
- 空间：约增加 20-30% 存储
- 写入：性能下降 5-10%（INSERT）
- 读取：性能提升 50-100%（SELECT）

---

## 性能优化策略

### 1. 连续聚合 (Continuous Aggregates)

**传统方式问题**：
```sql
-- 每次查询都要重新计算 - 慢！
SELECT DATE(time), AVG(close), MAX(high), MIN(low)
FROM price_data
WHERE symbol='GLD' AND time > NOW() - INTERVAL '1 year'
GROUP BY DATE(time);
```

**优化方式**：
```sql
-- 创建预计算聚合，自动增量更新
CREATE MATERIALIZED VIEW price_daily
WITH (timescaledb.continuous) AS
SELECT time_bucket(INTERVAL '1 day', time) as day,
       symbol,
       FIRST(open, time) as open,
       MAX(high) as high,
       MIN(low) as low,
       LAST(close, time) as close,
       SUM(volume) as volume
FROM price_data
GROUP BY day, symbol;

-- 查询速度：从 30 秒 → 10 毫秒
```

**何时使用**：
- 频繁的聚合查询（日报告、仪表板）
- 对实时性要求不是极高（可接受 1 小时延迟）
- 需要复杂的多步聚合

### 2. 数据压缩策略

```sql
-- 自动压缩 7 天前的数据
ALTER TABLE price_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',  -- 按 symbol 分段压缩
    timescaledb.compress_orderby = 'time DESC'   -- 按时间倒序压缩
);

SELECT add_compression_policy('price_data', INTERVAL '7 days');
```

**压缩效果**：
- 存储空间：减少 80-90%
- 查询速度：只减少 5-10%（自动解压）
- 适合历史数据（很少查询）

**压缩时间表**：
```
<7 天    : 行存储（实时更新快）
7-30 天  : 块存储（压缩状态）
>30 天   : 冷存储（可选 S3）
```

### 3. 查询优化建议

**✓ 好的查询模式**：
```sql
-- 1. 明确时间范围
SELECT * FROM price_data 
WHERE symbol='GLD' AND time > NOW() - INTERVAL '30 days'
ORDER BY time DESC LIMIT 100;

-- 2. 使用聚合代替子查询
SELECT symbol, AVG(close), MAX(high), MIN(low)
FROM price_data
WHERE time > NOW() - INTERVAL '1 year'
GROUP BY symbol;

-- 3. 利用连续聚合
SELECT * FROM price_daily WHERE symbol='GLD' AND day > NOW() - INTERVAL '1 year';
```

**✗ 避免的查询模式**：
```sql
-- 1. 无时间范围的全表扫描
SELECT * FROM price_data WHERE symbol='GLD';  -- 危险！

-- 2. 负向时间过滤
SELECT * FROM price_data 
WHERE time NOT IN (SELECT time FROM price_data WHERE symbol='SLV');  -- 低效

-- 3. 函数在 WHERE 子句
SELECT * FROM price_data 
WHERE EXTRACT(YEAR FROM time) = 2024;  -- 无法使用索引
```

---

## 数据保留和合规

### 1. 数据保留政策 (Retention Policies)

```sql
-- SEC 规则 17a-4：交易记录保留 6 年，前 2 年需立即可访问
SELECT add_retention_policy('price_data', INTERVAL '6 years');

-- ETF 流量数据：10 年（财务合规）
SELECT add_retention_policy('etf_flows', INTERVAL '10 years');

-- 新闻数据：3 年（业务分析）
SELECT add_retention_policy('news_articles', INTERVAL '3 years');
```

### 2. 自动删除vs冷存储

**自动删除策略**（快速）：
```sql
-- 自动删除 > 2 年的交易信号
SELECT add_retention_policy('trading_signals', INTERVAL '2 years');
```

**冷存储策略**（合规）：
```sql
-- 导出到 S3 存档
COPY (SELECT * FROM price_data WHERE time < NOW() - INTERVAL '2 years')
TO PROGRAM 'aws s3 cp - s3://archive-bucket/price_data.csv'
WITH (FORMAT csv);

-- 然后从热数据库删除
DELETE FROM price_data WHERE time < NOW() - INTERVAL '2 years';
```

### 3. 归档和恢复流程

```python
# 备份策略
1. 日增量备份（仅新数据）
   pg_dump -t price_data --incremental ...
   
2. 周完整备份
   pg_dump precious_metals > backup_week_52.sql
   
3. 月度归档到 S3
   aws s3 cp backup_month_12.sql.gz s3://precious-metals-archive/
```

---

## 查询优化实践

### 1. 常见查询模式性能对比

```sql
-- 查询 1: 获取 GLD 最新 100 个小时蜡烛图
-- 期望延迟: <100ms

-- ✓ 优化版本（使用连续聚合）
SELECT * FROM price_hourly 
WHERE symbol='GLD' AND hour > NOW() - INTERVAL '4 days'
ORDER BY hour DESC LIMIT 100;
-- 实际延迟: ~10ms

-- ✗ 非优化版本（原始数据）
SELECT time_bucket(INTERVAL '1 hour', time) as hour,
       FIRST(close, time) as close,
       MAX(high) as high,
       MIN(low) as low
FROM price_data
WHERE symbol='GLD' AND time > NOW() - INTERVAL '4 days'
GROUP BY hour
ORDER BY hour DESC LIMIT 100;
-- 实际延迟: ~500ms
```

### 2. 情绪分析查询优化

```sql
-- 查询: 过去 7 天黄金新闻情绪趋势

-- ✓ 优化版本（使用聚合视图）
SELECT day, symbol, avg_sentiment, news_volume
FROM daily_sentiment_summary
WHERE symbol='GLD' AND day > NOW() - INTERVAL '7 days'
ORDER BY day DESC;
-- 延迟: ~20ms

-- ✗ 非优化版本（实时计算）
SELECT DATE(time) as day,
       symbol,
       AVG(sentiment_score) as avg_sentiment,
       COUNT(*) as news_volume
FROM news_articles
WHERE symbol='GLD' AND time > NOW() - INTERVAL '7 days'
GROUP BY day, symbol
ORDER BY day DESC;
-- 延迟: ~300ms （取决于新闻数据量）
```

### 3. 聚合函数最佳实践

```sql
-- 使用 TimescaleDB 的 first_agg / last_agg
SELECT symbol,
       first(close, time) as open,      -- 获取时间序列第一个值
       max(high),
       min(low),
       last(close, time) as close        -- 获取时间序列最后一个值
FROM price_data
WHERE time > NOW() - INTERVAL '1 day'
GROUP BY symbol;
```

---

## 备份和恢复

### 1. 完整备份方案

```bash
# 每日增量备份（只备份新数据）
pg_dump --format=custom --no-privileges \
  --exclude-table='old_data' \
  precious_metals > backup_$(date +%Y%m%d).sql.gz

# 上传到 S3 冷存储
aws s3 cp backup_$(date +%Y%m%d).sql.gz \
  s3://precious-metals-backup/daily/

# 每周完整备份
pg_dump --format=tar precious_metals | \
  gzip > backup_full_$(date +%Y_week_%U).tar.gz

aws s3 cp backup_full_*.tar.gz s3://precious-metals-backup/weekly/
```

### 2. 恢复程序

```bash
# 恢复最新状态
pg_restore --format=custom --dbname=precious_metals \
  backup_20251201.sql.gz

# 恢复到指定时间点 (PITR)
# 使用 WAL 档案：
pg_ctl start -D /var/lib/postgresql/data \
  -c 'recovery_target_time = 2025-12-01 14:30:00' \
  -c 'recovery_target_timeline = latest'
```

### 3. 灾难恢复清单

- [ ] 备份数据库凭证（分离存储）
- [ ] 测试恢复流程（每月）
- [ ] 记录 RPO（恢复点目标）= 1 天
- [ ] 记录 RTO（恢复时间目标）= 4 小时
- [ ] 备份监控告警配置

---

## 监控和维护

### 1. 关键监控指标

```sql
-- 查看超表大小
SELECT hypertable_name, pg_size_pretty(total_bytes) as total_size
FROM timescaledb_information.hypertable_size
ORDER BY total_bytes DESC;

-- 查看压缩比例
SELECT hypertable_name, 
       pg_size_pretty(before_compression_total_bytes) as before,
       pg_size_pretty(after_compression_total_bytes) as after,
       ROUND(100.0 * after_compression_total_bytes / 
             NULLIF(before_compression_total_bytes, 0), 1) as compression_ratio
FROM timescaledb_information.compression_stats;

-- 查看分块分布
SELECT chunk_name, 
       range_start, 
       range_end,
       pg_size_pretty(pg_total_relation_size(chunk_name)) as size
FROM timescaledb_information.chunks
WHERE hypertable_name = 'price_data'
ORDER BY range_start DESC;
```

### 2. 性能调优参数

```sql
-- 调整工作内存（用于排序和聚合）
SET work_mem = '4GB';

-- 调整维护工作内存（用于 VACUUM）
SET maintenance_work_mem = '8GB';

-- 调整并行查询
SET max_parallel_workers_per_gather = 4;
SET max_parallel_workers = 8;
```

### 3. 日常维护任务

```sql
-- 每周运行 VACUUM（释放空间）
VACUUM ANALYZE price_data;
VACUUM ANALYZE news_articles;

-- 重建索引（每月）
REINDEX TABLE price_data;

-- 更新统计信息
ANALYZE;
```

---

## 总结

| 功能 | 实现方式 | 性能 | 成本 |
|------|--------|------|------|
| **实时价格** | price_data 表 | <100ms | 低 |
| **小时蜡烛图** | price_hourly 连续聚合 | <20ms | 低 |
| **日级分析** | price_daily 连续聚合 | <10ms | 低 |
| **情绪趋势** | daily_sentiment_summary | <50ms | 低 |
| **历史回测** | 压缩的历史数据 | <500ms | 超低 |
| **合规报告** | 冷存储 + 策略删除 | 按需 | 最低 |

**最终建议**：
- 开发阶段：使用单实例 PostgreSQL + TimescaleDB
- 生产阶段：PostgreSQL Primary + Read Replicas
- 企业阶段：云托管（AWS RDS 或 TimescaleDB Cloud）