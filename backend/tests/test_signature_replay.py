import httpx
import pytest
import pytest_asyncio
import uuid
from httpx import ASGITransport
from datetime import datetime, timezone, timedelta
from hashlib import sha256
from src.main import helloFastApi as app
from src.common.dependencies import get_async_engine, get_async_session
from src.Auth.models import Base, User
from src.settings import settings

def get_send_password(pwd: str) -> str:
    if settings.BOOKING_SM4_PASSWORD_ENCRYPT:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding
        from cryptography.hazmat.backends import default_backend
        import os
        import time
        
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
async def setup_replay_database():
    e = get_async_engine()
    engine = await e.__anext__()
    
    # 物理建表与管理员创建，以允许调用 reset 接口进行播种
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_gen = get_async_session(engine)
    session = await session_gen.__anext__()
    
    from sqlalchemy import select
    stmt = select(User).where(User.email == "admin@cinema.com")
    res = await session.execute(stmt)
    if not res.scalar_one_or_none():
        new_admin = User(
            email="admin@cinema.com",
            password="admin12345",
            admin=1,
            first_name="Cinema",
            last_name="Admin",
            gender=1
        )
        session.add(new_admin)
        await session.commit()
        
    await session.close()
    await engine.dispose()

@pytest.mark.asyncio
async def test_signature_anti_replay():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 管理员登录并重置播种数据
        r_adm = await client.post("/api/auth/token", data={"username": "admin@cinema.com", "password": get_send_password("admin12345")})
        admin_token = r_adm.json()["data"]["access_token"] if "data" in r_adm.json() else r_adm.json().get("access_token")
        
        r_reset = await client.post("/api/cinema/reset", headers={"Authorization": f"Bearer {admin_token}"})
        assert r_reset.status_code == 200

        # 2. 开启接口安全签名校验
        orig_config_resp = await client.get("/api/cinema/config")
        orig_config = orig_config_resp.json()["data"]

        update_payload = orig_config.copy()
        update_payload["signature_check"] = True
        r_up = await client.post("/api/cinema/config", json=update_payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert r_up.status_code == 200

        try:
            # 3. 会员用户登录
            r_usr = await client.post("/api/auth/token", data={"username": "user_1@test.com", "password": get_send_password("123456")})
            user_token = r_usr.json()["data"]["access_token"] if "data" in r_usr.json() else r_usr.json().get("access_token")

            # 4. 获取上映场次及座位
            r_show = await client.get("/api/cinema/showtimes", headers={"Authorization": f"Bearer {user_token}"})
            showtimes = r_show.json()["data"]["showtimes"]
            showtime = showtimes[0]
            showtime_id = showtime["uid"]

            r_seat = await client.get(f"/api/cinema/showtimes/{showtime_id}/seats", headers={"Authorization": f"Bearer {user_token}"})
            seats = r_seat.json()["data"]
            available_seats = [s for s in seats if s["status"] == 0]
            assert len(available_seats) >= 2, "测试需要至少2个空闲座位"

            seat1_id = available_seats[0]["uid"]
            seat2_id = available_seats[1]["uid"]

            # 5. 生成合法的数字签名，模拟第一次正常下单购买 seat1
            timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))
            nonce = str(uuid.uuid4())
            secret_key = settings.BOOKING_SIGNATURE_SECRET
            
            sig_payload = f"{showtime_id}{seat1_id}{timestamp}{nonce}{secret_key}"
            signature = sha256(sig_payload.encode()).hexdigest()

            headers = {
                "Authorization": f"Bearer {user_token}",
                "X-Timestamp": timestamp,
                "X-Nonce": nonce,
            }

            r_order1 = await client.post("/api/cinema/order", json={"showtime_id": showtime_id, "seat_id": seat1_id, "signature": signature}, headers=headers)
            assert r_order1.status_code == 201, f"首次使用正常签名下单失败: {r_order1.text}"

            # 6. 使用完全相同的随机盐 nonce 尝试发起重放攻击购买 seat2 (时间戳和nonce是一样的)
            sig_payload2 = f"{showtime_id}{seat2_id}{timestamp}{nonce}{secret_key}"
            signature2 = sha256(sig_payload2.encode()).hexdigest()
            
            headers_replay = {
                "Authorization": f"Bearer {user_token}",
                "X-Timestamp": timestamp,
                "X-Nonce": nonce, # 完全一样的随机盐
            }

            r_order2 = await client.post("/api/cinema/order", json={"showtime_id": showtime_id, "seat_id": seat2_id, "signature": signature2}, headers=headers_replay)
            # 应该由于我们在 nonce_cache 中命中去重锁，被直接以 401 拦截
            assert r_order2.status_code == 401, f"重放攻击未被阻断拦截: {r_order2.text}"
            err_msg = r_order2.json().get("detail") or r_order2.json().get("error_info") or ""
            assert "已被消费" in err_msg


        finally:
            # 还原配置，防止干扰其他正常压测
            await client.post("/api/cinema/config", json=orig_config, headers={"Authorization": f"Bearer {admin_token}"})


