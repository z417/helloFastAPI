import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport
from src.common.dependencies import get_async_engine, get_async_session
from src.main import helloFastApi as app
from src.Auth.models import Base, User

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    e = get_async_engine()
    engine = await e.__anext__()
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_gen = get_async_session(engine)
    session = await session_gen.__anext__()
    
    # Create admin user if not exists to allow API-based seeding
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

def get_send_password(pwd: str) -> str:
    from src.settings import settings
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


async def booking_order_adaptive(client, showtime_id, seat_id, user_token):
    from src.settings import settings
    from hashlib import sha256
    from datetime import datetime, timezone
    import uuid
    
    headers = {"Authorization": f"Bearer {user_token}"}
    body = {
        "showtime_id": str(showtime_id),
        "seat_id": str(seat_id)
    }
    
    if settings.BOOKING_SIGNATURE_CHECK or settings.BOOKING_SM3_SIGNATURE_CHECK:
        timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))
        nonce = str(uuid.uuid4())
        headers["X-Timestamp"] = timestamp
        headers["X-Nonce"] = nonce
        
        secret_key = settings.BOOKING_SIGNATURE_SECRET
        sig_payload = f"{showtime_id}{seat_id}{timestamp}{nonce}{secret_key}"
        
        if settings.BOOKING_SIGNATURE_CHECK:
            body["signature"] = sha256(sig_payload.encode()).hexdigest()
            
        if settings.BOOKING_SM3_SIGNATURE_CHECK:
            from cryptography.hazmat.primitives import hashes
            h = hashes.Hash(hashes.SM3())
            h.update(sig_payload.encode())
            headers["X-Signature"] = h.finalize().hex()
            
    return await client.post("/api/cinema/order", json=body, headers=headers)


@pytest.mark.asyncio
async def test_cinema_booking_flow():

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 管理员登录
        r1 = await client.post("/api/auth/token", data={"username": "admin@cinema.com", "password": get_send_password("admin12345")})
        assert r1.status_code == 201, f"Admin login failed: {r1.text}"
        token = r1.json()["data"]["access_token"] if "data" in r1.json() else r1.json().get("access_token")
        
        # 2. 执行数据重置与播种
        r2 = await client.post("/api/cinema/reset", headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200, f"Database reset failed: {r2.text}"
        
        # 3. 普通会员登录
        r3 = await client.post("/api/auth/token", data={"username": "user_1@test.com", "password": get_send_password("123456")})
        assert r3.status_code == 201, f"User login failed: {r3.text}"
        user_token = r3.json()["data"]["access_token"] if "data" in r3.json() else r3.json().get("access_token")
        
        # 4. 获取排片场次
        r4 = await client.get("/api/cinema/showtimes", headers={"Authorization": f"Bearer {user_token}"})
        assert r4.status_code == 200, f"Failed to get showtimes: {r4.text}"
        showtimes = r4.json()["data"]["showtimes"]
        assert len(showtimes) > 0, "No showtimes available"
        
        showtime = showtimes[0]
        showtime_id = showtime["uid"]
        
        # 校验豆瓣 Top100 电影的扩展字段已成功载入
        movie_obj = showtime["movie"]
        assert "rating" in movie_obj
        assert "genres" in movie_obj
        assert "summary" in movie_obj
        assert float(movie_obj["rating"]) > 0
        assert len(movie_obj["genres"]) > 0
        assert len(movie_obj["summary"]) > 0
        
        # 5. 获取指定场次座位
        r5 = await client.get(f"/api/cinema/showtimes/{showtime_id}/seats", headers={"Authorization": f"Bearer {user_token}"})
        assert r5.status_code == 200, f"Failed to get seats: {r5.text}"
        seats = r5.json()["data"]
        assert len(seats) == 40, f"Expected exactly 40 seats for VIP room, but got {len(seats)}"
        available_seats = [s for s in seats if s["status"] == 0]
        assert len(available_seats) == 40, "All seats should be available initially"
        
        seat = available_seats[0]
        seat_id = seat["uid"]
        
        # 6. 并发购票下单测试 (Decimal精度验证)
        r6 = await booking_order_adaptive(client, showtime_id, seat_id, user_token)
        assert r6.status_code == 201, f"Booking failed: {r6.text}"
        order_data = r6.json()["data"]
        assert order_data["amount"] == showtime["price"], "Price mismatch"


import uuid
from hashlib import sha256
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_admin_config_switches_combination():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 管理员登录
        r1 = await client.post("/api/auth/token", data={"username": "admin@cinema.com", "password": get_send_password("admin12345")})
        assert r1.status_code == 201, f"Admin login failed: {r1.text}"
        admin_token = r1.json()["data"]["access_token"] if "data" in r1.json() else r1.json().get("access_token")

        # 2. 获取原始配置
        r2 = await client.get("/api/cinema/config")
        assert r2.status_code == 200, r2.text
        orig_config = r2.json()["data"]

        # 3. 组合并开启所有性能与安全校验开关 (随意组合)
        test_payload = {
            "pool_mode": "null",
            "lock_mode": "optimistic",
            "slow_query": True,
            "signature_check": True
        }
        r3 = await client.post("/api/cinema/config", json=test_payload, headers={"Authorization": f"Bearer {admin_token}"})
        assert r3.status_code == 200, f"Failed to update config: {r3.text}"

        try:
            # 4. 再次获取配置验证已在内存热重载
            r4 = await client.get("/api/cinema/config")
            assert r4.json()["data"]["pool_mode"] == "null"
            assert r4.json()["data"]["lock_mode"] == "optimistic"
            assert r4.json()["data"]["slow_query"] is True
            assert r4.json()["data"]["signature_check"] is True

            # 5. 普通会员登录并尝试无签名下单 (由于开启了 signature_check，应该被拦截)
            r5 = await client.post("/api/auth/token", data={"username": "user_1@test.com", "password": get_send_password("123456")})
            user_token = r5.json()["data"]["access_token"] if "data" in r5.json() else r5.json().get("access_token")

            r6 = await client.get("/api/cinema/showtimes", headers={"Authorization": f"Bearer {user_token}"})
            showtimes = r6.json()["data"]["showtimes"]
            showtime = showtimes[0]
            showtime_id = showtime["uid"]

            r7 = await client.get(f"/api/cinema/showtimes/{showtime_id}/seats", headers={"Authorization": f"Bearer {user_token}"})
            available_seats = [s for s in r7.json()["data"] if s["status"] == 0]
            assert len(available_seats) > 0
            seat_id = available_seats[0]["uid"]

            # 无签名下单应失败 (401 或 400 校验异常)
            r8 = await client.post("/api/cinema/order", json={"showtime_id": showtime_id, "seat_id": seat_id}, headers={"Authorization": f"Bearer {user_token}"})
            assert r8.status_code in [400, 401], f"Expected signature check failure but got: {r8.status_code} {r8.text}"

            # 6. 生成数字签名并下单 (应成功通过)
            timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000))
            nonce = str(uuid.uuid4())
            secret_key = "hello_cinema_range_secret_key"
            sig_payload = f"{showtime_id}{seat_id}{timestamp}{nonce}{secret_key}"
            signature = sha256(sig_payload.encode()).hexdigest()

            headers = {
                "Authorization": f"Bearer {user_token}",
                "X-Timestamp": timestamp,
                "X-Nonce": nonce,
            }
            r9 = await client.post("/api/cinema/order", json={"showtime_id": showtime_id, "seat_id": seat_id, "signature": signature}, headers=headers)
            assert r9.status_code == 201, f"Booking with signature failed: {r9.text}"
        finally:
            # 7. 还原配置以防影响后续测试
            r10 = await client.post("/api/cinema/config", json=orig_config, headers={"Authorization": f"Bearer {admin_token}"})
            assert r10.status_code == 200, "Failed to restore config"


