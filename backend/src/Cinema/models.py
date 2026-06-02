from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DECIMAL, INT, SMALLINT, TIMESTAMP, VARCHAR, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Auth.models import Base
from src.common import CommonAttr


class Movie(Base, CommonAttr):
    """
    电影数据表模型
    """

    __tablename__ = "movie"  # type: ignore[override]

    uid: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="电影主键UUID",
    )
    title: Mapped[str] = mapped_column(
        VARCHAR(100),
        nullable=False,
        comment="电影名称",
    )
    duration: Mapped[int] = mapped_column(
        INT,
        nullable=False,
        comment="电影时长(分钟)",
    )
    rating: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 1),
        nullable=False,
        default=Decimal("0.0"),
        comment="豆瓣评分",
    )
    genres: Mapped[str] = mapped_column(
        VARCHAR(100),
        nullable=False,
        default="",
        comment="电影类别",
    )
    summary: Mapped[str] = mapped_column(
        VARCHAR(500),
        nullable=False,
        default="",
        comment="安利推荐语",
    )


class CinemaRoom(Base, CommonAttr):
    """
    影厅数据表模型
    """

    __tablename__ = "cinema_room"  # type: ignore[override]

    uid: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="影厅主键UUID",
    )
    name: Mapped[str] = mapped_column(
        VARCHAR(50),
        nullable=False,
        comment="影厅名称",
    )
    total_seats: Mapped[int] = mapped_column(
        INT,
        nullable=False,
        comment="总座位数",
    )


class Showtime(Base, CommonAttr):
    """
    放映场次与排片表模型 (高并发争抢核心)
    """

    __tablename__ = "showtime"  # type: ignore[override]

    uid: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="场次主键UUID",
    )
    movie_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("movie.uid", name="fk_showtime_movie"),
        nullable=False,
        comment="关联电影ID",
    )
    room_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("cinema_room.uid", name="fk_showtime_room"),
        nullable=False,
        comment="关联影厅ID",
    )
    start_time: Mapped[TIMESTAMP] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        comment="放映时间",
    )
    price: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="票价",
    )
    remaining_inventory: Mapped[int] = mapped_column(
        INT,
        nullable=False,
        comment="剩余可用票数",
    )
    version: Mapped[int] = mapped_column(
        INT,
        default=1,
        nullable=False,
        comment="乐观锁版本号",
    )
    movie: Mapped["Movie"] = relationship(foreign_keys=[movie_id])
    room: Mapped["CinemaRoom"] = relationship(foreign_keys=[room_id])


class Seat(Base, CommonAttr):
    """
    场次座位状态表模型 (细粒度占位)
    """

    __tablename__ = "seat"  # type: ignore[override]

    uid: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="座位主键UUID",
    )
    showtime_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("showtime.uid", name="fk_seat_showtime"),
        nullable=False,
        comment="关联场次ID",
    )
    row_num: Mapped[int] = mapped_column(
        INT,
        nullable=False,
        comment="排号",
    )
    col_num: Mapped[int] = mapped_column(
        INT,
        nullable=False,
        comment="列号",
    )
    status: Mapped[int] = mapped_column(
        SMALLINT,
        default=0,
        nullable=False,
        comment="座位状态 (0: 可选, 1: 已售出)",
    )
    sold_to_user: Mapped[Optional[UUID]] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("users.uid", name="fk_seat_user"),
        nullable=True,
        comment="购票人UUID",
    )


class TicketOrder(Base, CommonAttr):
    """
    购票订单数据表模型
    """

    __tablename__ = "ticket_order"  # type: ignore[override]

    uid: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="订单主键UUID",
    )
    showtime_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("showtime.uid", name="fk_order_showtime"),
        nullable=False,
        comment="关联场次ID",
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("users.uid", name="fk_order_user"),
        nullable=False,
        comment="关联购票用户ID",
    )
    seat_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=True),
        ForeignKey("seat.uid", name="fk_order_seat"),
        nullable=False,
        comment="关联座位ID",
    )
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="支付金额",
    )
    status: Mapped[int] = mapped_column(
        SMALLINT,
        default=1,
        nullable=False,
        comment="订单状态 (1: 购票成功/已支付, 2: 已退票)",
    )
