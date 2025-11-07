# Tushare MCP Server - Smithery 部署指南

## 概述

本项目是一个基于 Model Context Protocol (MCP) 的 Tushare 股票数据服务器，使用 Streamable HTTP 传输协议，可部署到 Smithery 平台。

## 架构说明

### 传输协议
- **协议类型**: Streamable HTTP (MCP 官方推荐的生产环境传输方式)
- **端口**: 8000 (可通过环境变量 PORT 配置)
- **端点**:
  - `/` - 服务信息
  - `/health` - 健康检查
  - `/mcp` - MCP 协议端点

### 工具列表

1. **get_stock_basic_info** - 查询股票基础信息
2. **search_stocks** - 搜索股票
3. **get_income_statement** - 获取利润表数据
4. **check_token_status** - 检查 Token 状态

## Smithery 部署步骤

### 1. 前置准备

获取 Tushare API Token:
1. 访问 [Tushare Pro](https://tushare.pro/register)
2. 注册并登录账号
3. 在 [Token 页面](https://tushare.pro/user/token) 获取 API Token

### 2. 部署到 Smithery

#### 方法 A: 通过 Smithery Web 界面

1. 登录 [Smithery](https://smithery.ai/)
2. 点击 "New Server" 或 "Deploy Server"
3. 连接你的 GitHub 仓库
4. 选择此项目仓库
5. Smithery 会自动检测 `smithery.yaml` 配置
6. 在配置页面输入你的 `TUSHARE_TOKEN`
7. 点击 "Deploy" 开始部署

#### 方法 B: 通过 GitHub 集成

1. 确保项目已推送到 GitHub
2. 在 Smithery 中添加 GitHub 集成
3. 授权 Smithery 访问你的仓库
4. Smithery 会自动触发部署

### 3. 配置环境变量

在 Smithery 部署配置中，需要设置以下环境变量：

```yaml
TUSHARE_TOKEN: "your_tushare_api_token_here"
```

### 4. 验证部署

部署成功后，可以通过以下方式验证：

1. 访问服务的健康检查端点: `https://your-deployment-url/health`
2. 在 Claude Desktop 或其他 MCP 客户端中连接服务
3. 测试调用 `check_token_status` 工具

## 本地开发和测试

### 安装依赖

```bash
pip install -r requirements.txt
```

### 设置环境变量

创建 `.env` 文件：

```bash
TUSHARE_TOKEN=your_token_here
```

### 启动服务器

```bash
# 方法 1: 直接运行
python app_http.py

# 方法 2: 使用 uvicorn
uvicorn app_http:app --host 0.0.0.0 --port 8000 --reload
```

### 测试端点

```bash
# 健康检查
curl http://localhost:8000/health

# 服务信息
curl http://localhost:8000/
```

## Docker 本地测试

### 构建镜像

```bash
docker build -t tushare-mcp .
```

### 运行容器

```bash
docker run -p 8000:8000 \
  -e TUSHARE_TOKEN=your_token_here \
  tushare-mcp
```

### 测试容器

```bash
curl http://localhost:8000/health
```

## 配置文件说明

### smithery.yaml

Smithery 平台的部署配置文件，定义了：
- 运行时类型 (container)
- Docker 构建配置
- 启动命令类型 (http)
- 配置 Schema (TUSHARE_TOKEN)

### Dockerfile

容器镜像构建文件，包含：
- Python 3.11 基础镜像
- 依赖安装
- 应用代码复制
- 健康检查配置
- 启动命令

### app_http.py

主应用文件，实现了：
- FastMCP 服务器初始化
- Streamable HTTP 传输
- MCP 工具定义
- 健康检查端点

## 故障排查

### Token 配置问题

**症状**: 工具调用返回 "TUSHARE_TOKEN not configured"

**解决方案**:
1. 确认在 Smithery 配置中正确设置了 TUSHARE_TOKEN
2. 检查 Token 格式是否正确（无空格、无引号）
3. 访问 `/health` 端点确认 `token_configured` 为 `true`

### API 调用失败

**症状**: 工具返回 "API call failed"

**解决方案**:
1. 使用 `check_token_status` 工具验证 Token 有效性
2. 检查 Tushare 账户积分是否充足
3. 确认网络连接正常

### 部署失败

**症状**: Smithery 部署过程中出错

**解决方案**:
1. 检查 `smithery.yaml` 格式是否正确
2. 确认 `Dockerfile` 可以本地成功构建
3. 查看 Smithery 部署日志获取详细错误信息

## 更新和维护

### 更新代码

1. 修改代码并提交到 GitHub
2. Smithery 会自动检测更新并触发重新部署
3. 或在 Smithery 界面手动触发部署

### 版本管理

在 `smithery.yaml` 和 `app_http.py` 中更新版本号：

```yaml
version: "1.2.0"
```

## 安全建议

1. **Token 保护**: 永远不要将 TUSHARE_TOKEN 硬编码在代码中
2. **环境隔离**: 使用 Smithery 的 secrets 管理功能
3. **访问控制**: 考虑添加认证中间件保护 API 端点
4. **日志审计**: 定期检查访问日志

## 支持和反馈

- Tushare 文档: https://tushare.pro/document/2
- MCP 协议文档: https://modelcontextprotocol.io/
- Smithery 文档: https://smithery.ai/docs
- FastMCP 文档: https://gofastmcp.com/

## 许可证

本项目遵循 MIT 许可证。
