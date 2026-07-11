import pymysql
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse
from datetime import datetime, timedelta
import os
import uuid
from dotenv import load_dotenv

load_dotenv()

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

BASE_DIR = base_dir
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="点餐系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ACCESS_TOKEN_EXPIRE_MINUTES = 30

active_tokens = {}

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=10, description="商品名称")
    price: float = Field(gt=0, description="价格")
    stock: int = Field(ge=0, description="库存数量")

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=10, description="用户名")
    password: str = Field(min_length=1, max_length=11, description="密码")

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=10, description="用户名")
    phone: str = Field(min_length=11, max_length=11, description="手机号")
    password: str = Field(min_length=1, max_length=11, description="密码")

class ResetPasswordRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=11, description="手机号")
    new_password: str = Field(min_length=1, max_length=11, description="新密码")

tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")
tidb_database = os.getenv("TIDB_DATABASE")

DB_CONFIG = {
    "host": tidb_host,
    "port": int(tidb_port),
    "user": tidb_user,
    "password": tidb_password,
    "database": tidb_database,
    "charset": "utf8"
}

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    token = str(uuid.uuid4())
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    active_tokens[token] = {
        "data": data,
        "expire": expire
    }
    return token

def verify_token(token: str):
    if token not in active_tokens:
        raise HTTPException(
            status_code=401,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = active_tokens[token]
    if datetime.now() > token_data["expire"]:
        del active_tokens[token]
        raise HTTPException(
            status_code=401,
            detail="登录已过期，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data["data"]

def get_current_user(authorization: str = Depends(lambda: None)):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="未授权",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        token = authorization.replace("Bearer ", "")
        return verify_token(token)
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

def init_db():
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset=DB_CONFIG['charset']
        )

        c = conn.cursor()

        c.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8")
        conn.commit()

        conn.select_db(DB_CONFIG['database'])

        c.execute(
            "CREATE TABLE IF NOT EXISTS sys_user(id INT PRIMARY KEY AUTO_INCREMENT, username VARCHAR(255), phone VARCHAR(20), password VARCHAR(255))"
        )
        conn.commit()

        try:
            c.execute("ALTER TABLE sys_user ADD COLUMN phone VARCHAR(20)")
            conn.commit()
            print("已为 sys_user 表添加 phone 字段")
        except Exception:
            pass

        c.execute(
            "CREATE TABLE IF NOT EXISTS product(id INT PRIMARY KEY AUTO_INCREMENT, name VARCHAR(20), price FLOAT, stock INT)")
        conn.commit()

        c.execute("SELECT COUNT(*) FROM sys_user")
        count = c.fetchone()
        if count[0] == 0:
            c.execute(
                "INSERT INTO sys_user (username, phone, password) VALUES (%s, %s, %s)",
                ('admin', '13800138000', '123456')
            )
            conn.commit()
            print("已创建默认用户: admin / 123456")

        c.close()
        conn.close()
    except Exception as e:
        print(f"初始化数据库异常，异常信息: {e}")

@app.post("/auth/login")
def login(login_data: LoginRequest):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)

        sql = "SELECT id, username, password FROM sys_user WHERE username = %s AND password = %s"
        c.execute(sql, (login_data.username, login_data.password))
        user = c.fetchone()

        c.close()
        conn.close()

        if user:
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user['username'], "user_id": user['id']},
                expires_delta=access_token_expires
            )
            return {
                "success": True,
                "message": "登录成功",
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "user": {
                    "id": user['id'],
                    "username": user['username']
                }
            }
        else:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@app.get("/auth/verify")
def verify_auth(token: str):
    try:
        user_data = verify_token(token)
        return {
            "success": True,
            "user": user_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/logout")
def logout(token: str):
    if token in active_tokens:
        del active_tokens[token]
    return {"success": True, "message": "退出成功"}

@app.post("/auth/register")
def register(register_data: RegisterRequest):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)

        c.execute("SELECT id FROM sys_user WHERE username = %s", (register_data.username,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")

        c.execute("SELECT id FROM sys_user WHERE phone = %s", (register_data.phone,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="手机号已被注册")

        c.execute(
            "INSERT INTO sys_user (username, phone, password) VALUES (%s, %s, %s)",
            (register_data.username, register_data.phone, register_data.password)
        )
        conn.commit()

        user_id = c.lastrowid
        c.close()
        conn.close()

        return {
            "success": True,
            "message": "注册成功",
            "user": {
                "id": user_id,
                "username": register_data.username,
                "phone": register_data.phone
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")

@app.post("/auth/reset_password")
def reset_password(reset_data: ResetPasswordRequest):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)

        c.execute("SELECT id, username FROM sys_user WHERE phone = %s", (reset_data.phone,))
        user = c.fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="该手机号未注册")

        if not reset_data.new_password:
            c.close()
            conn.close()
            return {
                "success": True,
                "message": "手机号验证成功",
                "user": {
                    "id": user['id'],
                    "username": user['username']
                }
            }

        c.execute(
            "UPDATE sys_user SET password = %s WHERE phone = %s",
            (reset_data.new_password, reset_data.phone)
        )
        conn.commit()

        c.close()
        conn.close()

        return {
            "success": True,
            "message": "密码修改成功，请使用新密码登录",
            "user": {
                "id": user['id'],
                "username": user['username']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"密码修改失败: {str(e)}")

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
        with open(os.path.join(STATIC_DIR, "goods.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError as e:
        return HTMLResponse(
            content=f"<h1>404 - goods.html 文件未找到</h1><p>错误: {str(e)}</p>",
            status_code=404
        )

@app.get("/user/login.html", response_class=HTMLResponse)
def login_page():
    try:
        with open(os.path.join(STATIC_DIR, "login.html"), "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError as e:
        return HTMLResponse(
            content=f"<h1>404 - login.html 文件未找到</h1><p>错误: {str(e)}</p>",
            status_code=404
        )

if __name__ == '__main__':
    init_db()
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
