import os
import json
from typing import Optional

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

# ---------------------------
# 1) 初始化 Tushare token
# ---------------------------
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "").strip()
try:
    import tushare as ts
    if TUSHARE_TOKEN:
        ts.set_token(TUSHARE_TOKEN)
        _pro = ts.pro_api()
        try:
            # 轻探针，避免启动报错阻塞扫描
            _pro.stock_basic(limit=1)
            print("[init] Tushare token OK")
        except Exception as e:
            print(f"[init] token set, probe failed (won't block): {e}")
    else:
        _pro = ts.pro_api()  # 允许无 token 启动（调用时再报 401）
        print("[init] TUSHARE_TOKEN not set; tools will return 401 if needed")
except Exception as e:
    # 不阻断启动；工具调用时再抛出清晰错误
    _pro = None
    print(f"[init] tushare import failed: {e}")


def _ensure_token():
    """在工具调用时确保存在有效 token；否则返回 (False, JSONResponse)"""
    if _pro is None:
        return False, JSONResponse(status_code=500, content={"error": "tushare SDK not available"})
    if not TUSHARE_TOKEN:
        return False, JSONResponse(status_code=401, content={"error": "Unauthorized: missing TUSHARE_TOKEN"})
    return True, None


# ---------------------------
# 2) 定义 MCP（HTTP）
# ---------------------------
mcp = FastMCP("tushare-mcp", stateless_http=True)

# ========== 工具 1：个股基础信息 ==========
@mcp.tool()
def get_stock_basic_info(
    ts_code: str = "",
    name: str = "",
    exchange: str = "",
    list_status: str = "",
) -> list[dict]:
    """
    查询股票基础信息（模糊或精确）。
    - ts_code: TS代码（优先）
    - name: 名称（可模糊）
    - exchange: 交易所 (SSE/SHSE/SH，SZSE/SZ)
    - list_status: L上市状态 (L/D/P)
    """
    ok, resp = _ensure_token()
    if not ok:
        return resp  # MCP 将自动封装为错误

    df = _pro.stock_basic(
        ts_code=ts_code or None,
        name=name or None,
        exchange=exchange or None,
        list_status=list_status or None,
        fields="ts_code,symbol,name,area,industry,market,list_date,fullname,enname,cnspell,list_status,exchange"
    )
    return json.loads(df.fillna("").to_json(orient="records"))

# ========== 工具 2：关键词搜索（名称/行业/地区） ==========
@mcp.tool()
def search_stocks(keyword: str) -> list[dict]:
    """
    基于名称/行业/地区的关键词搜索（极简召回）。
    """
    ok, resp = _ensure_token()
    if not ok:
        return resp

    df = _pro.stock_basic(
        fields="ts_code,symbol,name,area,industry,market,list_date"
    )
    if df is None or df.empty:
        return []

    kw = (keyword or "").strip().lower()
    if not kw:
        return []

    def _match(row) -> bool:
        for col in ("ts_code", "symbol", "name", "area", "industry", "market"):
            v = str(row.get(col, "")).lower()
            if kw in v:
                return True
        return False

    recs = [r for _, r in df.fillna("").iterrows() if _match(r)]
    return json.loads(pd.DataFrame(recs).to_json(orient="records"))

# ========== 工具 3：利润表（合并/母公司；时间区间） ==========
@mcp.tool()
def get_income_statement(
    ts_code: str,
    start_date: str = "",
    end_date: str = "",
    report_type: str = "1",  # 1合并 2单季 3母公司 4合并调整后 5母公司调整后
    period: str = "",        # 指定会计期（如 20231231）；与 start/end 二选一
    limit: int = 60
) -> list[dict]:
    """
    拉取利润表（income），支持区间或单期。
    - ts_code: 必填
    - start_date/end_date: YYYYMMDD
    - report_type: 1=合并 3=母公司
    - period: 指定单期
    - limit: 最大返回条数
    """
    ok, resp = _ensure_token()
    if not ok:
        return resp

    kw = dict(ts_code=ts_code, report_type=report_type)
    if period:
        kw["period"] = period
    else:
        if start_date:
            kw["start_date"] = start_date
        if end_date:
            kw["end_date"] = end_date

    df = _pro.income(**kw, limit=limit)
    if df is None or df.empty:
        return []
    return json.loads(df.fillna("").to_json(orient="records"))

# ========== 工具 4：检查 Token ==========
@mcp.tool()
def check_token_status() -> dict:
    """
    返回当前 Token 是否可用（对 stock_basic 做 1 条探针）。
    """
    if _pro is None:
        return {"ok": False, "reason": "tushare SDK not available"}
    if not TUSHARE_TOKEN:
        return {"ok": False, "reason": "missing TUSHARE_TOKEN"}

    try:
        _pro.stock_basic(limit=1)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "reason": str(e)}

# 生成符合 MCP-HTTP 的 FastAPI 应用（自带 JSON-RPC 与能力枚举）
app: FastAPI = mcp.streamable_http_app()


# ---------------------------
# 3) 兼容 Smithery 的 well-known 配置
# ---------------------------
# 某些扫描器会请求 /.well-known/mcp-config 以获得“测试会话配置”/动态参数；
# 这里返回一个最小可用对象（无需动态参数），避免 404 导致扫描中断。
@app.get("/.well-known/mcp-config")
def well_known_mcp_config():
    return {
        "schema": {"type": "object", "properties": {}},
        "example": {},
        # 可声明鉴权模式（这里不强制 OAuth，使用上游提供的测试环境变量）
        "authorization": {"type": "none"}
    }

# 兼容有的实现会请求 JSON 后缀的写法
@app.get("/.well-known/mcp.json")
def well_known_mcp_json():
    return {
        "name": "tushare-mcp",
        "version": "0.3.0",
        "endpoints": {
            # FastMCP 的 JSON-RPC 路径（内部约定），扫描器会通过 / 调用 initialize
            "rpc": "/",
        }
    }

# 可选：根路径健康检查（Smithery startCommand.path 会拿它做“唤醒/探测”）
@app.get("/")
def root():
    return {"status": "ok", "name": "tushare-mcp", "transport": "http"}
