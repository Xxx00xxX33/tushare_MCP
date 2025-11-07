import os
import json
from typing import List, Dict

import pandas as pd
from fastapi import FastAPI, Request
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
    # 轻探针，不抛异常阻断启动
    try:
        pro.stock_basic(limit=1)
        print("[init] Tushare token OK")
    except Exception as e:
        print(f"[init] token set, probe failed (won't block): {e}")
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
# 2) 定义 MCP 服务器与工具
# ---------------------------
mcp = FastMCP("tushare-mcp", stateless_http=True)

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
# 3) FastAPI 应用与路由（关键修正）
# ---------------------------
app = FastAPI()

# 3.1 MCP JSON-RPC 端点固定在 /mcp
@app.post("/mcp")
async def mcp_rpc(request: Request):
    # 直接把请求交给 FastMCP 的 RPC 处理
    return await mcp.rpc(request)

# 3.2 在 /mcp/.well-known/* 返回测试配置（扫描器会按 path 前缀来找）
@app.get("/mcp/.well-known/mcp-config")
def well_known_scoped():
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

# 3.3 兼容某些实现会在根路径找 .well-known（双投放，避免 404）
@app.get("/.well-known/mcp-config")
def well_known_root():
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

# 3.4 健康检查（Smithery 唤醒用）
@app.get("/")
def health_root():
    return {"status": "ok", "name": "tushare-mcp", "rpc": "/mcp"}

# 3.5 可选：在 /mcp/health 下也给一个
@app.get("/mcp/health")
def health_scoped():
    return {"status": "ok", "name": "tushare-mcp", "version": "1.0.2"}
