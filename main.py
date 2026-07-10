from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
import os
from pathlib import Path

from baw.goods import app  # 只导入 app，不导入 init_db

# ============ 挂载静态文件 ============
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    print(f"✅ Static files mounted from: {STATIC_DIR}")
else:
    print(f"⚠️ Static directory not found at: {STATIC_DIR}")

# ============ 路由 ============
@app.get("/")
async def root():
    """根路径重定向到登录页面"""
    return RedirectResponse(url="/static/login.html")

# ============ Vercel 入口 ============
# app 实例已存在，Vercel 会自动识别

# ============ 本地开发 ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
