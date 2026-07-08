import requests

base_url = "http://127.0.0.1:8080"


def test_produce_add():
    url = base_url + "/product/add"
    cs = {"name": "小米手机", "price": 1990, "stock": 10}
    r = requests.post(url, json=cs)
    print(r.text)
    assert "小米手机" in r.text

def test_get_all():
    url = base_url + "/product/getall"
    r = requests.get(url)
    print(r.text)
    assert "小米手机" in r.text

def test_get_one():
    url = base_url + "/product/get/2"
    r = requests.get(url)
    print(r.text)
    assert "小米手机" in r.text

    url = base_url + "/product/get/1"
    r = requests.get(url)
    print(r.status_code)
    print(r.text)
    assert r.json()['detail'] == "商品不存在"
    assert r.status_code == 404

def test_update_product():
    url = base_url + "/product/put/3"
    product = {"name": "苹果", "price": 7900, "stock": 100}
    r = requests.put(url, json=product)
    print(r.text)
    assert r.status_code == 200

    url = base_url + "/product/get/3"
    r = requests.get(url)
    print(r.text)
    assert "苹果" in r.text

    url = base_url + "/product/put/1"
    r = requests.put(url, json=product)
    print(r.text)
    assert r.status_code == 404

def test_delete_product():
    url = base_url + "/product/delete/6"
    r = requests.delete(url)
    print(r.text)
    assert r.status_code == 200

    url = base_url + "/product/get/6"
    r = requests.get(url)
    print(r.text)
    assert r.status_code == 404

    url = base_url + "/product/delete/5"
    r = requests.delete(url)
    print(r.text)
    assert r.status_code == 404