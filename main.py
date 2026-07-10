from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pathlib import Path

# 导入你的 app（包含所有 API 路由）
from baw.goods import app

# ============ 挂载静态文件 ============
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ============ 根路径重定向 ============
@app.get("/")
async def root():
    return RedirectResponse(url="/static/login.html")

# ============ Vercel 入口 ============
# app 实例已存在

# ============ 本地开发 ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
