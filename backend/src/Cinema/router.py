import asyncio
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from cacheout import LFUCache
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.Auth.dependencies import get_current_user
from src.Auth.models import User
from src.Cinema.models import CinemaRoom, Movie, Seat, Showtime, TicketOrder
from src.Cinema.schemas import (
    ConfigResponseSchema,
    CreateOrderSchema,
    OrderResponseSchema,
    SeatResponseSchema,
    ShowtimeListResponseSchema,
    ShowtimeResponseSchema,
    UpdateConfigSchema,
    UserOrderResponseSchema,
)
from src.Cinema.seeder import run_reset_and_seed
from src.common import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    InternalServerError,
    NotFoundException,
    ResponseModel,
    UnAuthenticatedException,
    get_async_session,
)
from src.settings import settings
from src.utils import L

nonce_cache = LFUCache()

router = APIRouter(
    prefix="/api/cinema",
    tags=["电影票务高并发性能测试靶场"],
)


@router.post("/reset", response_model=ResponseModel[str])
async def reset_database(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel:
    """
    一键还原接口：清除所有靶场业务数据及用户，重置数据回初始播种状态 (强制要求 Admin 管理员权限)
    """
    if current_user.admin != 1:
        raise ForbiddenException(message="权限不足，仅特权管理员可执行数据一键还原重置")

    try:
        await run_reset_and_seed(session)

        # 同步管理员的当前 session_id 到重置后的新库，避免 SSO 规则将当前管理员踢出
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            with L.catch(message="SSO session restore failed during reset", level="ERROR"):
                from jose import jwt

                from src.Auth.config import ALGORITHM, SECRET_KEY

                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                session_id = payload.get("session_id")
                if session_id:
                    await session.execute(update(User).where(User.email == current_user.email).values(current_session_id=session_id))
                    await session.commit()

        # 强制清理并释放全局 _engine，以防外部测试进程/日结清盘覆盖 SQLite 物理文件后连接句柄失效
        from src.common import dependencies

        if dependencies._engine is not None:
            await dependencies._engine.dispose()
            dependencies._engine = None
            dependencies._current_db_url = None
            dependencies._current_pool_mode = None
        return ResponseModel(data="success")
    except Exception as e:
        raise InternalServerError(message=f"数据重置失败: {str(e)}")


@router.get("/config", response_model=ResponseModel[ConfigResponseSchema])
async def get_cinema_config(response: Response) -> ResponseModel:
    """
    获取靶场当前瓶颈开关配置参数 (免鉴权，供 UI 看板渲染配置状态，增加协议级强力防缓存头)
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    data = ConfigResponseSchema(
        pool_mode=settings.DB_POOL_MODE,
        lock_mode=settings.BOOKING_LOCK_MODE,
        slow_query=settings.CINEMA_SLOW_QUERY,
        signature_check=settings.BOOKING_SIGNATURE_CHECK,
        signature_secret=settings.BOOKING_SIGNATURE_SECRET,
        signature_sm3_check=settings.BOOKING_SM3_SIGNATURE_CHECK,
        sm4_password_encrypt=settings.BOOKING_SM4_PASSWORD_ENCRYPT,
        sm4_key=settings.BOOKING_SM4_KEY,
    )

    return ResponseModel(data=data)


@router.get("/movies", response_model=ResponseModel[list[dict]])
async def get_movies(session: AsyncSession = Depends(get_async_session)) -> ResponseModel:
    """
    获取上映电影字典列表 (极简，高频读字典化)
    """
    res = await session.execute(select(Movie).where(Movie.is_deleted == 0))
    movies = res.scalars().all()
    return ResponseModel(data=[{"uid": str(m.uid), "title": m.title} for m in movies])


@router.get("/rooms", response_model=ResponseModel[list[dict]])
async def get_rooms(session: AsyncSession = Depends(get_async_session)) -> ResponseModel:
    """
    获取上映影厅字典列表 (极简，高频读字典化)
    """
    res = await session.execute(select(CinemaRoom).where(CinemaRoom.is_deleted == 0))
    rooms = res.scalars().all()
    return ResponseModel(data=[{"uid": str(r.uid), "name": r.name} for r in rooms])


@router.post("/config", response_model=ResponseModel[str])
async def update_cinema_config(
    req: UpdateConfigSchema,
    current_user: User = Depends(get_current_user),
) -> ResponseModel:
    """
    靶场参数配置热调修改接口 (特权 Admin 专属，支持内存热重载及硬盘 .env 持久化同步)
    """
    if current_user.admin != 1:
        raise ForbiddenException(message="权限不足，仅特权管理员可调节靶场性能开关配置")

    # 1. 内存热重载
    settings.DB_POOL_MODE = req.pool_mode
    settings.BOOKING_LOCK_MODE = req.lock_mode
    settings.CINEMA_SLOW_QUERY = req.slow_query
    settings.BOOKING_SIGNATURE_CHECK = req.signature_check
    settings.BOOKING_SM3_SIGNATURE_CHECK = req.signature_sm3_check
    settings.BOOKING_SM4_PASSWORD_ENCRYPT = req.sm4_password_encrypt

    # 2. 硬盘 .env 同步持久化增量覆盖写入 (只替换或追加本次更新的变量，保留原文件的其他内容及注释)
    try:
        env_path = Path(settings.ENV_FILE)
        env_path.parent.mkdir(parents=True, exist_ok=True)

        cinema_keys = {
            "DB_POOL_MODE": req.pool_mode,
            "BOOKING_LOCK_MODE": req.lock_mode,
            "CINEMA_SLOW_QUERY": str(req.slow_query),
            "BOOKING_SIGNATURE_CHECK": str(req.signature_check),
            "BOOKING_SM3_SIGNATURE_CHECK": str(req.signature_sm3_check),
            "BOOKING_SM4_PASSWORD_ENCRYPT": str(req.sm4_password_encrypt),
        }
        updated_keys = set()
        env_lines = []

        if env_path.exists():
            with env_path.open(mode="r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    # 保留注释、空行、分号行等
                    if not stripped or stripped.startswith("#") or stripped.startswith(";") or stripped.startswith("//"):
                        env_lines.append(line)
                        continue

                    # 确保被保留的每一行以换行符结尾，防止发生行尾拼接
                    line_to_append = line if line.endswith("\n") else line + "\n"

                    if "=" in stripped:
                        parts = stripped.split("=", 1)
                        key = parts[0].strip()
                        if key in cinema_keys:
                            env_lines.append(f"{key}={cinema_keys[key]}\n")
                            updated_keys.add(key)
                        else:
                            env_lines.append(line_to_append)
                    else:
                        env_lines.append(line_to_append)

        # 将原文件中不存在的配置变量追加到末尾
        for key, val in cinema_keys.items():
            if key not in updated_keys:
                env_lines.append(f"{key}={val}\n")

        # 写入文件
        with env_path.open(mode="w", encoding="utf-8") as f:
            f.writelines(env_lines)
    except Exception as e:
        L.exception(f"配置保存持久化失败: {str(e)}")
        raise InternalServerError(message=f"配置保存持久化失败: {str(e)}")

    return ResponseModel(data="success")


@router.get("/showtimes", response_model=ResponseModel[ShowtimeListResponseSchema])
async def get_showtimes(
    date: Optional[str] = None,
    movie_id: Optional[UUID] = None,
    room_id: Optional[UUID] = None,
    time_range: Optional[str] = None,
    search_name: Optional[str] = None,
    limit: int = 15,
    offset: int = 0,
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel:
    """
    排片场次联合检索查询接口 (高频读，支持慢 SQL 控制开关、完全数据库层过滤及分页查询)
    """
    # 模拟经典慢 SQL 性能瓶颈 (通过配置 CINEMA_SLOW_QUERY 控制)
    if settings.CINEMA_SLOW_QUERY:
        await asyncio.sleep(0.5)  # 注入 500ms 并发排队挂起延迟，模拟无索引下的表死锁/大表模糊扫描

    now_plus_5m = datetime.now() + timedelta(minutes=5)
    stmt = select(Showtime).join(Showtime.movie).where(Showtime.is_deleted == 0, Showtime.start_time >= now_plus_5m)

    # 1. 电影模糊搜索匹配 (DB 级别模糊查询)
    if search_name:
        stmt = stmt.where(Movie.title.ilike(f"%{search_name}%"))

    # 2. 观影日期匹配 (DB 级别截断对比)
    if date:
        stmt = stmt.where(func.date(Showtime.start_time) == date)

    # 3. 电影匹配
    if movie_id:
        stmt = stmt.where(Showtime.movie_id == movie_id)

    # 4. 影厅匹配
    if room_id:
        stmt = stmt.where(Showtime.room_id == room_id)

    # 5. 放映时间段匹配 (DB 级别解析小时，字典映射替代 if/elif 链)
    _TIME_RANGE_BOUNDS = {"morning": ("08", "12"), "afternoon": ("12", "18"), "night": ("18", "24")}
    if time_range and (bounds := _TIME_RANGE_BOUNDS.get(time_range)):
        hour_col = func.strftime("%H", Showtime.start_time)
        stmt = stmt.where(hour_col >= bounds[0], hour_col < bounds[1])

    # 6. 高性能 count 查询获取符合交集条件的总票单量 total (分页核心)
    from sqlalchemy import func as sa_func

    count_stmt = select(sa_func.count()).select_from(stmt.subquery())
    count_res = await session.execute(count_stmt)
    total = count_res.scalar() or 0

    # 7. 拼接 limit 和 offset 进行物理层数据截断，并联表加载
    stmt = stmt.options(joinedload(Showtime.movie), joinedload(Showtime.room)).limit(limit).offset(offset)
    res = await session.execute(stmt)
    showtimes = res.scalars().all()

    showtimes_data = []
    for s in showtimes:
        showtimes_data.append(
            ShowtimeResponseSchema(
                uid=s.uid,
                movie=s.movie,
                room=s.room,
                start_time=s.start_time,
                price=s.price,
                remaining_inventory=s.remaining_inventory,
            )
        )

    # 包装成分页结构响应返回
    data = ShowtimeListResponseSchema(total=total, showtimes=showtimes_data)
    return ResponseModel(data=data)


@router.get("/showtimes/{showtime_id}/seats", response_model=ResponseModel[list[SeatResponseSchema]])
async def get_seats(
    showtime_id: UUID,
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel:
    """
    某场次的座位图占用查询接口
    """
    stmt = select(Seat).where(Seat.showtime_id == showtime_id, Seat.is_deleted == 0)
    res = await session.execute(stmt)
    seats = res.scalars().all()

    data = [
        SeatResponseSchema(
            uid=seat.uid,
            row_num=seat.row_num,
            col_num=seat.col_num,
            status=seat.status,
        )
        for seat in seats
    ]
    return ResponseModel(data=data)


@router.post("/order", response_model=ResponseModel[OrderResponseSchema], status_code=status.HTTP_201_CREATED)
async def create_booking_order(
    req: CreateOrderSchema,
    request: Request,  # 用于读取安全签名 Headers
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel:
    """
    并发选座购票下单接口 (下单即代表购票成功，包含接口数字签名时效校验与唯一索引幂等处理)
    """
    # ==================== Step 1: 签名安全校验 (防恶意篡改与大并发下生成算法练习) ====================
    if settings.BOOKING_SIGNATURE_CHECK or settings.BOOKING_SM3_SIGNATURE_CHECK:
        x_timestamp = request.headers.get("X-Timestamp")
        x_nonce = request.headers.get("X-Nonce")

        if x_timestamp is None or x_nonce is None:
            raise UnAuthenticatedException(message="接口安全验证失败，签名参数 Headers 缺失")

        # 1.1 校验签名时效性 (防并发重放攻击，限制 5 分钟误差内)
        try:
            ts_ms = int(x_timestamp)
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            if abs(now_ms - ts_ms) > 300000:
                raise UnAuthenticatedException(message="接口安全验证失败，签名时间戳已超出 5 分钟有效期")
        except ValueError:
            raise BadRequestException(message="非法的时间戳格式")

        # 构造签名核心负载
        secret_key = settings.BOOKING_SIGNATURE_SECRET
        sig_payload = f"{req.showtime_id}{req.seat_id}{x_timestamp}{x_nonce}{secret_key}"

        # 1.2 常规 SHA-256 签名正交校验 (挪入 Body 传参的 signature)
        if settings.BOOKING_SIGNATURE_CHECK:
            if not req.signature:
                raise UnAuthenticatedException(message="接口安全验证失败，SHA-256 签名参数 signature 缺失")
            computed_sig = sha256(sig_payload.encode()).hexdigest()
            if computed_sig != req.signature:
                raise UnAuthenticatedException(message="接口安全验证未通过，常规数字签名校验失败")

        # 1.3 国密 SM3 签名正交校验 (占领 Header 的 X-Signature)
        if settings.BOOKING_SM3_SIGNATURE_CHECK:
            x_signature = request.headers.get("X-Signature")
            if not x_signature:
                raise UnAuthenticatedException(message="接口安全验证失败，国密 SM3 签名 Headers X-Signature 缺失")
            from cryptography.hazmat.primitives import hashes

            h = hashes.Hash(hashes.SM3())
            h.update(sig_payload.encode())
            computed_sig_sm3 = h.finalize().hex()
            if computed_sig_sm3 != x_signature:
                raise UnAuthenticatedException(message="接口安全验证未通过，国密 SM3 数字签名校验失败")

        # 1.4 校验随机盐去重防重放 (防高并发 API 重放，5分钟 300秒)
        if nonce_cache.get(x_nonce):
            raise UnAuthenticatedException(message="接口安全验证失败，该签名已被消费，请勿发起重放请求")
        nonce_cache.set(x_nonce, 1, ttl=300)

    lock_mode = settings.BOOKING_LOCK_MODE.lower()

    # ==================== Step 2: 根据高并发锁模式，查询场次与座位 ====================
    # 悲观锁追加 WITH FOR UPDATE 行排他锁；无锁/乐观锁使用普通查询，消除重复分支
    _for_update = lock_mode == "pessimistic"
    stmt_showtime = select(Showtime).where(Showtime.uid == req.showtime_id, Showtime.is_deleted == 0)
    if _for_update:
        stmt_showtime = stmt_showtime.with_for_update()
    showtime = (await session.execute(stmt_showtime)).scalar_one_or_none()
    if not showtime:
        raise NotFoundException(message="放映场次未找到")

    stmt_seat = select(Seat).where(Seat.uid == req.seat_id, Seat.showtime_id == req.showtime_id, Seat.is_deleted == 0)
    if _for_update:
        stmt_seat = stmt_seat.with_for_update()
    seat = (await session.execute(stmt_seat)).scalar_one_or_none()

    if not seat:
        raise NotFoundException(message="所选座位未找到")

    # ==================== Step 3: 严格的票务业务规则校验 ====================
    # 3.1 校验座位占用与放映场次库存
    if seat.status == 1:
        raise ConflictException(message="该座位已被售出，请重新选座")
    if showtime.remaining_inventory <= 0:
        raise ConflictException(message="该放映场次已售罄")

    # 3.2 校验时间：放映时间必须在未来，且最长预售期为 30 天
    now = datetime.now()
    start_time = showtime.start_time
    # 防御性编程：防御 naive/aware datetime 进行比较时引发的冲突错误
    if start_time.tzinfo is not None:
        start_time = start_time.replace(tzinfo=None)

    if start_time < now + timedelta(minutes=5):
        raise BadRequestException(message="该场次距离开映已不足 5 分钟或已放映，已关闭在线售票服务")
    if start_time > now + timedelta(days=30):
        raise BadRequestException(message="该场次超出 30 天预售期，暂未开启预售")

    # ==================== Step 4: 并发库存扣减与占座处理 ====================
    order_uid = uuid4()
    order_amount = showtime.price

    if lock_mode == "optimistic":
        # 4.1 乐观锁：基于 version 版本号进行 CAS 并发原子更新
        old_version = showtime.version
        stmt_update_showtime = (
            update(Showtime)
            .where(Showtime.uid == showtime.uid, Showtime.version == old_version)
            .values(remaining_inventory=Showtime.remaining_inventory - 1, version=Showtime.version + 1)
        )
        update_res = await session.execute(stmt_update_showtime)
        if isinstance(update_res, CursorResult) and update_res.rowcount == 0:
            raise ConflictException(message="购票人数较多，请稍后重试")

        # 乐观锁原子的占领座位状态 (status: 0 -> 1)
        stmt_update_seat = update(Seat).where(Seat.uid == seat.uid, Seat.status == 0).values(status=1, sold_to_user=current_user.uid)
        seat_update_res = await session.execute(stmt_update_seat)
        if isinstance(seat_update_res, CursorResult) and seat_update_res.rowcount == 0:
            raise ConflictException(message="该座位刚刚被其他用户占用了")
    else:
        # 4.2 悲观锁/无锁：内存中更新，SQLAlchemy 会在 commit 时进行 Flush
        showtime.remaining_inventory -= 1
        seat.status = 1
        seat.sold_to_user = current_user.uid

    # ==================== Step 5: 写入购票订单 (强加联合唯一约束以实现并发绝对幂等防重) ====================
    order = TicketOrder(
        uid=order_uid,
        showtime_id=showtime.uid,
        user_id=current_user.uid,
        seat_id=seat.uid,
        amount=order_amount,
        status=1,  # 购票成功
    )
    session.add(order)

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        # 深度捕获数据库联合唯一性索引冲突 (防止并发压测重复提交生成多张重合订单)
        err_str = str(e).lower()
        if isinstance(e, IntegrityError) or "unique" in err_str or "uq_showtime_seat" in err_str:
            raise ConflictException(message="该座位已被售出，请重新选座")
        raise InternalServerError(message=f"购票系统忙，请重试: {str(e)}")

    data = OrderResponseSchema(
        uid=order_uid,
        showtime_id=showtime.uid,
        seat_id=seat.uid,
        amount=order_amount,
        status=1,
    )
    return ResponseModel(data=data)


@router.get("/orders", response_model=ResponseModel[list[UserOrderResponseSchema]])
async def get_user_orders(
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel:
    """
    获取当前登录用户的所有已购票订单 (含详细的电影、影厅、座位与放映时间信息，支持高效物理分页)
    """
    stmt = (
        select(
            TicketOrder.uid,
            TicketOrder.showtime_id,
            TicketOrder.amount,
            TicketOrder.status,
            TicketOrder.created_at,
            Movie.title.label("movie_title"),
            Movie.duration.label("movie_duration"),
            CinemaRoom.name.label("room_name"),
            Showtime.start_time,
            Seat.row_num,
            Seat.col_num,
        )
        .join(Showtime, TicketOrder.showtime_id == Showtime.uid)
        .join(Movie, Showtime.movie_id == Movie.uid)
        .join(CinemaRoom, Showtime.room_id == CinemaRoom.uid)
        .join(Seat, TicketOrder.seat_id == Seat.uid)
        .where(TicketOrder.user_id == current_user.uid)
        .order_by(TicketOrder.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    res = await session.execute(stmt)
    orders = res.all()

    data = [
        UserOrderResponseSchema(
            uid=o.uid,
            showtime_id=o.showtime_id,
            amount=o.amount,
            status=o.status,
            created_at=o.created_at,
            movie_title=o.movie_title,
            movie_duration=o.movie_duration,
            room_name=o.room_name,
            start_time=o.start_time,
            row_num=o.row_num,
            col_num=o.col_num,
        )
        for o in orders
    ]
    return ResponseModel(data=data)


@router.post("/order/{order_id}/refund", response_model=ResponseModel[str])
async def refund_ticket(
    order_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResponseModel:
    """
    退票接口：将订单状态置为已退票(2)，恢复座位状态为可选(0)，并将场次库存+1
    """
    # 1. 悲观行锁查询订单，确保订单数据独占
    stmt_order = select(TicketOrder).where(TicketOrder.uid == order_id).with_for_update()
    res_order = await session.execute(stmt_order)
    order = res_order.scalar_one_or_none()

    if not order:
        raise NotFoundException(message="订单未找到")

    if order.user_id != current_user.uid:
        raise ForbiddenException(message="无权操作此订单")

    if order.status == 2:
        raise BadRequestException(message="该订单已成功退票，请勿重复申请")

    # 2. 查询对应的场次与座位并加锁，确保库存与状态一致性
    stmt_showtime = select(Showtime).where(Showtime.uid == order.showtime_id).with_for_update()
    res_showtime = await session.execute(stmt_showtime)
    showtime = res_showtime.scalar_one_or_none()

    if not showtime:
        raise NotFoundException(message="该订单关联的放映场次未找到")

    # 3. 校验放映时间：如果开映时间已过，则不允许退票
    now = datetime.now()
    start_time = showtime.start_time
    if start_time.tzinfo is not None:
        start_time = start_time.replace(tzinfo=None)

    if start_time < now:
        raise BadRequestException(message="该放映场次已经放映或开映，不可申请退票")

    stmt_seat = select(Seat).where(Seat.uid == order.seat_id).with_for_update()
    res_seat = await session.execute(stmt_seat)
    seat = res_seat.scalar_one_or_none()

    if not seat:
        raise NotFoundException(message="该订单关联的座位未找到")

    # 4. 执行退票状态流更新
    order.status = 2  # 状态 2 表示已退票

    # 恢复座位可选状态
    seat.status = 0
    seat.sold_to_user = None

    # 恢复场次余票库存，并递增版本（兼容乐观锁并发）
    showtime.remaining_inventory += 1
    showtime.version += 1

    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise InternalServerError(message=f"退票失败，系统繁忙: {str(e)}")

    return ResponseModel(data="退票成功，退款已秒级原路退回")
