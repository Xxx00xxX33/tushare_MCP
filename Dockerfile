# Tushare MCP Server - Smithery Deployment
# 使用 Python 3.11 slim 镜像以减小体积
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 给启动脚本添加执行权限
RUN chmod +x start.sh

# 暴露端口（Smithery 使用 8081）
EXPOSE 8081

# 健康检查（使用 PORT 环境变量，默认 8081）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8081}/health || exit 1

# 启动命令 - 使用启动脚本
CMD ["./start.sh"]
