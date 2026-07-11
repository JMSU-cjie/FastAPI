"""
baw/goods.py - 业务逻辑模块
负责：商品管理、用户认证、数据库操作
不定义 FastAPI app，只提供路由函数
"""

import os
import pymysql
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

# ============ 创建路由器 ============
router = APIRouter()

# ============ 数据模型 ============

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, description="用户名")
    password: str = Field(min_length=1, description="密码")

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=10, description="用户名")
    phone: str = Field(min_length=11, max_length=11, description="手机号")
    password: str = Field(min_length=1, max_length=11, description="密码")

class ResetPasswordRequest(BaseModel):
    phone: str = Field(min_length=11, max_length=11, description="手机号")
    new_password: Optional[str] = Field(None, description="新密码")

class Product(BaseModel):
    name: str = Field(min_length=1, max_length=10, description="商品名称")
    price: float = Field(gt=0, description="价格")
    stock: int = Field(ge=0, description="库存数量")

# ============ 数据库配置 ============

def get_db_config():
    """从环境变量获取数据库配置"""
    return {
        "host": os.getenv("TIDB_HOST", "localhost"),
        "port": int(os.getenv("TIDB_PORT", 4000)),
        "user": os.getenv("TIDB_USER", "root"),
        "password": os.getenv("TIDB_PASSWORD", ""),
        "database": os.getenv("TIDB_DATABASE", "fastapi"),
        "charset": "utf8mb4"
    }

def get_db_connection():
    """获取数据库连接"""
    config = get_db_config()
    return pymysql.connect(**config)

def init_database():
    """初始化数据库表"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 创建用户表
        c.execute("""
            CREATE TABLE IF NOT EXISTS sys_user (
                id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                phone VARCHAR(11) UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # 创建商品表
        c.execute("""
            CREATE TABLE IF NOT EXISTS product (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(20) NOT NULL,
                price FLOAT NOT NULL,
                stock INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # 插入测试数据（仅当表为空时）
        c.execute("SELECT COUNT(*) FROM sys_user")
        count = c.fetchone()[0]
        if count == 0:
            c.execute("INSERT INTO sys_user (username, password, phone) VALUES ('admin', '123456', '13800138000')")
            c.execute("INSERT INTO sys_user (username, password, phone) VALUES ('user', '123456', '13900139000')")
            conn.commit()
            print("✅ 测试账号已创建: admin/123456, user/123456")
        
        c.close()
        conn.close()
        print("✅ 数据库初始化成功！")
    except Exception as e:
        print(f"⚠️  数据库初始化警告: {e}")

# ============ 认证接口 ============

@router.post("/auth/login")
async def login(login_data: LoginRequest):
    """用户登录"""
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
                "access_token": f"token_{user['id']}_{int(__import__('time').time())}",
                "token_type": "bearer",
                "user": {
                    "id": user['id'],
                    "username": user['username']
                }
            }
        else:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@router.post("/auth/register")
async def register(register_data: RegisterRequest):
    """用户注册"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 检查用户名是否已存在
        c.execute("SELECT id FROM sys_user WHERE username = %s", (register_data.username,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 检查手机号是否已注册
        c.execute("SELECT id FROM sys_user WHERE phone = %s", (register_data.phone,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="手机号已被注册")
        
        # 插入新用户
        sql = "INSERT INTO sys_user (username, password, phone) VALUES (%s, %s, %s)"
        c.execute(sql, (register_data.username, register_data.password, register_data.phone))
        conn.commit()
        
        c.close()
        conn.close()
        
        return {
            "success": True,
            "message": "注册成功",
            "username": register_data.username
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册失败: {str(e)}")

@router.post("/auth/reset_password")
async def reset_password(reset_data: ResetPasswordRequest):
    """重置密码"""
    try:
        conn = get_db_connection()
        c = conn.cursor(pymysql.cursors.DictCursor)
        
        # 查找用户
        c.execute("SELECT id, username FROM sys_user WHERE phone = %s", (reset_data.phone,))
        user = c.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="手机号未注册")
        
        # 如果没有提供新密码，表示验证步骤
        if not reset_data.new_password:
            c.close()
            conn.close()
            return {
                "success": True,
                "message": "验证成功",
                "username": user['username']
            }
        
        # 更新密码
        c.execute(
            "UPDATE sys_user SET password = %s WHERE phone = %s",
            (reset_data.new_password, reset_data.phone)
        )
        conn.commit()
        
        c.close()
        conn.close()
        
        return {
            "success": True,
            "message": "密码已更新",
            "user": {"username": user['username']}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置密码失败: {str(e)}")

@router.get("/auth/check")
async def check_auth(username: str):
    """检查用户是否存在"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id FROM sys_user WHERE username = %s", (username,))
        user = c.fetchone()
        c.close()
        conn.close()
        return {"exists": user is not None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查失败: {str(e)}")

# ============ 商品管理接口 ============

@router.post("/product/add")
async def create_product(product: Product):
    """添加商品"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        sql = "INSERT INTO product(name, price, stock) VALUES (%s, %s, %s)"
        c.execute(sql, (product.name, product.price, product.stock))
        conn.commit()
        id = c.lastrowid
        c.close()
        conn.close()
        return {"id": id, **product.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加商品失败: {str(e)}")

@router.get("/product/getall")
async def get_all_products():
    """获取所有商品"""
    try:
        conn = get_db_connection()
        c = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM product ORDER BY id"
        c.execute(sql)
        products = c.fetchall()
        c.close()
        conn.close()
        return products
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商品列表失败: {str(e)}")

@router.get("/product/get/{id}")
async def get_product(id: int):
    """获取单个商品"""
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取商品失败: {str(e)}")

@router.put("/product/put/{id}")
async def update_product(id: int, product: Product):
    """更新商品"""
    try:
        conn = get_db_connection()
        c = conn.cursor(pymysql.cursors.DictCursor)
        
        # 检查商品是否存在
        c.execute("SELECT * FROM product WHERE id = %s", (id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="商品不存在")
        
        sql = "UPDATE product SET name = %s, price = %s, stock = %s WHERE id = %s"
        c.execute(sql, (product.name, product.price, product.stock, id))
        conn.commit()
        c.close()
        conn.close()
        return {"id": id, **product.dict()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新商品失败: {str(e)}")

@router.delete("/product/delete/{id}")
async def delete_product(id: int):
    """删除商品"""
    try:
        conn = get_db_connection()
        c = conn.cursor(pymysql.cursors.DictCursor)
        
        # 检查商品是否存在
        c.execute("SELECT * FROM product WHERE id = %s", (id,))
        if not c.fetchone():
            raise HTTPException(status_code=404, detail="商品不存在")
        
        sql = "DELETE FROM product WHERE id = %s"
        c.execute(sql, (id,))
        conn.commit()
        c.close()
        conn.close()
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除商品失败: {str(e)}")
