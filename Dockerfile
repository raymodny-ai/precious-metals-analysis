# 使用官方Python基础镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_DEBUG=False

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装Playwright依赖
RUN pip install playwright && playwright install-deps

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# 复制应用代码
COPY . .

# 创建非root用户
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 暴露端口
EXPOSE 5000 8501

# 启动脚本
COPY scripts/start.sh /start.sh
# 暂时无法chmod，假设在Windows上构建，Linux上运行需要chmod +x

# 默认命令（可以被docker-compose覆盖）
CMD ["python", "app.py"]
