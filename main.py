from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

# 从 baw/goods.py 导入包含所有 API 路由的 app
from baw.goods import app

# 挂载静态文件目录：所有 /static/xxx 的请求会去 ./static 目录找 xxx
app.mount("/static", StaticFiles(directory="static"), name="static")

# 根路径重定向到登录页
@app.get("/")
def root():
    return RedirectResponse(url="/static/login.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
