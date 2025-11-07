import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import tushare as ts

# -------- init token from env --------
token = os.getenv("TUSHARE_TOKEN", "").strip()
if token:
    ts.set_token(token)

pro = ts.pro_api()

app = FastAPI()

@app.get("/")
def root():
    return {"msg": "Tushare MCP HTTP server running."}

@app.post("/tools/get_stock_basic_info")
async def get_stock_basic_info(request: Request):
    body = await request.json()
    ts_code = body.get("ts_code", "")
    name = body.get("name", "")

    if not token:
        return JSONResponse(status_code=401, content={"error": "Missing TUSHARE_TOKEN"})

    df = pro.stock_basic(ts_code=ts_code, name=name)
    return json.loads(df.to_json(orient="records"))
