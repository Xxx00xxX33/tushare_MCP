# Tushare MCP Server

<div align="center">

基于 Model Context Protocol (MCP) 的智能股票数据助手

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Streamable%20HTTP-green)](https://modelcontextprotocol.io/)

</div>

## 🚀 快速开始

### Smithery 一键部署（推荐）

[![Deploy to Smithery](https://smithery.ai/badge)](https://smithery.ai/)

1. 点击上方按钮访问 Smithery
2. 连接此 GitHub 仓库
3. 配置 `TUSHARE_TOKEN` 环境变量
4. 点击部署，几分钟内即可使用

详细部署指南请查看 [DEPLOYMENT.md](./DEPLOYMENT.md)

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/Xxx00xxX33/tushare_MCP.git
cd tushare_MCP

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export TUSHARE_TOKEN="your_token_here"

# 启动服务器
python app_http.py
```

## 🎯 核心功能

### 1. 股票基础信息查询
- 支持通过股票代码（如：000001.SZ）精确查询
- 支持通过股票名称（如：平安银行）模糊查询
- 返回信息包含：
  - 股票代码和名称
  - 所属行业和地区
  - 上市日期
  - 市场类型
  - 交易状态

### 2. 智能股票搜索
- 支持模糊关键词搜索
- 同时匹配股票代码和名称
- 支持行业关键词搜索（如："新能源"、"科技"）
- 返回匹配度最高的股票列表

### 3. 财务报表分析
- 支持查询上市公司利润表数据
- 灵活的时间范围查询（年报、季报、半年报）
- 多种报表类型支持（合并报表、母公司报表等）
- 主要指标一目了然：
  - 每股收益
  - 营业收入和成本
  - 期间费用
  - 利润指标
- 支持历史数据对比分析

### 4. Token 状态管理
- 自动验证 Token 有效性
- 实时检查 API 连接状态
- 友好的错误提示

## 🛠️ 技术特点

### 传输协议
- **Streamable HTTP**: MCP 官方推荐的生产环境传输方式
- **无状态设计**: 支持水平扩展和负载均衡
- **标准化接口**: 完全兼容 MCP 协议规范

### 架构优势
- 基于 FastMCP 框架，开发效率高
- 使用 FastAPI 提供高性能 HTTP 服务
- 实时连接 Tushare Pro 数据源
- 智能错误处理和提示
- 支持并发请求处理

## 📦 部署方式

### 1. Smithery 云部署（推荐）

最简单的部署方式，无需管理服务器：

- ✅ 自动容器化
- ✅ 自动扩展
- ✅ 内置监控
- ✅ HTTPS 支持
- ✅ 一键更新

查看 [DEPLOYMENT.md](./DEPLOYMENT.md) 获取详细步骤

### 2. Docker 部署

```bash
# 构建镜像
docker build -t tushare-mcp .

# 运行容器
docker run -p 8000:8000 \
  -e TUSHARE_TOKEN=your_token_here \
  tushare-mcp
```

### 3. 传统部署

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app_http:app --host 0.0.0.0 --port 8000
```

## 🔑 获取 Tushare Token

1. 访问 [Tushare Pro](https://tushare.pro/register) 注册账号
2. 登录后访问 [Token 页面](https://tushare.pro/user/token)
3. 复制你的 API Token
4. 在部署时配置为环境变量

## 💡 使用场景

### 投资研究
```
"帮我查找所有新能源相关的股票"
"查询比亚迪的基本信息"
"获取平安银行2023年的利润表"
```

### 财务分析
```
"查看腾讯控股最新一期合并报表"
"对比阿里巴巴近三年的利润变化"
"分析小米集团的季度利润趋势"
```

### 行业分析
```
"列出所有医药行业的股票"
"查找深圳地区的科技公司"
```

## 📚 API 工具

### get_stock_basic_info
查询股票基础信息

**参数**:
- `ts_code` (可选): 股票代码，如 "000001.SZ"
- `name` (可选): 股票名称，如 "平安银行"
- `exchange` (可选): 交易所代码 (SSE/SZSE)
- `list_status` (可选): 上市状态 (L/D/P)

### search_stocks
搜索股票

**参数**:
- `keyword` (必填): 搜索关键词

### get_income_statement
获取利润表数据

**参数**:
- `ts_code` (必填): 股票代码
- `period` (可选): 报告期，格式 YYYYMMDD
- `limit` (可选): 返回记录数，默认 60

### check_token_status
检查 Token 状态

**参数**: 无

## 🔒 安全性

- Token 通过环境变量安全管理
- 不在代码中硬编码敏感信息
- 支持 HTTPS 加密传输
- 健康检查不暴露敏感数据

## 📖 文档

- [部署指南](./DEPLOYMENT.md) - 详细的部署步骤和配置说明
- [Tushare 文档](https://tushare.pro/document/2) - Tushare API 文档
- [MCP 协议](https://modelcontextprotocol.io/) - MCP 协议规范
- [FastMCP](https://gofastmcp.com/) - FastMCP 框架文档

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 开源协议

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Tushare Pro](https://tushare.pro/) - 提供优质的金融数据接口
- [FastMCP](https://github.com/jlowin/fastmcp) - 优秀的 MCP 框架
- [Smithery](https://smithery.ai/) - 便捷的 MCP 部署平台

## 📞 支持

如有问题或建议，请：
- 提交 [GitHub Issue](https://github.com/Xxx00xxX33/tushare_MCP/issues)
- 查看 [部署文档](./DEPLOYMENT.md)
- 访问 [Tushare 社区](https://tushare.pro/document/2)
