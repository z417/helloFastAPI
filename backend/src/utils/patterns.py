from functools import wraps


def singleton(cls):
    """
    singleton pattern decorator
    :param cls: the object you want to set singleton
    :return:
    """
    instances = {}

    @wraps(cls)
    def _wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _wrapper
