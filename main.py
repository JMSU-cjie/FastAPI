from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pathlib import Path
from pydantic import BaseModel, Field

# ============ 导入商品模块 ============
from baw.goods import init_db, get_all_products, get_product_by_id, create_product, update_product, delete_product

# ============ Pydantic 模型 ============
class Product(BaseModel):
    name: str = Field(min_length=1, max_length=10, description="商品名称")
    price: float = Field(gt=0, description="价格")
    stock: int = Field(ge=0, description="库存数量")

# ============ 创建 FastAPI 应用 ============
app = FastAPI(title="点餐系统")

# ============ 挂载静态文件 ============
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ============ 商品路由 ============
@app.post("/product/add")
def add_product(product: Product):
    """添加商品"""
    return create_product(product.name, product.price, product.stock)

@app.get("/product/getall")
def get_all():
    """获取所有商品"""
    return get_all_products()

@app.get("/product/get/{product_id}")
def get_product(product_id: int):
    """根据ID获取商品"""
    product = get_product_by_id(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product

@app.put("/product/put/{product_id}")
def update_product_info(product_id: int, product: Product):
    """更新商品信息"""
    success = update_product(product_id, product.name, product.price, product.stock)
    if not success:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product

@app.delete("/product/delete/{product_id}")
def delete_product_info(product_id: int):
    """删除商品"""
    success = delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {"message": "删除成功"}

# ============ 根路由 ============
@app.get("/")
async def root():
    """根路径重定向到登录页面"""
    return RedirectResponse(url="/static/login.html")

# ============ 本地开发 ============
if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
