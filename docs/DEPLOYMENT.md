# 部署指南

PreciousInsight完整部署文档

---

## 目录

1. [本地开发部署](#本地开发部署)
2. [Docker部署](#docker部署)
3. [生产环境部署](#生产环境部署)
4. [性能优化](#性能优化)
5. [监控与维护](#监控与维护)

---

## 本地开发部署

### 环境要求

- Python 3.9+
- MySQL 8.0+
- Redis 6.0+ (可选,推荐)
- 8GB+ RAM
- 10GB+ 磁盘空间

### 步骤1: 克隆代码

```bash
git clone https://github.com/yourname/PreciousInsight.git
cd PreciousInsight
```

### 步骤2: 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 步骤3: 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 步骤4: 配置环境变量

```bash
cp .env.example .env
```

编辑`.env`文件:

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=precious_insight

# Redis配置 (可选)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# LLM API密钥
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# 数据源API
ALPHA_VANTAGE_KEY=...
```

### 步骤5: 初始化数据库

```bash
python schema/init_database.py
```

### 步骤6: 启动应用

```bash
# 启动Streamlit UI
streamlit run app.py

# 或启动Flask API
python app.py
```

访问: http://localhost:8501

---

## Docker部署

### 方式1: Docker Compose (推荐)

#### 创建docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8501:8501"
      - "5000:5000"
    environment:
      - DB_HOST=mysql
      - REDIS_HOST=redis
    env_file:
      - .env
    depends_on:
      - mysql
      - redis
    volumes:
      - ./data:/app/data
  
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: precious_insight
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  mysql_data:
  redis_data:
```

#### 启动服务

```bash
docker-compose up -d
```

#### 查看日志

```bash
docker-compose logs -f app
```

### 方式2: 单独Docker容器

```bash
# 构建镜像
docker build -t preciousinsight:latest .

# 运行容器
docker run -d \
  --name preciousinsight \
  -p 8501:8501 \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  preciousinsight:latest
```

---

## 生产环境部署

### 云平台部署

#### AWS部署

**方案1: AWS ECS** (推荐)

1. 构建并推送镜像到ECR
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin your-account.dkr.ecr.us-east-1.amazonaws.com

docker tag preciousinsight:latest your-account.dkr.ecr.us-east-1.amazonaws.com/preciousinsight:latest

docker push your-account.dkr.ecr.us-east-1.amazonaws.com/preciousinsight:latest
```

2. 创建ECS任务定义
3. 创建ECS服务
4. 配置负载均衡器

**方案2: AWS EC2**

```bash
# 在EC2上部署
ssh ec2-user@your-instance-ip

# 安装Docker
sudo yum update -y
sudo yum install docker -y
sudo service docker start

# 克隆代码并启动
git clone https://github.com/yourname/PreciousInsight.git
cd PreciousInsight
docker-compose up -d
```

#### 数据库配置

使用AWS RDS (MySQL):
```env
DB_HOST=your-rds-endpoint.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=your_secure_password
DB_NAME=precious_insight
```

使用AWS ElastiCache (Redis):
```env
REDIS_HOST=your-elasticache.cache.amazonaws.com
REDIS_PORT=6379
```

---

## 性能优化

### 1. 数据库优化

#### 添加索引

```sql
-- 价格数据索引
CREATE INDEX idx_prices_symbol_date ON precious_prices(symbol, date);

-- 新闻数据索引
CREATE INDEX idx_news_publish_date ON us_news(publish_date);
CREATE INDEX idx_news_source ON us_news(source);
```

#### 连接池配置

```python
# config/database.py
POOL_SIZE = 20
MAX_OVERFLOW = 10
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600
```

### 2. Redis缓存优化

```python
# 配置TTL
LLM_CACHE_TTL = 3600  # 1小时
DATA_CACHE_TTL = 300  # 5分钟
SIGNAL_CACHE_TTL = 30  # 30秒
```

### 3. Streamlit性能

```python
# 使用缓存装饰器
@st.cache_data(ttl=600)
def get_market_data(symbol, days):
    # 数据获取逻辑
    pass

@st.cache_resource
def init_llm_service():
    # LLM服务初始化
    pass
```

### 4. 并发控制

```python
# 使用线程池
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

# 异步数据获取
futures = [executor.submit(fetch_data, symbol) for symbol in symbols]
results = [f.result() for f in futures]
```

---

## 监控与维护

### 日志配置

```python
# config/logging_config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

### prometheus监控 (可选)

```python
from prometheus_client import Counter, Histogram, start_http_server

# 定义指标
llm_requests = Counter('llm_requests_total', 'Total LLM requests')
llm_latency = Histogram('llm_latency_seconds', 'LLM request latency')

# 启动metrics服务器
start_http_server(9090)
```

### 健康检查

创建`健康检查端点`:

```python
@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'database': check_db_connection(),
        'redis': check_redis_connection(),
        'timestamp': datetime.now().isoformat()
    }
```

### 定时备份

```bash
# backup.sh
#!/bin/bash

DATE=$(date +%Y%m%d)
mysqldump -u root -p precious_insight > backup_$DATE.sql
gzip backup_$DATE.sql

# 上传到S3
aws s3 cp backup_$DATE.sql.gz s3://your-bucket/backups/
```

添加到crontab:
```bash
0 2 * * * /path/to/backup.sh
```

---

## 故障排查

### 常见问题

#### 1. 数据库连接失败

```bash
# 检查MySQL服务
sudo systemctl status mysql

# 检查连接
mysql -u root -p -h localhost
```

#### 2. Redis连接失败

```bash
# 检查Redis服务
redis-cli ping

# 应该返回 PONG
```

#### 3. LLM API超时

检查`.env`中的API密钥是否正确,网络是否正常。

#### 4. 内存不足

```bash
# 检查内存使用
free -h

# 增加swap空间
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 安全建议

1. **环境变量**: 永远不要将`.env`提交到Git
2. **API密钥**: 使用密钥管理服务 (AWS Secrets Manager)
3. **SSL/TLS**: 生产环境必须使用HTTPS
4. **防火墙**: 仅开放必要端口
5. **定期更新**: 及时更新依赖包

---

## 扩展性

### 水平|扩展

使用负载均衡器 (Nginx/AWS ALB):

```nginx
upstream preciousinsight {
    server app1:850 1;
    server app2:8501;
    server app3:8501;
}

server {
    listen 80;
    location / {
        proxy_pass http://preciousinsight;
    }
}
```

### 读写分离

```python
# 主库 (写)
MASTER_DB = {
    'host': 'master-db.example.com',
    'port': 3306
}

# 从库 (读)
SLAVE_DB = {
    'host': 'slave-db.example.com',
    'port': 3306
}
```

---

完整部署成功后,访问 http://your-domain.com 即可使用PreciousInsight！
