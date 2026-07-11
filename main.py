"""
main.py - 应用主入口
只负责：路由管理、静态文件挂载、应用配置
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse
from pathlib import Path

# ============ 创建应用 ============
app = FastAPI(
    title="点餐系统",
    description="美味点餐系统",
    version="1.0.0"
)

# ============ CORS 配置 ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ 挂载静态文件 ============
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount(
        "/static", 
        StaticFiles(directory=str(STATIC_DIR), html=True), 
        name="static"
    )
    print(f"✅ 静态文件目录已挂载: {STATIC_DIR}")
else:
    print(f"⚠️  静态文件目录不存在: {STATIC_DIR}")

# ============ 页面路由 ============

@app.get("/")
async def root():
    """根路径 → 登录页面"""
    return RedirectResponse(url="/static/login.html")

@app.get("/login")
async def login_page():
    """登录页面"""
    return RedirectResponse(url="/static/login.html")

@app.get("/index")
async def index_page():
    """首页"""
    return RedirectResponse(url="/static/index.html")

@app.get("/goods")
async def goods_page():
    """商品管理页面"""
    return RedirectResponse(url="/static/goods.html")

# ============ 健康检查 ============

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "点餐系统",
        "version": "1.0.0"
    }

# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 50)
    print("🍜 点餐系统启动中...")
    print(f"📁 静态文件目录: {STATIC_DIR}")
    print(f"🌐 访问地址: http://localhost:8080")
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
        reload=True
    )
