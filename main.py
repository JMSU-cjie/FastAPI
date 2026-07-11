from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pathlib import Path
import os
import sys

# ============ 打印调试信息 ============
print(f"✅ Python 版本: {sys.version}")
print(f"✅ 当前工作目录: {os.getcwd()}")
print(f"✅ 目录内容: {os.listdir('.')}")

# ============ 尝试导入 app ============
try:
    from baw.goods import app
    print("✅ 成功从 baw.goods 导入 app")
except Exception as e:
    print(f"❌ 导入 baw.goods 失败: {e}")
    import traceback
    traceback.print_exc()
    # 如果导入失败，创建一个临时 app 用于调试
    from fastapi import FastAPI
    app = FastAPI(title="点餐系统（调试模式）")
    
    @app.get("/")
    async def root():
        return {"error": "导入 baw.goods 失败", "detail": str(e)}
    
    @app.get("/debug")
    async def debug():
        return {
            "error": str(e),
            "cwd": os.getcwd(),
            "files": os.listdir('.'),
            "python_path": sys.path
        }

# ============ 挂载静态文件 ============
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    try:
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
        print(f"✅ 静态文件挂载成功: {STATIC_DIR}")
    except Exception as e:
        print(f"❌ 静态文件挂载失败: {e}")
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

# ============ 打印所有已注册路由（调试用） ============
print("📋 已注册的路由:")
for route in app.routes:
    print(f"  {route.methods if hasattr(route, 'methods') else 'ANY'} {route.path}")

# ============ Vercel 入口 ============
# app 实例已从 baw.goods 导入

# ============ 本地开发 ============
if __name__ == "__main__":
    import uvicorn
    print(f"🚀 启动服务器: http://localhost:8080")
    print(f"📁 静态目录: {STATIC_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
