import pymysql
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse
from datetime import datetime, timedelta, UTC
from jose import jwt
import os
from dotenv import load_dotenv

# ============================================================
# 环境变量加载（仅本地开发时使用）
# Vercel 部署时通过平台环境变量注入
# ============================================================
if not os.getenv("VERCEL"):
    load_dotenv()

app = FastAPI(title="点餐系统")

# ===== CORS 中间件 =====
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== JWT 配置 =====
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
security = HTTPBearer()

# ============================================================
# 数据库配置（从环境变量读取）
# ============================================================
tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")
tidb_database = os.getenv("TIDB_DATABASE")

# 检查必需的环境变量
missing_vars = []
if not tidb_host: missing_vars.append("TIDB_HOST")
if not tidb_port: missing_vars.append("TIDB_PORT")
if not tidb_user: missing_vars.append("TIDB_USER")
if not tidb_password: missing_vars.append("TIDB_PASSWORD")
if not tidb_database: missing_vars.append("TIDB_DATABASE")

if missing_vars:
    error_msg = f"缺少环境变量: {', '.join(missing_vars)}"
    print(f"❌ {error_msg}")
    # 在 Vercel 上只打印警告，不中断启动（让应用能响应健康检查）
    if not os.getenv("VERCEL"):
        raise EnvironmentError(f"{error_msg}。请在 .env 文件或 Vercel 环境变量中配置。")
    else:
        print(f"⚠️ Vercel 环境缺少环境变量，请检查 Vercel 仪表盘设置")

DB_CONFIG = {
    "host": tidb_host,
    "port": int(tidb_port) if tidb_port else 4000,
    "user": tidb_user,
    "password": tidb_password,
    "database": tidb_database,
    "charset": "utf8"
}

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
# JWT 工具函数
# ============================================================
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None or user_id is None:
            raise HTTPException(status_code=401, detail="无效的认证凭证")
        return {"username": username, "user_id": user_id}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭证")

# ============================================================
# 数据库初始化（惰性加载 - 在 Vercel 上跳过）
# ============================================================
_db_initialized = False

def init_db():
    """初始化数据库表（Vercel 环境下跳过）"""
    global _db_initialized
    if _db_initialized:
        return
    
    # Vercel 环境下跳过数据库初始化，避免超时
    if os.getenv("VERCEL"):
        print("⚠️ Vercel 环境，跳过数据库初始化（表应该已存在）")
        _db_initialized = True
        return
    
    # 检查环境变量是否完整
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
        
        # 创建数据库
        c.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8")
        conn.commit()
        conn.select_db(DB_CONFIG['database'])
        
        # 创建用户表
        c.execute("""
            CREATE TABLE IF NOT EXISTS sys_user (
                id INT PRIMARY KEY AUTO_INCREMENT, 
                username VARCHAR(255), 
                phone VARCHAR(20), 
                password VARCHAR(255)
            )
        """)
        conn.commit()
        
        # 添加 phone 字段（如果不存在）
        try:
            c.execute("ALTER TABLE sys_user ADD COLUMN phone VARCHAR(20)")
            conn.commit()
            print("✅ 已为 sys_user 表添加 phone 字段")
        except Exception:
            pass
        
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
        
        # 创建默认管理员用户
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
        _db_initialized = True  # 避免重复尝试

# ============================================================
# 启动事件
# ============================================================
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()

# ============================================================
# 健康检查
# ============================================================
@app.get("/health")
async def health_check():
    """健康检查端点"""
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
# API 路由
# ============================================================

# ---------- 认证 ----------
@app.post("/auth/login")
def login(login_data: LoginRequest):
    try:
        # 检查环境变量是否完整
        if not all([tidb_host, tidb_port, tidb_user, tidb_password, tidb_database]):
            raise HTTPException(status_code=500, detail="数据库配置不完整，请检查环境变量")
        
        conn = pymysql.connect(**DB_CONFIG)
        c = conn.cursor(pymysql.cursors.DictCursor)
        c.execute("SELECT id, username, password FROM sys_user WHERE username = %s AND password = %s", 
                  (login_data.username, login_data.password))
        user = c.fetchone()
        c.close()
        conn.close()
        
        if user:
            access_token = create_access_token(
                data={"sub": user['username'], "user_id": user['id']},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
def verify_auth(current_user: dict = Depends(verify_token)):
    return {"success": True, "user": current_user}

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

# ---------- 商品管理 ----------
@app.post("/product/add")
def create_product(product: Product):
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
def update_product(id: int, product: Product):
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
def delete_product(id: int):
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
# 本地运行
# ============================================================
if __name__ == '__main__':
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
