from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from jose import jwt

from src.Auth.config import ALGORITHM, SECRET_KEY
from src.Auth.models import Base
from src.common.dependencies import get_async_engine
from src.main import helloFastApi as app
from src.settings import settings


def get_send_password(pwd: str) -> str:
    if settings.BOOKING_SM4_PASSWORD_ENCRYPT:
        import os
        import time

        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        key = settings.BOOKING_SM4_KEY.encode()
        iv = os.urandom(16)  # 生成 16 字节随机 IV

        # 内嵌 13 位毫秒时间戳
        timestamp_ms = str(int(time.time() * 1000))
        plain_payload = f"{timestamp_ms}:{pwd}"

        cipher = Cipher(algorithms.SM4(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        padder = padding.PKCS7(128).padder()
        padded_pwd = padder.update(plain_payload.encode()) + padder.finalize()
        ct = encryptor.update(padded_pwd) + encryptor.finalize()
        return iv.hex() + ct.hex()
    return pwd


@pytest_asyncio.fixture(autouse=True)
async def setup_auth_database():
    engine = await get_async_engine()

    # 物理建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()


@pytest.mark.asyncio
async def test_signup_avatar_optional_and_password_validation():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 保证没有残留的用户
        import random

        email = f"test_auth_api_{random.randint(1000, 9999)}@test.com"

        # 1. 简单密码开关为 False 时，注册简单密码，且不传头像 (avatar 设为 None / 可选)
        settings.AUTH_STRONG_PASSWORD_CHECK = False
        payload1 = {"email": email, "password": "123", "first_name": "Auth", "last_name": "Test", "birthday": None, "avatar": None}
        r1 = await client.post("/api/auth/signup", json=payload1)
        assert r1.status_code == 201, f"简单密码且无头像注册失败: {r1.text}"
        assert r1.json()["data"]["email"] == email

        # 2. 强密码开关开启时，使用不达标的简单密码注册，应该被 422 拦截拒绝
        settings.AUTH_STRONG_PASSWORD_CHECK = True
        email2 = f"test_auth_api_strong_{random.randint(1000, 9999)}@test.com"
        payload2 = {"email": email2, "password": "123", "first_name": "Auth", "last_name": "Strong", "birthday": None, "avatar": None}
        r2 = await client.post("/api/auth/signup", json=payload2)
        assert r2.status_code == 422, f"强密码开关开启时未拦截弱密码: {r2.text}"

        # 3. 强密码开关开启时，使用达标的复杂度密码注册，应该成功通过
        payload3 = {"email": email2, "password": "Password_123!", "first_name": "Auth", "last_name": "Strong", "birthday": None, "avatar": None}
        r3 = await client.post("/api/auth/signup", json=payload3)
        assert r3.status_code == 201, f"强密码开关开启时达标密码注册失败: {r3.text}"

        # 还原开关
        settings.AUTH_STRONG_PASSWORD_CHECK = False


@pytest.mark.asyncio
async def test_refresh_token_life_cycle():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        email = "refresh_test@test.com"
        # 注册
        payload = {"email": email, "password": "123", "first_name": "Refresh", "last_name": "User", "birthday": None, "avatar": None}
        await client.post("/api/auth/signup", json=payload)

        # 1. 登录以获取 token 与 refresh_token
        r1 = await client.post("/api/auth/token", data={"username": email, "password": get_send_password("123")})
        assert r1.status_code == 201
        data = r1.json()["data"] if "data" in r1.json() else r1.json()
        refresh_token = data.get("refresh_token")
        assert refresh_token is not None

        # 2. 刷新 Token
        r2 = await client.get(f"/api/auth/token?refreshToken={refresh_token}")
        assert r2.status_code == 201, f"Token 刷新接口发生崩溃失败: {r2.text}"
        new_data = r2.json()["data"]
        assert "access_token" in new_data


@pytest.mark.asyncio
async def test_token_expired_signature_priority():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 构造一个已经过期的 Token (iat 设在过去，exp 也是过去)
        current_time = datetime.now(timezone.utc)
        expired_time = current_time - timedelta(minutes=60)
        payload = {"sub": "expired_user@test.com", "exp": expired_time, "iat": expired_time - timedelta(minutes=10), "scope": "access_token"}
        expired_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        # 2. 使用此过期 Token 请求 Profile 接口，期望首选拦截为 Token 过期
        r = await client.get("/api/auth/profile", headers={"Authorization": f"Bearer {expired_token}"})
        assert r.status_code == 401
        detail = r.json().get("detail", "")
        # 确保由于我们在 dependencies 中调换了顺序，异常能被 ExpiredSignatureError 首选捕获，
        # 从而返回符合规范的 "Token expired" 细节
        assert "expired" in detail.lower()


@pytest.mark.asyncio
async def test_user_profile_details():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import random

        email = f"profile_detail_test_{random.randint(1000, 9999)}@test.com"
        # 注册，指定 gender 值为 1 (男)
        payload = {
            "email": email,
            "password": "123",
            "first_name": "Profile",
            "last_name": "Detail",
            "gender": 1,
            "birthday": "1995-05-20",
            "avatar": "data:image/png;base64,xxxx",
        }
        r_signup = await client.post("/api/auth/signup", json=payload)
        assert r_signup.status_code == 201, f"Signup failed: {r_signup.text}"

        # 登录
        r1 = await client.post("/api/auth/token", data={"username": email, "password": get_send_password("123")})
        assert r1.status_code == 201
        data = r1.json()["data"] if "data" in r1.json() else r1.json()
        access_token = data["access_token"]

        # 获取 profile
        r2 = await client.get("/api/auth/profile", headers={"Authorization": f"Bearer {access_token}"})
        assert r2.status_code == 200
        profile_data = r2.json()["data"]

        # 验证返回字段
        assert profile_data["email"] == email
        assert profile_data["full_name"] == "Profile Detail"
        assert profile_data["gender"] == 1
        assert profile_data["birthday"] == "1995-05-20"
        assert profile_data["avatar"] == "data:image/png;base64,xxxx"


@pytest.mark.asyncio
async def test_single_sign_on_restriction():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import random

        email = f"sso_test_{random.randint(1000, 9999)}@test.com"

        # 1. 注册新用户
        signup_payload = {"email": email, "password": "sso_password123", "first_name": "SSO", "last_name": "Tester", "birthday": None, "avatar": None}
        r_signup = await client.post("/api/auth/signup", json=signup_payload)
        assert r_signup.status_code == 201

        # 2. 第一次登录 (模拟终端 A)
        r_login_a = await client.post("/api/auth/token", data={"username": email, "password": get_send_password("sso_password123")})
        assert r_login_a.status_code == 201
        data_a = r_login_a.json()["data"] if "data" in r_login_a.json() else r_login_a.json()
        token_a = data_a["access_token"]
        refresh_a = data_a["refresh_token"]

        # 3. 终端 A 验证：调用 profile 接口，应该成功
        r_profile_a1 = await client.get("/api/auth/profile", headers={"Authorization": f"Bearer {token_a}"})
        assert r_profile_a1.status_code == 200

        # 4. 第二次登录 (模拟终端 B)
        r_login_b = await client.post("/api/auth/token", data={"username": email, "password": get_send_password("sso_password123")})
        assert r_login_b.status_code == 201
        data_b = r_login_b.json()["data"] if "data" in r_login_b.json() else r_login_b.json()
        token_b = data_b["access_token"]
        refresh_b = data_b["refresh_token"]

        # 5. 终端 A 被踢出验证：再次使用 token_A 调用 profile，应该失败 (401)
        r_profile_a2 = await client.get("/api/auth/profile", headers={"Authorization": f"Bearer {token_a}"})
        assert r_profile_a2.status_code == 401
        assert "elsewhere" in r_profile_a2.json().get("detail", "").lower()

        # 6. 终端 B 正常访问验证：使用 token_B 调用 profile，应该成功
        r_profile_b = await client.get("/api/auth/profile", headers={"Authorization": f"Bearer {token_b}"})
        assert r_profile_b.status_code == 200

        # 7. 终端 A Refresh Token 失效验证：尝试用 refresh_A 刷新，应该失败 (401)
        r_refresh_a = await client.get(f"/api/auth/token?refreshToken={refresh_a}")
        assert r_refresh_a.status_code == 401
        assert "elsewhere" in r_refresh_a.json().get("detail", "").lower()

        # 8. 终端 B Refresh Token 正常验证：尝试用 refresh_B 刷新，应该成功 (201)
        r_refresh_b = await client.get(f"/api/auth/token?refreshToken={refresh_b}")
        assert r_refresh_b.status_code == 201
        assert "access_token" in r_refresh_b.json()["data"]


@pytest.mark.asyncio
async def test_sm4_password_encryption_login():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 注册一个测试账号
        import random

        email = f"sm4_login_{random.randint(1000, 9999)}@test.com"
        pwd = "test_sm4_password_123"

        signup_payload = {
            "email": email,
            "password": pwd,
            "first_name": "SM4",
            "last_name": "User",
        }
        r_signup = await client.post("/api/auth/signup", json=signup_payload)
        assert r_signup.status_code == 201

        # 2. 完全尊重并根据 .env 实际配置 switch 校验分支 or 非校验分支
        if settings.BOOKING_SM4_PASSWORD_ENCRYPT:
            # 开启了 SM4 密码加密：明文登录应该被拦截失败（400）
            r_plain = await client.post("/api/auth/token", data={"username": email, "password": pwd})
            assert r_plain.status_code == 400

            # 手动模拟前端使用 SM4 对称加密密码进行登录：应该成功并通过（201）
            r_encrypt = await client.post("/api/auth/token", data={"username": email, "password": get_send_password(pwd)})
            assert r_encrypt.status_code == 201
            assert "access_token" in r_encrypt.json() or "access_token" in r_encrypt.json().get("data", {})
        else:
            # 未开启密码加密：明文登录应该直接成功并通过（201）
            r_plain = await client.post("/api/auth/token", data={"username": email, "password": pwd})
            assert r_plain.status_code == 201
            assert "access_token" in r_plain.json()
