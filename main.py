from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pathlib import Path
import os

# ============ 导入包含所有 API 路由的 app ============
# 这样 main.py 作为入口，执行时会先加载 baw.goods，
# 然后获得已包含所有路由的 app 实例
from baw.goods import app

# ============ 挂载静态文件 ============
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    print(f"✅ 静态文件挂载成功: {STATIC_DIR}")
else:
    print(f"⚠️ 静态目录不存在: {STATIC_DIR}")

# ============ 根路径重定向 ============
@app.get("/")
async def root():
    """根路径重定向到登录页面"""
    return RedirectResponse(url="/static/login.html")

# ============ 健康检查 ============
@app.get("/health")
async def health():
    """健康检查"""
    return {
        "status": "ok",
        "static_dir": str(STATIC_DIR),
        "static_exists": STATIC_DIR.exists(),
        "vercel": bool(os.getenv("VERCEL"))
    }

# ============ Vercel 入口 ============
# app 实例已从 baw.goods 导入，所有路由都已包含

# ============ 本地开发 ============
if __name__ == "__main__":
    import uvicorn
    print(f"🚀 启动服务器: http://localhost:8080")
    print(f"📁 静态目录: {STATIC_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
