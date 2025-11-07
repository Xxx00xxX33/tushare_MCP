# Smithery 部署修复说明

## 修复日期
2025-11-08

## 问题描述

Smithery 扫描器无法连接到 MCP 端点，报错：
```
Failed to fetch .well-known/mcp-config
HTTP POST → undefined (10003ms)
Request: {"method":"initialize",...}
HTTP error: This operation was aborted
```

## 根本原因

1. **使用了错误的 FastMCP API**
   - 错误：使用 `mcp.streamable_http_app()` 
   - 正确：应该使用 `mcp.http_app()`

2. **缺少必要的依赖**
   - 缺少 `fastmcp` 包
   - 缺少 `websockets` 包
   - 缺少 `wsproto` 包

3. **启动方式不正确**
   - 使用 `mcp.run()` 会导致 WebSocket 协议错误
   - 应该使用标准的 uvicorn 启动 ASGI 应用

## 解决方案

### 1. 修改 app_http.py

**关键更改**:
```python
# 创建 ASGI 应用（正确方式）
app = mcp.http_app()

# 使用 uvicorn 启动
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
```

**自定义路由**:
```python
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy"})
```

### 2. 更新 requirements.txt

添加必要的依赖：
```
fastmcp>=2.0.0
websockets>=12.0
wsproto>=1.2.0
```

### 3. 测试结果

所有端点测试通过：

**健康检查**:
```bash
$ curl http://localhost:8000/health
{"status":"healthy","service":"tushare-mcp","version":"1.2.0","token_configured":false,"mcp_endpoint":"/mcp"}
```

**MCP 端点**:
```bash
$ curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",...}'

event: message
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05",...}}
```

## 技术细节

### FastMCP HTTP 部署的正确方式

**用于 ASGI 部署（推荐）**:
```python
from fastmcp import FastMCP

mcp = FastMCP("server-name")

# 添加工具
@mcp.tool()
def my_tool():
    pass

# 添加自定义路由
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy"})

# 创建 ASGI 应用
app = mcp.http_app()

# 使用 uvicorn 运行
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### MCP Streamable HTTP 协议

- **端点路径**: `/mcp`
- **协议**: Server-Sent Events (SSE)
- **Content-Type**: `application/json`
- **Accept**: `application/json, text/event-stream`
- **响应格式**: SSE 事件流

### 为什么不能使用 mcp.run()?

`mcp.run()` 方法会：
1. 创建自己的事件循环
2. 使用 FastMCP 的内部 uvicorn 配置
3. 可能导致 WebSocket 协议不匹配错误

使用 `mcp.http_app()` + `uvicorn.run()` 可以：
1. 完全控制 uvicorn 配置
2. 避免 WebSocket 协议问题
3. 更好地与 ASGI 服务器集成

## 部署验证

### 本地测试通过
- ✅ 服务器成功启动
- ✅ `/health` 端点正常
- ✅ `/` 根路径端点正常
- ✅ `/mcp` MCP 协议端点正常
- ✅ initialize 请求正确响应
- ✅ SSE 格式响应正确

### Smithery 部署检查清单
- [x] app_http.py 使用正确的 API
- [x] requirements.txt 包含所有依赖
- [x] Dockerfile 配置正确
- [x] smithery.yaml 配置正确
- [x] 本地测试通过

## 下一步

1. ✅ 修改代码
2. ✅ 更新依赖
3. ✅ 本地测试
4. ⏳ 推送到 GitHub
5. ⏳ 在 Smithery 重新部署
6. ⏳ 验证部署成功

## 参考资源

- FastMCP 文档: https://gofastmcp.com/deployment/running-server
- FastMCP GitHub: https://github.com/jlowin/fastmcp
- MCP 协议规范: https://modelcontextprotocol.io/
- Smithery 文档: https://smithery.ai/docs
