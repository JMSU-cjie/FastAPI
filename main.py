from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pathlib import Path

# ============ 创建 FastAPI 应用 ============
app = FastAPI(title="点餐系统")

# ============ 挂载静态文件 ============
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ============ 路由 ============
@app.get("/")
async def root():
    """根路径重定向到登录页面"""
    return RedirectResponse(url="/static/login.html")

# ============ 本地开发 ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
