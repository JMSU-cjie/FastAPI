import pymysql
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============ 加载环境变量 ============
# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
env_path = BASE_DIR / '.env'

logger.info(f"项目根目录: {BASE_DIR}")
logger.info(f".env 文件路径: {env_path}")
logger.info(f".env 文件是否存在: {env_path.exists()}")

# 加载 .env 文件
if env_path.exists():
    load_dotenv(env_path)
    logger.info("成功加载 .env 文件")
else:
    logger.warning(".env 文件不存在，将使用系统环境变量")
    load_dotenv()

# ============ 数据库配置 ============
tidb_host = os.getenv("TIDB_HOST")
tidb_port = os.getenv("TIDB_PORT")
tidb_user = os.getenv("TIDB_USER")
tidb_password = os.getenv("TIDB_PASSWORD")
tidb_database = os.getenv("TIDB_DATABASE")

# 打印配置信息（隐藏密码）
logger.info(f"数据库配置: host={tidb_host}, port={tidb_port}, user={tidb_user}, database={tidb_database}")

# 检查必要的配置
if not all([tidb_host, tidb_port, tidb_user, tidb_password, tidb_database]):
    logger.error("数据库配置不完整，请检查 .env 文件")
    raise ValueError("数据库配置不完整，请检查 .env 文件")

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
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        raise

def test_db_connection():
    """测试数据库连接"""
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("数据库连接测试成功")
        return True
    except Exception as e:
        logger.error(f"数据库连接测试失败: {e}")
        return False

def init_db():
    """初始化数据库"""
    logger.info("开始初始化数据库...")
    
    # 测试数据库连接
    if not test_db_connection():
        logger.error("数据库连接失败，初始化中止")
        return False
    
    try:
        # 连接数据库（不指定数据库名）
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset=DB_CONFIG['charset']
        )
        c = conn.cursor()

        # 创建数据库
        try:
            c.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} CHARACTER SET utf8")
            conn.commit()
            logger.info(f"数据库 {DB_CONFIG['database']} 已创建或已存在")
        except Exception as e:
            logger.error(f"创建数据库失败: {e}")
            return False

        # 切换到目标数据库
        conn.select_db(DB_CONFIG['database'])

        # 创建商品表
        try:
            c.execute("""
                CREATE TABLE IF NOT EXISTS product(
                    id INT PRIMARY KEY AUTO_INCREMENT, 
                    name VARCHAR(20) NOT NULL, 
                    price FLOAT NOT NULL, 
                    stock INT NOT NULL DEFAULT 0
                )
            """)
            conn.commit()
            logger.info("商品表 product 已创建或已存在")
        except Exception as e:
            logger.error(f"创建商品表失败: {e}")
            return False

        c.close()
        conn.close()
        logger.info("数据库初始化成功")
        return True
    except Exception as e:
        logger.error(f"初始化数据库异常: {e}")
        return False

# ============ 商品数据库操作函数 ============

def get_all_products():
    """获取所有商品"""
    try:
        conn = get_db_connection()
        c = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM product ORDER BY id"
        c.execute(sql)
        products = c.fetchall()
        c.close()
        conn.close()
        logger.info(f"获取到 {len(products)} 个商品")
        return products
    except Exception as e:
        logger.error(f"获取所有商品失败: {e}")
        raise

def get_product_by_id(product_id: int):
    """根据ID获取商品"""
    try:
        conn = get_db_connection()
        c = conn.cursor(pymysql.cursors.DictCursor)
        sql = "SELECT * FROM product WHERE id = %s"
        c.execute(sql, (product_id,))
        product = c.fetchone()
        c.close()
        conn.close()
        if product:
            logger.info(f"获取商品成功: id={product_id}")
        else:
            logger.warning(f"商品不存在: id={product_id}")
        return product
    except Exception as e:
        logger.error(f"获取商品失败: {e}")
        raise

def create_product(name: str, price: float, stock: int):
    """创建商品"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        sql = "INSERT INTO product(name, price, stock) VALUES (%s, %s, %s)"
        c.execute(sql, (name, price, stock))
        conn.commit()
        product_id = c.lastrowid
        c.close()
        conn.close()
        logger.info(f"创建商品成功: id={product_id}, name={name}")
        return {"id": product_id, "name": name, "price": price, "stock": stock}
    except Exception as e:
        logger.error(f"创建商品失败: {e}")
        raise

def update_product(product_id: int, name: str, price: float, stock: int):
    """更新商品信息"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 检查商品是否存在
        check_sql = "SELECT id FROM product WHERE id = %s"
        c.execute(check_sql, (product_id,))
        if c.fetchone() is None:
            c.close()
            conn.close()
            logger.warning(f"更新失败，商品不存在: id={product_id}")
            return False
        
        # 更新商品
        sql = "UPDATE product SET name = %s, price = %s, stock = %s WHERE id = %s"
        c.execute(sql, (name, price, stock, product_id))
        conn.commit()
        c.close()
        conn.close()
        logger.info(f"更新商品成功: id={product_id}")
        return True
    except Exception as e:
        logger.error(f"更新商品失败: {e}")
        raise

def delete_product(product_id: int):
    """删除商品"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # 检查商品是否存在
        check_sql = "SELECT id FROM product WHERE id = %s"
        c.execute(check_sql, (product_id,))
        if c.fetchone() is None:
            c.close()
            conn.close()
            logger.warning(f"删除失败，商品不存在: id={product_id}")
            return False
        
        # 删除商品
        sql = "DELETE FROM product WHERE id = %s"
        c.execute(sql, (product_id,))
        conn.commit()
        c.close()
        conn.close()
        logger.info(f"删除商品成功: id={product_id}")
        return True
    except Exception as e:
        logger.error(f"删除商品失败: {e}")
        raise
