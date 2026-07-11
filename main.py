from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
import os
import logging
from pydantic import BaseModel, Field

# ============ 导入商品模块 ============
from baw.goods import init_db, get_all_products, get_product_by_id, create_product, update_product, delete_product

# ============ 配置日志 ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ Pydantic 模型 ============
class Product(BaseModel):
    name: str = Field(min_length=1, max_length=10, description="商品名称")
    price: float = Field(gt=0, description="价格")
    stock: int = Field(ge=0, description="库存数量")

# ============ 创建 FastAPI 应用 ============
app = FastAPI(title="点餐系统")

# ============ 静态文件配置 ============
# 获取当前文件所在目录（项目根目录）
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

logger.info(f"项目根目录: {BASE_DIR}")
logger.info(f"静态文件目录: {STATIC_DIR}")
logger.info(f"静态目录是否存在: {STATIC_DIR.exists()}")

# 检查静态目录和文件
if STATIC_DIR.exists():
    static_files = list(STATIC_DIR.iterdir())
    logger.info(f"静态目录中的文件: {[f.name for f in static_files]}")
    
    # 检查 login.html 是否存在
    login_html = STATIC_DIR / "login.html"
    if not login_html.exists():
        logger.warning(f"login.html 不存在: {login_html}")
else:
    logger.error(f"静态目录不存在: {STATIC_DIR}")
    # 尝试创建静态目录
    try:
        STATIC_DIR.mkdir(exist_ok=True)
        logger.info(f"已创建静态目录: {STATIC_DIR}")
    except Exception as e:
        logger.error(f"创建静态目录失败: {e}")

# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ============ 根路由 ============
@app.get("/")
async def root():
    """根路径重定向到登录页面"""
    try:
        return RedirectResponse(url="/static/login.html")
    except Exception as e:
        logger.error(f"根路径重定向失败: {e}")
        return HTMLResponse(content=f"""
            <h1>500 - 服务器错误</h1>
            <p>错误信息: {str(e)}</p>
            <p>静态文件目录: {STATIC_DIR}</p>
            <p>login.html 是否存在: {(STATIC_DIR / 'login.html').exists()}</p>
        """, status_code=500)

# ============ 商品路由 ============
@app.post("/product/add")
def add_product(product: Product):
    """添加商品"""
    try:
        return create_product(product.name, product.price, product.stock)
    except Exception as e:
        logger.error(f"添加商品失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加商品失败: {str(e)}")

@app.get("/product/getall")
def get_all():
    """获取所有商品"""
    try:
        return get_all_products()
    except Exception as e:
        logger.error(f"获取商品列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取商品列表失败: {str(e)}")

@app.get("/product/get/{product_id}")
def get_product(product_id: int):
    """根据ID获取商品"""
    try:
        product = get_product_by_id(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="商品不存在")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取商品失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取商品失败: {str(e)}")

@app.put("/product/put/{product_id}")
def update_product_info(product_id: int, product: Product):
    """更新商品信息"""
    try:
        success = update_product(product_id, product.name, product.price, product.stock)
        if not success:
            raise HTTPException(status_code=404, detail="商品不存在")
        return product
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新商品失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新商品失败: {str(e)}")

@app.delete("/product/delete/{product_id}")
def delete_product_info(product_id: int):
    """删除商品"""
    try:
        success = delete_product(product_id)
        if not success:
            raise HTTPException(status_code=404, detail="商品不存在")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除商品失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除商品失败: {str(e)}")

# ============ 健康检查 ============
@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "ok",
        "base_dir": str(BASE_DIR),
        "static_dir": str(STATIC_DIR),
        "static_exists": STATIC_DIR.exists(),
        "login_html_exists": (STATIC_DIR / "login.html").exists()
    }

# ============ 本地开发 ============
if __name__ == "__main__":
    # 初始化数据库
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
