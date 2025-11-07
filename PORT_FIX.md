# 端口配置修复说明

## 问题发现

Smithery 扫描器仍然超时，原因是：

**Smithery 使用 PORT=8081，而不是 8000！**

根据 Smithery 官方文档：
> "However, when deployed to Smithery, your server must listen on the PORT environment variable, which Smithery will set to 8081."

来源: https://smithery.ai/docs/cookbooks/python_custom_container

## 问题分析

### 原配置
- Dockerfile CMD: `uvicorn app_http:app --host 0.0.0.0 --port 8000`
- 硬编码端口 8000
- Smithery 期望端口 8081
- **结果**: 扫描器连接到 8081，但服务器监听 8000 → 超时

### 正确配置
- 必须使用 PORT 环境变量
- Smithery 会设置 PORT=8081
- 服务器必须监听 ${PORT}

## 修复方案

### 1. 修改 Dockerfile

**修改前**:
```dockerfile
CMD ["uvicorn", "app_http:app", "--host", "0.0.0.0", "--port", "8000"]
```

**修改后**:
```dockerfile
CMD ["./start.sh"]
```

使用启动脚本来处理环境变量。

### 2. 创建 start.sh

```bash
#!/bin/bash
export PORT=${PORT:-8081}
echo "PORT: $PORT"
exec uvicorn app_http:app --host 0.0.0.0 --port $PORT --log-level info
```

### 3. 更新 EXPOSE 和 HEALTHCHECK

```dockerfile
# 暴露端口（Smithery 使用 8081）
EXPOSE 8081

# 健康检查（使用 PORT 环境变量）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8081}/health || exit 1
```

## 验证

### 本地测试（默认 8000）
```bash
$ docker build -t tushare-mcp .
$ docker run -p 8000:8081 tushare-mcp
# 服务器监听 8081（默认）
```

### Smithery 部署（自动 8081）
```bash
# Smithery 自动设置 PORT=8081
# 服务器监听 8081
# 扫描器连接 8081 ✅
```

## 关键点

1. **不要硬编码端口**: 必须使用 PORT 环境变量
2. **Smithery 默认端口**: 8081，不是 8000
3. **启动脚本**: 确保环境变量正确传递给 uvicorn
4. **健康检查**: 也要使用 PORT 环境变量

## 测试清单

- [x] Dockerfile 使用 PORT 环境变量
- [x] 创建 start.sh 启动脚本
- [x] 更新 EXPOSE 为 8081
- [x] 更新 HEALTHCHECK 使用 PORT
- [x] app_http.py 已经使用 PORT（无需修改）
- [ ] 本地 Docker 测试
- [ ] 推送到 GitHub
- [ ] Smithery 重新部署

## 参考

- Smithery Python Custom Container: https://smithery.ai/docs/cookbooks/python_custom_container
- Smithery Container Deployment: https://smithery.ai/docs/build/deployments/custom-container
