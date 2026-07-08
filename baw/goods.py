import pymysql
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse
import os

app = FastAPI(title="商品管理系统")

# ===== 添加 CORS 中间件 =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)


class Product(BaseModel):
    name: str = Field(min_length=1, max_length=10, description="商品名称")
    price: float = Field(gt=0, description="价格")
    stock: int = Field(ge=0, description="库存数量")


# ===== 新增：登录请求模型 =====
class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=10, description="用户名")
    password: str = Field(min_length=1, max_length=11, description="密码")


TIDB_CONFIG = {
    "host": "gateway01.ap-northeast-1.prod.aws.tidbcloud.com",
    "port": 4000,
    "user": "ngp2NDw7ttNrg3T.root",
    "password": "I9HGgYJjVVEJtfPk",
    "charset": "utf8mb4"
}


def init_tidb():
    try:
        conn = pymysql.connect(**TIDB_CONFIG)
        c = conn.cursor()
        # 创建数据库
        c.execute("CREATE DATABASE IF NOT EXISTS fastapi")
        conn.commit()
        # 切换到 fastapi
        conn.select_db("fastapi")
        # 创建表
        c.execute("""
            CREATE TABLE IF NOT EXISTS sys_user (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(255),
                password VARCHAR(255)
            )
        """)
        conn.commit()
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
        print("TiDB 数据库初始化成功！")
    except Exception as e:
        print(f"初始化失败: {e}")


# ===== 新增：登录验证接口 =====
@app.post("/auth/login")
def login(login_data: LoginRequest):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)

        # 查询用户
        sql = "SELECT id, username, password FROM sys_user WHERE username = %s AND password = %s"
        c.execute(sql, (login_data.username, login_data.password))
        user = c.fetchone()

        c.close()
        conn.close()

        if user:
            return {
                "success": True,
                "message": "登录成功",
                "user": {
                    "id": user['id'],
                    "username": user['username']
                }
            }
        else:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@app.post("/product/add")
def create_product(product: Product):
    conn = pymysql.connect(**DB_CONFIG)
    c = conn.cursor()
    sql = "insert into product(name, price, stock) values (%s, %s, %s)"
    c.execute(sql, (product.name, product.price, product.stock))
    conn.commit()
    id = c.lastrowid
    c.close()
    conn.close()
    return {"id": id, **product.dict()}


@app.get("/product/getall")
def get_all_products():
    conn = pymysql.connect(**DB_CONFIG)
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "select * from product"
    c.execute(sql)
    products = c.fetchall()
    c.close()
    conn.close()
    print(products)
    return products


@app.get("/product/get/{id}")
def get_product(id: int):
    conn = pymysql.connect(**DB_CONFIG)
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "select * from product where id = %s"
    c.execute(sql, (id,))
    product = c.fetchone()
    c.close()
    conn.close()
    if product is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    else:
        return product


@app.put("/product/put/{id}")
def update_product(id: int, product: Product):
    conn = pymysql.connect(**DB_CONFIG)
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "select * from product where id = %s"
    c.execute(sql, (id,))
    p = c.fetchone()
    if p is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    else:
        sql = "update product set name = %s, price = %s, stock = %s where id = %s"
        c.execute(sql, (product.name, product.price, product.stock, id))
        conn.commit()
        c.close()
        conn.close()
        return product


@app.delete("/product/delete/{id}")
def update_product(id: int):
    conn = pymysql.connect(**DB_CONFIG)
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "select * from product where id = %s"
    c.execute(sql, (id,))
    p = c.fetchone()
    if p is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    else:
        sql = "delete from product where id = %s"
        c.execute(sql, (id,))
        conn.commit()
        c.close()
        conn.close()


@app.get("/user/goods.html", response_class=HTMLResponse)
def goods_page():
    try:
        # 使用相对路径：../static/goods.html
        # 注意：这里相对于 goods.py 文件的位置
        with open("../static/goods.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError as e:
        return HTMLResponse(
            content=f"<h1>404 - goods.html 文件未找到</h1><p>请确认文件在 ../static/goods.html</p><p>错误: {str(e)}</p>",
            status_code=404
        )


# ===== 根路径重定向到登录页 =====
@app.get("/")
def root():
    return HTMLResponse(content="""
    <script>
        window.location.href = '/user/login.html';
    </script>
    """)


# ===== 修改：使用上级目录的 static =====
@app.get("/user/login.html", response_class=HTMLResponse)
def goods_page():
    with open("../static/login.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == '__main__':
    init_tidb()  # 替换原来的 init_db()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
