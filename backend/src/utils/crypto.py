from hashlib import md5


async def get_md5(key: str) -> str:
    """return a md5 string"""
    return md5(key.encode(encoding="utf-8")).hexdigest()
