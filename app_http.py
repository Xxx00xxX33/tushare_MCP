import os
import json
import pandas as pd
from typing import List, Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

# ---------------------------
# 1) 初始化 Tushare
# ---------------------------
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()
try:
    import tushare as ts
    if TUSHARE_TOKEN:
        ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
except Exception as e:
    print("[init] tushare import failed:", e)
    pro = None


def _ensure_token():
    if pro is None:
        return False, JSONResponse(status_code=500, content={"error": "tushare SDK not available"})
    if not TUSHARE_TOKEN:
        return False, JSONResponse(status_code=401, content={"error": "Unauthorized: missing TUSHARE_TOKEN"})
    return True, None


# ---------------------------
# 2) 定义 MCP 服务器（工具）
# ---------------------------
mcp = FastMCP("tushare-mcp")

@mcp.tool()
def get_stock_basic_info(ts_code: str = "", name: str = "", exchange: str = "", list_status: str = "") -> List[Dict]:
    """
    查询股票基础信息。
    - ts_code: TS代码（精确）
    - name: 名称（模糊）
    - exchange: 交易所 (SSE/SZSE)
    - list_status: 上市状态 L/D/P
    """
    ok, resp = _ensure_token()
    if not ok:
        return resp
    df = pro.stock_basic(
        ts_code=ts_code or None,
        name=name or None,
        exchange=exchange or None,
        list_status=list_status or None,
        fields="ts_code,symbol,name,area,industry,market,list_date,fullname,enname,cnspell,list_status,exchange"
    )
    return json.loads(df.fillna("").to_json(orient="records"))

@mcp.tool()
def search_stocks(keyword: str) -> List[Dict]:
    """
    基于名称/行业/地区的关键词搜索（极简召回）。
    """
    ok, resp = _ensure_token()
    if not ok:
        return resp
    df = pro.stock_basic(fields="ts_code,symbol,name,area,industry,market,list_date")
    if df is None or df.empty:
        return []
    kw = (keyword or "").strip().lower()
    if not kw:
        return []
    mask = (
        df["ts_code"].astype(str).str.lower().str.contains(kw)
        | df["symbol"].astype(str).str.lower().str.contains(kw)
        | df["name"].astype(str).str.lower().str.contains(kw)
        | df["area"].astype(str).str.lower().str.contains(kw)
        | df["industry"].astype(str).str.lower().str.contains(kw)
        | df["market"].astype(str).str.lower().str.contains(kw)
    )
    return json.loads(df[mask].fillna("").to_json(orient="records"))

@mcp.tool()
def get_income_statement(ts_code: str, period: str = "", limit: int = 60) -> List[Dict]:
    """
    拉取利润表（income），可指定 period（如 20231231）或使用 limit 条数。
    """
    ok, resp = _ensure_token()
    if not ok:
        return resp
    df = pro.income(ts_code=ts_code, period=period or None, limit=limit)
    if df is None or df.empty:
        return []
    return json.loads(df.fillna("").to_json(orient="records"))

@mcp.tool()
def check_token_status() -> Dict:
    """
    探针：验证 Token 是否可用
    """
    if pro is None:
        return {"ok": False, "reason": "tushare SDK not available"}
    if not TUSHARE_TOKEN:
        return {"ok": False, "reason": "missing TUSHARE_TOKEN"}
    try:
        pro.stock_basic(limit=1)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


# ---------------------------
# 3) 生成 MCP 的 ASGI 子应用，并把 /.well-known 也放进去
# ---------------------------
# 关键：把 MCP 子应用放到 path="/mcp"，此子应用中自带 JSON-RPC (POST /mcp)
#      同时在“同一个子应用”里提供 .well-known，确保 scanner 以 /mcp 为前缀访问时能命中
mcp_app = mcp.http_app(path="/mcp")

# 在同一“子应用”中暴露 .well-known（注意：这里注册在 mcp_app 上）
@mcp_app.get("/.well-known/mcp-config")
def well_known_mcp_config():
    return {
        "configSchema": {
            "type": "object",
            "properties": {
                "TUSHARE_TOKEN": {"type": "string", "description": "Tushare API Token"}
            },
            "required": ["TUSHARE_TOKEN"]
        },
        "exampleConfig": {"TUSHARE_TOKEN": "your_token_here"}
    }

@mcp_app.get("/.well-known/mcp.json")
def well_known_mcp_json():
    # 提示客户端：JSON-RPC 入口以及使用的传输
    return {
        "name": "tushare-mcp",
        "version": "1.0.1",
        "transport": {"type": "http", "rpcPath": "/mcp"},
        "endpoints": {"rpc": "/mcp"}
    }

# ---------------------------
# 4) 导出最终应用：仅包含 MCP 子应用的所有路由
#    这样最终可访问：
#      - POST /mcp           ← JSON-RPC initialize 等
#      - GET  /mcp/.well-known/mcp-config
# ---------------------------
app = FastAPI(routes=[*mcp_app.routes], lifespan=mcp_app.lifespan)

# 可选健康检查（挂在 /mcp/health，仍然在同一前缀内）
@app.get("/mcp/health")
def health():
    return {"status": "ok", "name": "tushare-mcp", "version": "1.0.1"}
