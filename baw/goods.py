import os
import pymysql
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse

app = FastAPI(title="商品管理系统")

# ===== 添加 CORS 中间件 =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Product(BaseModel):
    name: str = Field(min_length=1, max_length=10, description="商品名称")
    price: float = Field(gt=0, description="价格")
    stock: int = Field(ge=0, description="库存数量")


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=10, description="用户名")
    password: str = Field(min_length=1, max_length=11, description="密码")


# ===== 优化：从环境变量读取 TiDB 配置 =====
def get_db_config():
    """从环境变量获取数据库配置，本地开发时可使用 .env 文件"""
    return {
        "host": os.getenv("TIDB_HOST", "gateway01.ap-northeast-1.prod.aws.tidbcloud.com"),
        "port": int(os.getenv("TIDB_PORT", 4000)),
        "user": os.getenv("TIDB_USER", "ngp2NDw7ttNrg3T.root"),
        "password": os.getenv("TIDB_PASSWORD", ""),  # 密码必须从环境变量读取
        "database": os.getenv("TIDB_DATABASE", "fastapi"),
        "charset": "utf8mb4",
        "ssl": {"ca": os.getenv("TIDB_CA_PATH", "./ca.pem")} if os.getenv("TIDB_CA_PATH") else None
    }


def get_db_connection():
    """获取数据库连接"""
    config = get_db_config()
    # 如果 SSL 证书配置为 None，则移除该键，避免 pymysql 报错
    if config.get("ssl") is None:
        del config["ssl"]
    return pymysql.connect(**config)


def init_tidb():
    """初始化 TiDB 数据库：创建库和表（如果不存在）"""
    try:
        # 先获取一个不指定数据库的连接，用于创建数据库
        config = get_db_config()
        db_name = config.pop("database")  # 暂时移除 database，因为需要先创建库
        
        conn = pymysql.connect(**config)
        c = conn.cursor()
        
        # 创建数据库
        c.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        conn.commit()
        
        # 切换到目标数据库
        conn.select_db(db_name)
        
        # 创建用户表
        c.execute("""
            CREATE TABLE IF NOT EXISTS sys_user (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(255),
                password VARCHAR(255)
            )
        """)
        conn.commit()
        
        # 创建商品表
        c.execute("""
            CREATE TABLE IF NOT EXISTS product (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(20),
                price FLOAT,
                stock INT
            )
        """)
        conn.commit()
        
        c.close()
        conn.close()
        print("✅ TiDB 数据库初始化成功！")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")


# ===== API 路由 =====
@app.post("/auth/login")
def login(login_data: LoginRequest):
    try:
        conn = get_db_connection()
        c = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT id, username, password FROM sys_user WHERE username = %s AND password = %s"
        c.execute(sql, (login_data.username, login_data.password))
        user = c.fetchone()
        c.close()
        conn.close()
        
        if user:
            return {
                "success": True,
                "message": "登录成功",
                "user": {"id": user['id'], "username": user['username']}
            }
        else:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@app.post("/product/add")
def create_product(product: Product):
    conn = get_db_connection()
    c = conn.cursor()
    sql = "INSERT INTO product(name, price, stock) VALUES (%s, %s, %s)"
    c.execute(sql, (product.name, product.price, product.stock))
    conn.commit()
    id = c.lastrowid
    c.close()
    conn.close()
    return {"id": id, **product.dict()}


@app.get("/product/getall")
def get_all_products():
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM product"
    c.execute(sql)
    products = c.fetchall()
    c.close()
    conn.close()
    return products


@app.get("/product/get/{id}")
def get_product(id: int):
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM product WHERE id = %s"
    c.execute(sql, (id,))
    product = c.fetchone()
    c.close()
    conn.close()
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@app.put("/product/put/{id}")
def update_product(id: int, product: Product):
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM product WHERE id = %s"
    c.execute(sql, (id,))
    p = c.fetchone()
    if p is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    sql = "UPDATE product SET name = %s, price = %s, stock = %s WHERE id = %s"
    c.execute(sql, (product.name, product.price, product.stock, id))
    conn.commit()
    c.close()
    conn.close()
    return product


@app.delete("/product/delete/{id}")
def delete_product(id: int):
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM product WHERE id = %s"
    c.execute(sql, (id,))
    p = c.fetchone()
    if p is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    sql = "DELETE FROM product WHERE id = %s"
    c.execute(sql, (id,))
    conn.commit()
    c.close()
    conn.close()
    return {"message": "删除成功"}


# ===== 页面路由 =====
@app.get("/", response_class=HTMLResponse)
def root():
    with open("static/login.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/user/goods.html", response_class=HTMLResponse)
def goods_page():
    with open("static/goods.html", "r", encoding="utf-8") as f:
        return f.read()


# ===== 启动入口 =====
if __name__ == '__main__':
    # 初始化数据库（仅本地运行时执行）
    init_tidb()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
