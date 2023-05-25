#!/usr/bin/env python3
# coding=UTF-8
'''
 * @Author       : Yuri
 * @Date         : 28/Apr/2023 09:48
 * @LastEditors  : Yuri
 * @LastEditTime : 28/Apr/2023 09:52
 * @FilePath     : /teach/helloFastAPI/backend/tests/Auth/test.py
 * @Description  : file desc
'''
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_signup():
    response = client.post('/api/auth/signup')
    assert response.status_code == 200
