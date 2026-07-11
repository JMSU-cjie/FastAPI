import pymysql
from pydantic import BaseModel, Field
from datetime import datetime, timedelta, UTC
from jose import jwt
import os
from dotenv import load_dotenv

# ============================================================
# 环境变量加载
# ============================================================
if not os.getenv("VERCEL"):
    load_dotenv()

# ============================================================
# 数据库配置
# ============================================================
tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")
tidb_database = os.getenv("TIDB_DATABASE")

DB_CONFIG = {
    "host": tidb_host,
    "port": int(tidb_port) if tidb_port else 4000,
    "user": tidb_user,
    "password": tidb_password,
    "database": tidb_database,
    "charset": "utf8"
}

# ============================================================
# Pydantic 模型（可复用）
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
# 数据库操作函数
# ============================================================
def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def init_db():
    """初始化数据库表"""
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
        print("✅ 数据库初始化完成")
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")

def get_user_by_username_password(username: str, password: str):
    """根据用户名和密码查询用户"""
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    c.execute("SELECT id, username, password FROM sys_user WHERE username = %s AND password = %s", 
              (username, password))
    user = c.fetchone()
    c.close()
    conn.close()
    return user

def get_user_by_username(username: str):
    """根据用户名查询用户"""
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    c.execute("SELECT id FROM sys_user WHERE username = %s", (username,))
    user = c.fetchone()
    c.close()
    conn.close()
    return user

def get_user_by_phone(phone: str):
    """根据手机号查询用户"""
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    c.execute("SELECT id, username FROM sys_user WHERE phone = %s", (phone,))
    user = c.fetchone()
    c.close()
    conn.close()
    return user

def create_user(username: str, phone: str, password: str):
    """创建新用户"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO sys_user (username, phone, password) VALUES (%s, %s, %s)",
        (username, phone, password)
    )
    conn.commit()
    user_id = c.lastrowid
    c.close()
    conn.close()
    return user_id

def update_user_password(phone: str, new_password: str):
    """更新用户密码"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE sys_user SET password = %s WHERE phone = %s",
        (new_password, phone)
    )
    conn.commit()
    c.close()
    conn.close()

def get_all_products():
    """获取所有商品"""
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    c.execute("SELECT * FROM product")
    products = c.fetchall()
    c.close()
    conn.close()
    return products

def get_product_by_id(id: int):
    """根据ID获取商品"""
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    c.execute("SELECT * FROM product WHERE id = %s", (id,))
    product = c.fetchone()
    c.close()
    conn.close()
    return product

def create_product(name: str, price: float, stock: int):
    """创建商品"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO product(name, price, stock) VALUES (%s, %s, %s)", 
              (name, price, stock))
    conn.commit()
    product_id = c.lastrowid
    c.close()
    conn.close()
    return product_id

def update_product(id: int, name: str, price: float, stock: int):
    """更新商品"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE product SET name = %s, price = %s, stock = %s WHERE id = %s",
        (name, price, stock, id)
    )
    conn.commit()
    c.close()
    conn.close()

def delete_product(id: int):
    """删除商品"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM product WHERE id = %s", (id,))
    conn.commit()
    c.close()
    conn.close()
