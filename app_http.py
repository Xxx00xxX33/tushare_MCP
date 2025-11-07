import os
import json
from typing import List, Dict

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

# ---------------------------
# 1) 初始化 Tushare（允许无 Token 启动；调用时再报 401）
# ---------------------------
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()
try:
    import tushare as ts
    if TUSHARE_TOKEN:
        ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
    try:
        pro.stock_basic(limit=1)  # 轻探针，不影响启动
        print("[init] Tushare probe OK")
    except Exception as e:
        print(f"[init] Tushare probe failed (won't block): {e}")
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
# 2) 定义 MCP 服务器（根路径提供 JSON-RPC + well-known）
# ---------------------------
mcp = FastMCP("tushare-mcp", stateless_http=True)

# 生成根路径下的 FastAPI 应用（JSON-RPC 默认挂载在 "/"）
app: FastAPI = mcp.streamable_http_app()

# --- MCP well-known（根路径，供扫描器读取 Test Config） ---
@app.get("/.well-known/mcp-config")
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

@app.get("/.well-known/mcp.json")
def well_known_mcp_json():
    # 告知客户端：使用 HTTP 传输，RPC 在根路径 "/"
    return {
        "name": "tushare-mcp",
        "version": "1.1.0",
        "transport": {"type": "http", "rpcPath": "/"},
        "endpoints": {"rpc": "/"}
    }

# --- 健康检查（根路径 GET） ---
@app.get("/")
def health_root():
    return {"status": "ok", "name": "tushare-mcp", "rpc": "/"}


# ---------------------------
# 3) 工具定义
# ---------------------------
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
    基于名称/行业/地区的关键词搜索。
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
