from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.common import BaseModel


class MovieSchema(BaseModel):
    """
    电影基础模型
    """

    uid: UUID
    title: str
    duration: int
    rating: Decimal
    genres: str
    summary: str


class CinemaRoomSchema(BaseModel):
    """
    影厅基础模型
    """

    uid: UUID
    name: str
    total_seats: int


class ShowtimeResponseSchema(BaseModel):
    """
    排片场次返回模型
    """

    uid: UUID
    movie: MovieSchema
    room: CinemaRoomSchema
    start_time: datetime
    price: Decimal
    remaining_inventory: int


class SeatResponseSchema(BaseModel):
    """
    座位状态返回模型
    """

    uid: UUID
    row_num: int
    col_num: int
    status: int  # 0: 可选, 1: 已售出


class CreateOrderSchema(BaseModel):
    """
    购票下单请求模型 (下单选座即代表成功购票)
    """

    showtime_id: UUID
    seat_id: UUID
    signature: str | None = None


class OrderResponseSchema(BaseModel):
    """
    购票订单返回模型
    """

    uid: UUID
    showtime_id: UUID
    seat_id: UUID
    amount: Decimal
    status: int  # 1: 购票成功


class ConfigResponseSchema(BaseModel):
    """
    靶场参数配置返回模型
    """

    pool_mode: str
    lock_mode: str
    slow_query: bool
    signature_check: bool
    signature_secret: str
    signature_sm3_check: bool
    sm4_password_encrypt: bool
    sm4_key: str


class UpdateConfigSchema(BaseModel):
    """
    靶场参数配置热调修改请求模型
    """

    pool_mode: str  # 'queue' 或 'null'
    lock_mode: str  # 'none'、'pessimistic' 或 'optimistic'
    slow_query: bool
    signature_check: bool
    signature_sm3_check: bool = False
    sm4_password_encrypt: bool = False


class ShowtimeListResponseSchema(BaseModel):
    """
    排片场次分页返回包裹模型
    """

    total: int
    showtimes: list[ShowtimeResponseSchema]


class UserOrderResponseSchema(BaseModel):
    """
    用户已购票详情响应模型
    """

    uid: UUID
    showtime_id: UUID
    amount: Decimal
    status: int
    created_at: datetime
    movie_title: str
    movie_duration: int
    room_name: str
    start_time: datetime
    row_num: int
    col_num: int
