import requests

base_url = "http://127.0.0.1:8080/"


def test_register(get_register):
    url = base_url + "user/register"
    respose = requests.get(url=url, params=get_register)
    print(respose.text)

    assert respose.json()["msg"] == "注册成功"

def test_login(get_login):
    url = base_url + "user/login"

    response = requests.post(url=url, data=get_login)
    print(response.text)

    assert response.json()["msg"] == "登录成功"


def test_recharge(get_amount):
    url = base_url  + "user/recharge"
    response = requests.post(url=url, json=get_amount)
    print(response.text)

    assert response.json()["msg"] == "充值成功"





