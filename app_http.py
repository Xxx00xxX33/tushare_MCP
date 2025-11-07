import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
import pandas as pd

# ---------- Load Tushare Token ----------
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()

try:
    import tushare as ts
    if TUSHARE_TOKEN:
        ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()
except Exception as e:
    print("[init] tushare failed:", e)
    pro = None


def ensure_token():
    if pro is None:
        return False, JSONResponse(status_code=500, content={"error": "tushare not available"})
    if not TUSHARE_TOKEN:
        return False, JSONResponse(status_code=401, content={"error": "missing TUSHARE_TOKEN"})
    return True, None


# ---------- MCP Server ----------
mcp = FastMCP("tushare-mcp", stateless_http=True)

@app := mcp.app  # FastAPI 实例，可增加 http 路由


# ---------- tools ----------
@mcp.tool()
def get_stock_basic_info(ts_code: str = "", name: str = "") -> list[dict]:
    ok, resp = ensure_token()
    if not ok:
        return resp

    df = pro.stock_basic(ts_code=ts_code or None, name=name or None)
    return json.loads(df.fillna("").to_json(orient="records"))


@mcp.tool()
def search_stocks(keyword: str) -> list[dict]:
    ok, resp = ensure_token()
    if not ok:
        return resp

    df = pro.stock_basic()
    if df is None or df.empty:
        return []
    keyword = keyword.lower()
    result = df[df.apply(lambda r: keyword in str(r).lower(), axis=1)]
    return json.loads(result.fillna("").to_json(orient="records"))


@mcp.tool()
def get_income_statement(ts_code: str, period: str = "", limit: int = 10) -> list[dict]:
    ok, resp = ensure_token()
    if not ok:
        return resp

    df = pro.income(ts_code=ts_code, period=period or None, limit=limit)
    return json.loads(df.fillna("").to_json(orient="records"))


@mcp.tool()
def check_token_status() -> dict:
    if not TUSHARE_TOKEN:
        return {"ok": False, "reason": "missing TUSHARE_TOKEN"}
    try:
        pro.stock_basic(limit=1)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


# ---------- MCP routing ----------
# MCP JSON-RPC endpoint
@app.post("/mcp")  # ✅ 关键：scanner 会 POST /mcp initialize
async def mcp_rpc(request: Request):
    return await mcp.rpc(request)


# required by Smithery
@app.get("/.well-known/mcp-config")
def well_known():
    return {"configSchema": {"type": "object"}, "example": {}}

@app.get("/")
def root():
    return {"status": "ok", "name": "tushare-mcp"}
