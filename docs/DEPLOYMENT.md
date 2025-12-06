# 🚀 Precious Metals Analysis System - 部署指南

## 📋 目录

1. [系统要求](#系统要求)
2. [Windows 11 本地部署](#windows-11-本地部署)
3. [Docker 容器部署](#docker-容器部署)
4. [生产环境配置](#生产环境配置)
5. [常见问题](#常见问题)

---

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4核 | 8核+ |
| 内存 | 8GB | 16GB+ |
| 硬盘 | 20GB SSD | 100GB SSD |
| GPU | 无 | NVIDIA GPU (用于ML推理加速) |

### 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10 - 3.12 | 推荐3.11 |
| PostgreSQL | 14+ | 可选TimescaleDB扩展 |
| Redis | 7+ | 缓存和消息队列 |
| Node.js | 18+ | 前端构建 (可选) |
| Docker | 24+ | 容器部署 |

---

## Windows 11 本地部署

### 1. 安装 Python

```powershell
# 从 Microsoft Store 安装 Python 3.11
winget install Python.Python.3.11

# 验证安装
python --version
pip --version
```

### 2. 安装 PostgreSQL

```powershell
# 使用 winget 安装
winget install PostgreSQL.PostgreSQL

# 或下载: https://www.postgresql.org/download/windows/
```

安装后创建数据库:
```sql
-- 使用 pgAdmin 或 psql
CREATE DATABASE precious_metals;
CREATE USER pm_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE precious_metals TO pm_user;
```

### 3. 安装 Redis

Windows 上推荐使用 Memurai (Redis 兼容):
```powershell
# 下载: https://www.memurai.com/
# 或使用 WSL2 运行 Redis
wsl --install
wsl -d Ubuntu
sudo apt update && sudo apt install redis-server -y
sudo service redis-server start
```

### 4. 克隆项目

```powershell
# 克隆代码
git clone https://github.com/raymodny-ai/precious-metals-analysis.git
cd precious-metals-analysis
```

### 5. 创建虚拟环境

```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 如果遇到执行策略问题
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 6. 安装依赖

```powershell
# 升级 pip
python -m pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt

# 如果 torch 安装很慢，可以使用清华源
pip install torch -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 7. 配置环境变量

```powershell
# 复制配置模板
copy .env.example .env

# 编辑 .env 文件
notepad .env
```

`.env` 文件内容:
```ini
# 数据库
DATABASE_URL=postgresql://pm_user:your_password@localhost:5432/precious_metals
REDIS_URL=redis://localhost:6379/0

# API Keys (可选)
DEEPSEEK_API_KEY=your_key
FRED_API_KEY=your_key
NEWS_API_KEY=your_key

# 安全
JWT_SECRET_KEY=your_super_secret_key_change_this

# 应用设置
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
```

### 8. 初始化数据库

```powershell
# 运行数据库迁移 (如果使用Alembic)
# alembic upgrade head

# 或使用Python脚本创建表
python -c "from src.models.base import create_tables, Base; from sqlalchemy import create_engine; e = create_engine('postgresql://pm_user:your_password@localhost:5432/precious_metals'); create_tables(e)"
```

### 9. 启动服务

```powershell
# 启动 API 服务器
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# 或使用 Python 直接运行
python -m src.api.main
```

### 10. 验证安装

```powershell
# 检查健康状态
curl http://localhost:8000/health

# 打开浏览器访问
start http://localhost:8000/docs
```

### Windows 服务 (持久化运行)

使用 NSSM 将应用注册为 Windows 服务:

```powershell
# 下载 NSSM: https://nssm.cc/download

# 安装服务
nssm install PreciousMetalsAPI "C:\path\to\venv\Scripts\python.exe"
nssm set PreciousMetalsAPI AppParameters "-m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
nssm set PreciousMetalsAPI AppDirectory "C:\path\to\precious-metals-analysis"

# 启动服务
nssm start PreciousMetalsAPI
```

---

## Docker 容器部署

### 1. 安装 Docker Desktop

```powershell
# Windows 11 安装 Docker Desktop
winget install Docker.DockerDesktop

# 重启后验证
docker --version
docker-compose --version
```

### 2. 创建 Dockerfile

项目已包含 `Dockerfile`:

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/
COPY configs/ ./configs/

# 创建非root用户
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3. 创建 docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  # API 服务
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/precious_metals
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-change_this_secret}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./models:/app/models

  # PostgreSQL 数据库
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: precious_metals
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Redis 缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # Prometheus 监控 (可选)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
    profiles:
      - monitoring

  # Grafana 仪表盘 (可选)
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    profiles:
      - monitoring

volumes:
  postgres_data:
  redis_data:
  grafana_data:
```

### 4. 构建和启动

```powershell
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 检查状态
docker-compose ps
```

### 5. 启动监控服务 (可选)

```powershell
# 启动包含 Prometheus 和 Grafana 的完整栈
docker-compose --profile monitoring up -d

# 访问
# - API: http://localhost:8000
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

### 6. 常用 Docker 命令

```powershell
# 停止所有服务
docker-compose down

# 停止并删除数据
docker-compose down -v

# 重启单个服务
docker-compose restart api

# 进入容器
docker-compose exec api bash

# 查看资源使用
docker stats

# 清理未使用资源
docker system prune -a
```

---

## 生产环境配置

### 环境变量

```ini
# .env.production
DATABASE_URL=postgresql://user:password@prod-db:5432/precious_metals
REDIS_URL=redis://prod-redis:6379/0

# 关闭调试
DEBUG=false
ENVIRONMENT=production

# 安全密钥 (使用强随机值)
JWT_SECRET_KEY=your_very_long_random_secret_key_here

# API Keys
DEEPSEEK_API_KEY=sk-xxx
FRED_API_KEY=xxx
NEWS_API_KEY=xxx

# 性能
API_WORKERS=4
```

### Nginx 反向代理

```nginx
# /etc/nginx/sites-available/precious-metals
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### SSL 证书 (Let's Encrypt)

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

---

## 常见问题

### Q: pip install 失败

```powershell
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 如果 torch 太大，单独安装
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### Q: PostgreSQL 连接失败

```powershell
# 检查服务状态
Get-Service postgresql*

# 检查防火墙
netsh advfirewall firewall add rule name="PostgreSQL" dir=in action=allow protocol=tcp localport=5432
```

### Q: Redis 连接失败 (Windows)

```powershell
# 使用 WSL2
wsl -d Ubuntu -e redis-cli ping

# 或安装 Memurai
# 检查服务: Get-Service memurai
```

### Q: Docker 构建慢

```powershell
# 使用国内镜像
# 编辑 Docker Desktop Settings -> Docker Engine
{
  "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"]
}
```

### Q: 内存不足

```powershell
# 减少 torch 内存使用
# 在代码中设置
import torch
torch.set_num_threads(2)
```

---

## 📞 支持

- 📧 Issues: [GitHub Issues](https://github.com/raymodny-ai/precious-metals-analysis/issues)
- 📖 文档: [API Docs](http://localhost:8000/docs)
