from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse

app = FastAPI()

# 挂载静态文件目录：所有 /static/xxx 的请求会去 ./static 目录找 xxx
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    # 访问根路径时，直接重定向到登录页
    return RedirectResponse(url="/static/login.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
