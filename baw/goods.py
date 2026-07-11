import pymysql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============ 数据库配置 ============
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

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

# ============ 数据库工具函数 ============
def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(**DB_CONFIG)

def init_db():
    """初始化数据库"""
    try:
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

        # 切换到目标数据库
        conn.select_db(DB_CONFIG['database'])

        # 创建商品表
        c.execute("""
            CREATE TABLE IF NOT EXISTS product(
                id INT PRIMARY KEY AUTO_INCREMENT, 
                name VARCHAR(20), 
                price FLOAT, 
                stock INT
            )
        """)
        conn.commit()

        c.close()
        conn.close()
        print("数据库初始化成功")
    except Exception as e:
        print(f"初始化数据库异常: {e}")

# ============ 商品数据库操作函数 ============

def get_all_products():
    """获取所有商品"""
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM product ORDER BY id"
    c.execute(sql)
    products = c.fetchall()
    c.close()
    conn.close()
    return products

def get_product_by_id(product_id: int):
    """根据ID获取商品"""
    conn = get_db_connection()
    c = conn.cursor(pymysql.cursors.DictCursor)
    sql = "SELECT * FROM product WHERE id = %s"
    c.execute(sql, (product_id,))
    product = c.fetchone()
    c.close()
    conn.close()
    return product

def create_product(name: str, price: float, stock: int):
    """创建商品"""
    conn = get_db_connection()
    c = conn.cursor()
    sql = "INSERT INTO product(name, price, stock) VALUES (%s, %s, %s)"
    c.execute(sql, (name, price, stock))
    conn.commit()
    product_id = c.lastrowid
    c.close()
    conn.close()
    return {"id": product_id, "name": name, "price": price, "stock": stock}

def update_product(product_id: int, name: str, price: float, stock: int):
    """更新商品信息"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 检查商品是否存在
    check_sql = "SELECT id FROM product WHERE id = %s"
    c.execute(check_sql, (product_id,))
    if c.fetchone() is None:
        c.close()
        conn.close()
        return False
    
    # 更新商品
    sql = "UPDATE product SET name = %s, price = %s, stock = %s WHERE id = %s"
    c.execute(sql, (name, price, stock, product_id))
    conn.commit()
    c.close()
    conn.close()
    return True

def delete_product(product_id: int):
    """删除商品"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # 检查商品是否存在
    check_sql = "SELECT id FROM product WHERE id = %s"
    c.execute(check_sql, (product_id,))
    if c.fetchone() is None:
        c.close()
        conn.close()
        return False
    
    # 删除商品
    sql = "DELETE FROM product WHERE id = %s"
    c.execute(sql, (product_id,))
    conn.commit()
    c.close()
    conn.close()
    return True
