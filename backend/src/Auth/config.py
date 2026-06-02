from typing import Final

from passlib.context import CryptContext

from src.settings import config

TOKEN_URL = "/api/auth/token"
# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY: Final[str] = "180c3055d7ae1816e4084901378cbfa15aa84e7484c7bb782295771d0b5854e3"
ALGORITHM: Final[str] = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30
DEFAULT_TOKEN_EXPIRE_MINUTES: Final[int] = 15
REFRESH_TOKEN_EXPIRE_MINUTES: Final[int] = 300
PARSE_JWT_COUNT_PER_MINUTE: Final[int] = 60
PWD_CONTEXT: CryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
FLAG_USER_ROLE_COMMON: Final[int] = 0
FLAG_USER_ROLE_ADMIN: Final[int] = 1
FLAG_USER_ROLE_GUEST: Final[int] = 2
FLAG_GENDER_FEMALE: Final[int] = 0
FLAG_GENDER_MALE: Final[int] = 1
FLAG_GENDER_UNKNOW: Final[int] = 2
FLAG_USER_STATUS_NORMAL: Final[int] = 0
FLAG_USER_STATUS_ABNORMAL: Final[int] = 1
FLAG_USER_STATUS_LOCKED: Final[int] = 2


class AuthSettings:
    """认证与国密传输安全热配置"""

    BOOKING_SM4_PASSWORD_ENCRYPT: bool = config("BOOKING_SM4_PASSWORD_ENCRYPT", cast=bool, default=False)  # 登录密码国密SM4传输加密开关
    BOOKING_SM4_KEY: str = config("BOOKING_SM4_KEY", cast=str, default="hello_cinema_sm4")  # SM4 对称加密密钥，必须为16字节
    AUTH_STRONG_PASSWORD_CHECK: bool = config("AUTH_STRONG_PASSWORD_CHECK", cast=bool, default=False)  # 简单密码强度开关


auth_settings = AuthSettings()

if __name__ == "__main__":
    print(PWD_CONTEXT.hash("123456"))
    print(PWD_CONTEXT.verify("123456", "$2b$12$1aTB0U6EJLf5/Ot7SdwfpOhLv77evLV9u27bIsOnjir5bLfW1Gqt."))