@pytest.mark.asyncio
async def test_db_engine_singleton_and_hot_reload():
    # 1. 获取两次 Engine，验证它们是同一个单例对象 (未改变配置时)
    engine_gen1 = get_async_engine()
    engine1 = await engine_gen1.__anext__()
    
    engine_gen2 = get_async_engine()
    engine2 = await engine_gen2.__anext__()
    
    assert engine1 is engine2, "在配置未变更时，数据库引擎单例未能复用，导致长连接池失效"
    
    # 2. 模拟配置热变更，再次获取，验证引擎已被 dispose 并重新实例化
    from src.settings import settings
    original_pool_mode = settings.DB_POOL_MODE
    
    try:
        # 修改配置以触发热重载
        settings.DB_POOL_MODE = "null" if original_pool_mode != "null" else "queue"
        
        engine_gen3 = get_async_engine()
        engine3 = await engine_gen3.__anext__()
        
        assert engine3 is not engine1, "配置发生热变更后，引擎单例未能成功销毁并热重载重建"
    finally:
        # 还原配置
        settings.DB_POOL_MODE = original_pool_mode


@pytest.mark.asyncio
async def test_user_orders_and_timing_checks():
    
    from datetime import datetime, timezone, timedelta
    from uuid import uuid4
    from src.Cinema.models import Showtime, Seat, Movie, CinemaRoom
    from sqlalchemy import select

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. 管理员登录并重置
        r1 = await client.post("/api/auth/token", data={"username": "admin@cinema.com", "password": get_send_password("admin12345")})
        assert r1.status_code == 201
        admin_token = r1.json()["data"]["access_token"] if "data" in r1.json() else r1.json().get("access_token")
        
        r2 = await client.post("/api/cinema/reset", headers={"Authorization": f"Bearer {admin_token}"})
        assert r2.status_code == 200

        # 2. 普通会员登录
        r3 = await client.post("/api/auth/token", data={"username": "user_1@test.com", "password": get_send_password("123456")})
        assert r3.status_code == 201
        user_token = r3.json()["data"]["access_token"] if "data" in r3.json() else r3.json().get("access_token")

        # 3. 校验获取的所有排片场次都必须在 5 分钟之后 (当前时间 + 5分钟)，且排片场次总量正好等于 2,160 场
        r4 = await client.get("/api/cinema/showtimes?limit=3000", headers={"Authorization": f"Bearer {user_token}"})
        assert r4.status_code == 200
        showtimes_data = r4.json()["data"]
        assert showtimes_data["total"] == 2160, f"Expected exactly 2160 showtimes, but got {showtimes_data['total']}"
        showtimes = showtimes_data["showtimes"]
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for s in showtimes:
            st = datetime.fromisoformat(s["start_time"].replace("Z", "+00:00")).replace(tzinfo=None)
            assert st >= now + timedelta(minutes=5), "列表中不应包含上映前 5 分钟内或已过期的场次"

        # 4. 下单购票
        showtime = showtimes[0]
        showtime_id = showtime["uid"]
        r5 = await client.get(f"/api/cinema/showtimes/{showtime_id}/seats", headers={"Authorization": f"Bearer {user_token}"})
        available_seats = [s for s in r5.json()["data"] if s["status"] == 0]
        seat_id = available_seats[0]["uid"]

        r6 = await booking_order_adaptive(client, showtime_id, seat_id, user_token)
        assert r6.status_code == 201

        # 5. 用户获取已购票记录并校验订单结构与详情
        r7 = await client.get("/api/cinema/orders", headers={"Authorization": f"Bearer {user_token}"})
        assert r7.status_code == 200
        orders = r7.json()["data"]
        assert len(orders) > 0, "用户应当能成功查询到刚刚购买的选票"
        order = orders[0]
        assert "movie_title" in order
        assert "room_name" in order
        assert "row_num" in order
        assert "col_num" in order
        assert order["amount"] == showtime["price"]

        # 6. 特别注入：构造一个“上映前2分钟（不足5分钟）”的放映场次，测试购票API拦截行为
        e = get_async_engine()
        engine = await e.__anext__()
        session_gen = get_async_session(engine)
        session = await session_gen.__anext__()

        # 获取已有的电影和影厅
        res_m = await session.execute(select(Movie))
        movie = res_m.scalars().first()
        assert movie is not None
        res_r = await session.execute(select(CinemaRoom))
        room = res_r.scalars().first()
        assert room is not None

        near_showtime_id = uuid4()
        near_seat_id = uuid4()
        
        # 场次时间设为当前时间 + 2分钟 (不足 5 分钟)
        near_start = datetime.now(timezone.utc) + timedelta(minutes=2)
        
        near_showtime = Showtime(
            uid=near_showtime_id,
            movie_id=movie.uid,
            room_id=room.uid,
            start_time=near_start,
            price=showtime["price"],
            remaining_inventory=100,
            version=1,
            is_deleted=0
        )
        near_seat = Seat(
            uid=near_seat_id,
            showtime_id=near_showtime_id,
            row_num=1,
            col_num=1,
            status=0,
            is_deleted=0
        )
        session.add(near_showtime)
        session.add(near_seat)
        await session.commit()
        await session.close()
        await engine.dispose()

        # 尝试购买该临近开映的选票，期望返回 400 Bad Request 并且拒绝交易
        r8 = await booking_order_adaptive(client, near_showtime_id, near_seat_id, user_token)
        assert r8.status_code == 400, f"Expected 400 rejection for near showtime but got {r8.status_code} {r8.text}"
        err_msg = r8.json().get("detail") or r8.json().get("error_info") or ""
        assert "不足 5 分钟" in err_msg or "5 分钟" in err_msg

        # 7. 退票测试
        order_id = order["uid"]
        
        # 正常退票
        r_refund = await client.post(f"/api/cinema/order/{order_id}/refund", headers={"Authorization": f"Bearer {user_token}"})
        assert r_refund.status_code == 200, f"Refund failed: {r_refund.text}"
        assert "退票成功" in r_refund.json()["data"]
        
        # 重复退票拦截 (期望返回 400)
        r_refund_dup = await client.post(f"/api/cinema/order/{order_id}/refund", headers={"Authorization": f"Bearer {user_token}"})
        assert r_refund_dup.status_code == 400
        
        # 校验获取的订单中订单状态变成 2 (已退票)
        r_orders_check = await client.get("/api/cinema/orders", headers={"Authorization": f"Bearer {user_token}"})
        assert r_orders_check.status_code == 200
        refunded_order = [o for o in r_orders_check.json()["data"] if o["uid"] == order_id][0]
        assert refunded_order["status"] == 2
