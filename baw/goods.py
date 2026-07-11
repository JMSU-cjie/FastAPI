import pymysql
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse
from datetime import datetime, timedelta
import os
import uuid
from dotenv import load_dotenv

# ============================================================
# 环境变量加载
# ============================================================
if not os.getenv("VERCEL"):
    load_dotenv()

# ============================================================
# 创建 FastAPI 应用
# ============================================================
app = FastAPI(title="点餐系统")

# ===== CORS 中间件 =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== 配置 =====
ACCESS_TOKEN_EXPIRE_MINUTES = 30
security = HTTPBearer()

# ===== 内存存储（生产环境应使用 Redis） =====
active_tokens = {}

# ============================================================
# Pydantic 模型
# ============================================================
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

# ============================================================
# 数据库配置
# ============================================================
tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")
tidb_database = os.getenv("TIDB_DATABASE")

# 检查环境变量
missing_vars = []
if not tidb_host: missing_vars.append("TIDB_HOST")
if not tidb_port: missing_vars.append("TIDB_PORT")
if not tidb_user: missing_vars.append("TIDB_USER")
if not tidb_password: missing_vars.append("TIDB_PASSWORD")
if not tidb_database: missing_vars.append("TIDB_DATABASE")

if missing_vars:
    print(f"⚠️ 缺少环境变量: {', '.join(missing_vars)}")
    if not os.getenv("VERCEL"):
        raise EnvironmentError(f"缺少环境变量: {', '.join(missing_vars)}")

DB_CONFIG = {
    "host": tidb_host,
    "port": int(tidb_port) if tidb_port else 4000,
    "user": tidb_user,
    "password": tidb_password,
    "database": tidb_database,
    "charset": "utf8"
}

# ============================================================
# Token 管理函数
# ============================================================
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

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """从 HTTP Bearer 头获取并验证用户"""
    try:
        token = credentials.credentials
        return verify_token(token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

# ============================================================
# 数据库初始化
# ============================================================
_db_initialized = False

def init_db():
    global _db_initialized
    if _db_initialized:
        return
    
    if os.getenv("VERCEL"):
        print("⚠️ Vercel 环境，跳过数据库初始化")
        _db_initialized = True
        return
    
    if not all([tidb_host, tidb_port, tidb_user, tidb_password, tidb_database]):
        print("⚠️ 数据库配置不完整，跳过初始化")
        _db_initialized = True
        return
    
    try:
        print("⏳ 正在初始化数据库...")
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
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS sys_user (
                id INT PRIMARY KEY AUTO_INCREMENT, 
                username VARCHAR(255), 
                phone VARCHAR(20), 
                password VARCHAR(255)
            )
        """)
        conn.commit()
        
        try:
            c.execute("ALTER TABLE sys_user ADD COLUMN phone VARCHAR(20)")
            conn.commit()
            print("✅ 已为 sys_user 表添加 phone 字段")
        except Exception:
            pass
        
        c.execute("""
            CREATE TABLE IF NOT EXISTS product (
                id INT PRIMARY KEY AUTO_INCREMENT, 
                name VARCHAR(20), 
                price FLOAT, 
                stock INT
            )
        """)
        conn.commit()
        
        c.execute("SELECT COUNT(*) FROM sys_user")
        count = c.fetchone()
        if count and count[0] == 0:
            c.execute(
                "INSERT INTO sys_user (username, phone, password) VALUES (%s, %s, %s)",
                ('admin', '13800138000', '123456')
            )
            conn.commit()
            print("✅ 已创建默认用户: admin / 123456")
        
        c.close()
        conn.close()
        _db_initialized = True
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        _db_initialized = True

# ============================================================
# 启动事件
# ============================================================
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        print("✅ 数据库初始化成功")
    except Exception as e:
        print(f"⚠️ 数据库初始化失败: {e}")

# ============================================================
# API 路由
# ============================================================

@app.post("/auth/login")
def login(login_data: LoginRequest):
    try:
        if not all([tidb_host, tidb_port, tidb_user, tidb_password, tidb_database]):
            raise HTTPException(status_code=500, detail="数据库配置不完整")
        
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute("SELECT id, username, password FROM sys_user WHERE username = %s AND password = %s", 
                  (login_data.username, login_data.password))
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
                "user": {"id": user['id'], "username": user['username']}
            }
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"数据库错误: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@app.get("/auth/verify")
def verify_auth(current_user: dict = Depends(get_current_user)):
    return {"success": True, "user": current_user}

@app.post("/auth/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    if token in active_tokens:
        del active_tokens[token]
    return {"success": True, "message": "退出成功"}

@app.post("/auth/register")
def register(register_data: RegisterRequest):
    try:
        if not all([tidb_host, tidb_port, tidb_user, tidb_password, tidb_database]):
            raise HTTPException(status_code=500, detail="数据库配置不完整")
        
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
            "user": {"id": user_id, "username": register_data.username, "phone": register_data.phone}
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
                "user": {"id": user['id'], "username": user['username']}
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
            "user": {"id": user['id'], "username": user['username']}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"密码修改失败: {str(e)}")

@app.post("/product/add")
def create_product(product: Product, current_user: dict = Depends(get_current_user)):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor()
        c.execute("INSERT INTO product(name, price, stock) VALUES (%s, %s, %s)", 
                  (product.name, product.price, product.stock))
        conn.commit()
        id = c.lastrowid
        c.close()
        conn.close()
        return {"id": id, **product.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建商品失败: {str(e)}")

@app.get("/product/getall")
def get_all_products():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute("SELECT * FROM product")
        products = c.fetchall()
        c.close()
        conn.close()
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商品列表失败: {str(e)}")

@app.get("/product/get/{id}")
def get_product(id: int):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute("SELECT * FROM product WHERE id = %s", (id,))
        product = c.fetchone()
        c.close()
        conn.close()
        if product is None:
            raise HTTPException(status_code=404, detail="商品不存在")
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商品失败: {str(e)}")

@app.put("/product/put/{id}")
def update_product(id: int, product: Product, current_user: dict = Depends(get_current_user)):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute("SELECT * FROM product WHERE id = %s", (id,))
        if c.fetchone() is None:
            raise HTTPException(status_code=404, detail="商品不存在")
        c.execute(
            "UPDATE product SET name = %s, price = %s, stock = %s WHERE id = %s",
            (product.name, product.price, product.stock, id)
        )
        conn.commit()
        c.close()
        conn.close()
        return product
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新商品失败: {str(e)}")

@app.delete("/product/delete/{id}")
def delete_product(id: int, current_user: dict = Depends(get_current_user)):
    try:
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute("SELECT * FROM product WHERE id = %s", (id,))
        if c.fetchone() is None:
            raise HTTPException(status_code=404, detail="商品不存在")
        c.execute("DELETE FROM product WHERE id = %s", (id,))
        conn.commit()
        c.close()
        conn.close()
        return {"success": True, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除商品失败: {str(e)}")

# ============================================================
# 健康检查
# ============================================================
@app.get("/health")
async def health_check():
    db_ok = False
    try:
        conn = pymysql.connect(**DB_CONFIG)
        conn.close()
        db_ok = True
    except Exception as e:
        print(f"⚠️ 健康检查 - 数据库连接失败: {e}")
    
    return {
        "status": "ok",
        "database": "connected" if db_ok else "disconnected",
        "vercel_env": bool(os.getenv("VERCEL"))
    }

# ============================================================
# 本地运行
# ============================================================
if __name__ == '__main__':
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
