from fastapi import FastAPI, Form
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse

app = FastAPI()


@app.get("/")
def root():
    return {"message": "hello world"}


@app.get("/user/register")
def register(phone: str, pwd: str):
    return {"status": 0, "msg": "注册成功"}


@app.post("/user/login")
def login(phone: str = Form(...), pwd: str = Form(...)):
    return {"status": 0, "msg": "登录成功"}


class RechargeModel(BaseModel):
    phone: str = Field(min_length=11, max_length=11, description="电话号码")
    amount: float = Field(gt=0)

@app.post("/user/recharge")
def recharge(data: RechargeModel):
    return {"status": 0, "msg": "充值成功"}


@app.get("/user/login.html", response_class=HTMLResponse)
def login_page():
    with open("../static/login.html", "r", encoding="utf-8") as f:
        return f.read()

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
