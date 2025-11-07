"""
Tushare MCP Server - Streamable HTTP Transport
部署到 Smithery 的 HTTP MCP 服务器
"""
import os
import json
from typing import List, Dict

import pandas as pd
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

# ---------------------------
# 1) 初始化 Tushare
# ---------------------------
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()

try:
    import tushare as ts
    if TUSHARE_TOKEN:
        ts.set_token(TUSHARE_TOKEN)
        print(f"[init] Tushare token configured")
    else:
        print("[init] TUSHARE_TOKEN not set - tools will require configuration")
    
    pro = ts.pro_api()
    
    # 轻量级探针测试
    if TUSHARE_TOKEN:
        try:
            pro.stock_basic(limit=1)
            print("[init] Tushare API connection OK")
        except Exception as e:
            print(f"[init] Tushare API probe failed (non-blocking): {e}")
except Exception as e:
    print(f"[init] Tushare import failed: {e}")
    pro = None


def _ensure_token():
    """验证 Token 是否可用"""
    if pro is None:
        return False, {"error": "Tushare SDK not available"}
    if not TUSHARE_TOKEN:
        return False, {"error": "TUSHARE_TOKEN not configured"}
    return True, None


# ---------------------------
# 2) 创建 MCP 服务器（Streamable HTTP）
# ---------------------------
mcp = FastMCP("tushare-mcp", stateless_http=True)


# ---------------------------
# 3) MCP 工具定义
# ---------------------------
@mcp.tool()
def get_stock_basic_info(
    ts_code: str = "", 
    name: str = "", 
    exchange: str = "", 
    list_status: str = ""
) -> List[Dict]:
    """
    查询股票基础信息
    
    参数:
        ts_code: 股票代码（如：000001.SZ）- 精确匹配
        name: 股票名称（如：平安银行）- 模糊匹配
        exchange: 交易所代码 (SSE=上交所, SZSE=深交所)
        list_status: 上市状态 (L=上市, D=退市, P=暂停上市)
    
    返回:
        股票基础信息列表，包含代码、名称、行业、地区等信息
    """
    ok, error = _ensure_token()
    if not ok:
        return [error]
    
    try:
        df = pro.stock_basic(
            ts_code=ts_code or None,
            name=name or None,
            exchange=exchange or None,
            list_status=list_status or None,
            fields="ts_code,symbol,name,area,industry,market,list_date,fullname,enname,cnspell,list_status,exchange"
        )
        
        if df is None or df.empty:
            return []
        
        return json.loads(df.fillna("").to_json(orient="records"))
    except Exception as e:
        return [{"error": f"Query failed: {str(e)}"}]


@mcp.tool()
def search_stocks(keyword: str) -> List[Dict]:
    """
    搜索股票
    
    参数:
        keyword: 搜索关键词（可匹配代码、名称、行业、地区）
    
    返回:
        匹配的股票列表
    """
    ok, error = _ensure_token()
    if not ok:
        return [error]
    
    try:
        df = pro.stock_basic(
            fields="ts_code,symbol,name,area,industry,market,list_date"
        )
        
        if df is None or df.empty:
            return []
        
        kw = (keyword or "").strip().lower()
        if not kw:
            return []
        
        # 多字段模糊搜索
        mask = (
            df["ts_code"].astype(str).str.lower().str.contains(kw, na=False)
            | df["symbol"].astype(str).str.lower().str.contains(kw, na=False)
            | df["name"].astype(str).str.lower().str.contains(kw, na=False)
            | df["area"].astype(str).str.lower().str.contains(kw, na=False)
            | df["industry"].astype(str).str.lower().str.contains(kw, na=False)
            | df["market"].astype(str).str.lower().str.contains(kw, na=False)
        )
        
        results = df[mask]
        return json.loads(results.fillna("").to_json(orient="records"))
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


@mcp.tool()
def get_income_statement(
    ts_code: str, 
    period: str = "", 
    limit: int = 60
) -> List[Dict]:
    """
    获取上市公司利润表数据
    
    参数:
        ts_code: 股票代码（必填，如：000001.SZ）
        period: 报告期（可选，格式：YYYYMMDD，如：20231231）
        limit: 返回记录数量限制（默认60条）
    
    返回:
        利润表数据列表，包含营收、利润、费用等财务指标
    """
    ok, error = _ensure_token()
    if not ok:
        return [error]
    
    if not ts_code:
        return [{"error": "ts_code is required"}]
    
    try:
        df = pro.income(
            ts_code=ts_code, 
            period=period or None, 
            limit=limit
        )
        
        if df is None or df.empty:
            return []
        
        return json.loads(df.fillna("").to_json(orient="records"))
    except Exception as e:
        return [{"error": f"Query failed: {str(e)}"}]


@mcp.tool()
def check_token_status() -> Dict:
    """
    检查 Tushare Token 状态
    
    返回:
        Token 配置和连接状态信息
    """
    if pro is None:
        return {
            "ok": False, 
            "reason": "Tushare SDK not available"
        }
    
    if not TUSHARE_TOKEN:
        return {
            "ok": False, 
            "reason": "TUSHARE_TOKEN not configured"
        }
    
    try:
        # 测试 API 调用
        pro.stock_basic(limit=1)
        return {
            "ok": True,
            "message": "Token is valid and API is accessible"
        }
    except Exception as e:
        return {
            "ok": False, 
            "reason": f"API call failed: {str(e)}"
        }


# ---------------------------
# 4) 生成 Starlette 应用
# ---------------------------
app = mcp.streamable_http_app()

# 添加自定义路由
@app.route("/health", methods=["GET"])
async def health_check(request):
    """健康检查端点"""
    return JSONResponse({
        "status": "healthy",
        "service": "tushare-mcp",
        "version": "1.1.0",
        "token_configured": bool(TUSHARE_TOKEN)
    })

@app.route("/", methods=["GET"])
async def root(request):
    """根路径信息"""
    return JSONResponse({
        "name": "tushare-mcp",
        "version": "1.1.0",
        "description": "Tushare A-share data MCP server with Streamable HTTP transport",
        "transport": "streamable-http",
        "endpoints": {
            "health": "/health",
            "mcp": "/mcp"
        }
    })


# ---------------------------
# 5) 启动入口（用于本地测试）
# ---------------------------
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting Tushare MCP server on port {port}")
    print(f"Token configured: {bool(TUSHARE_TOKEN)}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