@pytest.mark.asyncio
async def test_sm3_signature_verification():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 管理员登录
        r_adm = await client.post("/api/auth/token", data={"username": "admin@cinema.com", "password": get_send_password("admin12345")})
        admin_token = r_adm.json()["data"]["access_token"] if "data" in r_adm.json() else r_adm.json().get("access_token")
        
        # 2. 开启国密 SM3 校验开关并重置数据
        r_reset = await client.post("/api/cinema/reset", headers={"Authorization": f"Bearer {admin_token}"})
        assert r_reset.status_code == 200
        
        orig_config = (await client.get("/api/cinema/config")).json()["data"]
        update_payload = orig_config.copy()
        update_payload["signature_check"] = False # 关闭常规签名
        update_payload["signature_sm3_check"] = True # 开启国密签名
        update_payload["sm4_password_encrypt"] = False
        r_up = await client.post("/api/cinema/config", json=update_payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert r_up.status_code == 200
        
        try:
            # 3. 会员登录并获取场次座位
            r_usr = await client.post("/api/auth/token", data={"username": "user_1@test.com", "password": get_send_password("123456")})
            user_token = r_usr.json()["data"]["access_token"] if "data" in r_usr.json() else r_usr.json().get("access_token")
            
            r_show = await client.get("/api/cinema/showtimes", headers={"Authorization": f"Bearer {user_token}"})
            showtime_id = r_show.json()["data"]["showtimes"][0]["uid"]
            
            r_seat = await client.get(f"/api/cinema/showtimes/{showtime_id}/seats", headers={"Authorization": f"Bearer {user_token}"})
            seat_id = [s for s in r_seat.json()["data"] if s["status"] == 0][0]["uid"]
            
            # 4. 国密签名校验：故意不携带 X-Signature 头部，预期失败 401
            timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))
            nonce = str(uuid.uuid4())
            
            headers_no_sig = {
                "Authorization": f"Bearer {user_token}",
                "X-Timestamp": timestamp,
                "X-Nonce": nonce,
            }
            r_no_sig = await client.post("/api/cinema/order", json={"showtime_id": showtime_id, "seat_id": seat_id}, headers=headers_no_sig)
            assert r_no_sig.status_code == 401
            
            # 5. 携带正确的国密签名下单，预期成功 201
            secret_key = settings.BOOKING_SIGNATURE_SECRET
            sig_payload = f"{showtime_id}{seat_id}{timestamp}{nonce}{secret_key}"
            
            from cryptography.hazmat.primitives import hashes
            h = hashes.Hash(hashes.SM3())
            h.update(sig_payload.encode())
            sig_sm3 = h.finalize().hex()
            
            headers_sm3 = {
                "Authorization": f"Bearer {user_token}",
                "X-Timestamp": timestamp,
                "X-Nonce": nonce,
                "X-Signature": sig_sm3
            }
            r_order = await client.post("/api/cinema/order", json={"showtime_id": showtime_id, "seat_id": seat_id}, headers=headers_sm3)
            assert r_order.status_code == 201, f"SM3下单失败: {r_order.text}"
            
        finally:
            # 还原
            await client.post("/api/cinema/config", json=orig_config, headers={"Authorization": f"Bearer {admin_token}"})
