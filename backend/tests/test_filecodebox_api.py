from datetime import datetime, timedelta, timezone

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport

from src.Auth.models import Base
from src.common.dependencies import get_async_engine
from src.FileCodeBox.router import upload_ip_limit
from src.main import helloFastApi as app


def get_send_password(pwd: str) -> str:
    from src.settings import settings

    if settings.BOOKING_SM4_PASSWORD_ENCRYPT:
        import os
        import time

        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        key = settings.BOOKING_SM4_KEY.encode()
        iv = os.urandom(16)
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
async def setup_filebox_database():
    e = get_async_engine()
    engine = await e.__anext__()

    # 物理建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()


@pytest.mark.asyncio
async def test_filecodebox_ip_rate_limiting_and_cleanup():
    # 保证有测试用户
    email = "filebox_test@test.com"
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 注册并获取 Token
        await client.post(
            "/api/auth/signup", json={"email": email, "password": "123", "first_name": "Box", "last_name": "User", "birthday": None, "avatar": None}
        )
        r_tok = await client.post("/api/auth/token", data={"username": email, "password": get_send_password("123")})
        token = r_tok.json()["data"]["access_token"] if "data" in r_tok.json() else r_tok.json().get("access_token")

        headers = {"Authorization": f"Bearer {token}", "X-Real-IP": "192.168.1.100"}

        # 1. 验证接口挂载连通性，且限流自动计数累加
        # 清空测试 IP 计数以防干扰
        upload_ip_limit.ips.clear()

        # 允许上传的次数通常是有限的，我们在配置里看一下它的 count
        # 但我们直接通过 mock 或连点来测试。
        # 比如我们连续发送 50 次请求以触发限流
        triggered_429 = False
        for _ in range(50):
            r = await client.post("/api/fileCodeBox/share", json={"code": "123456", "pwd": ""}, headers=headers)
            if r.status_code == 429:
                triggered_429 = True
                break

        assert triggered_429 is True, "连续高频请求未正确触发 429 速率限制拦截"

        # 2. 模拟清理过期 IP 的逻辑，验证在遍历字典时是否还会触发 RuntimeError 崩溃
        # 人为注入一些过期的 IP 记录
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        upload_ip_limit.ips["10.0.0.1"] = {"count": 5, "time": now - timedelta(minutes=60)}
        upload_ip_limit.ips["10.0.0.2"] = {"count": 5, "time": now - timedelta(minutes=60)}
        upload_ip_limit.ips["10.0.0.3"] = {"count": 2, "time": now}  # 这个不过期

        # 执行异步并发清理
        await upload_ip_limit.remove_expired_ip()

        # 期望过期 IP 已安全剔除且没有触发任何字典大小改变的 RuntimeError 崩溃
        assert "10.0.0.1" not in upload_ip_limit.ips
        assert "10.0.0.2" not in upload_ip_limit.ips
        assert "10.0.0.3" in upload_ip_limit.ips
