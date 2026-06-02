from src.settings import config


class CinemaSettings:
    """影院核心业务高并发与安全热配置"""

    BOOKING_LOCK_MODE: str = config("BOOKING_LOCK_MODE", cast=str, default="pessimistic")  # 'none' 无锁, 'pessimistic' 悲观锁, 'optimistic' 乐观锁
    CINEMA_SLOW_QUERY: bool = config("CINEMA_SLOW_QUERY", cast=bool, default=False)  # 慢查询开关
    BOOKING_SIGNATURE_CHECK: bool = config("BOOKING_SIGNATURE_CHECK", cast=bool, default=False)  # 接口签名校验开关
    BOOKING_SIGNATURE_SECRET: str = config("BOOKING_SIGNATURE_SECRET", cast=str, default="hello_cinema_range_secret_key")  # 签名秘钥，以.env配置优先级最高
    BOOKING_SM3_SIGNATURE_CHECK: bool = config("BOOKING_SM3_SIGNATURE_CHECK", cast=bool, default=False)  # 接口国密SM3签名校验开关


cinema_settings = CinemaSettings()
