import pytest

@pytest.fixture(scope="session", params=[
    {"phone": "13888888888", "pwd": "123456"},
    {"phone": "13899999999", "pwd": "123456"},
    {"phone": "13866666666", "pwd": "123456"},
    {"phone": "13888888888", "pwd": "123456"},
    {"phone": "13866666666", "pwd": "123456"}
])
def get_register(request):
    return request.param

@pytest.fixture(scope="session", params=[
    {"phone": "13888888888", "pwd": "123456"},
    {"phone": "13899999999", "pwd": "123456"},
    {"phone": "13866666666", "pwd": "123456"},
    {"phone": "13888888888", "pwd": "123456"},
    {"phone": "13866666666", "pwd": "123456"}
])
def get_login(request):
    return request.param

@pytest.fixture(scope="session", params=[
    {"phone": "13888888888", "amount": 10},
    {"phone": "13899999999", "amount": 20},
    {"phone": "13866666666", "amount": 30},
    {"phone": "13888888888", "amount": 40},
    {"phone": "13866666666", "amount": 50}
])
def get_amount(request):
    return request.param