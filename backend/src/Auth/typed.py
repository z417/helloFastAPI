from pydantic import constr

_NameType = constr(
    pattern=r"^[A-Za-z0-9-_]+$",
    to_lower=False,
    strip_whitespace=True,
    min_length=1,
    max_length=16,
)

_EmailStrType = constr(
    pattern=r"^[A-Za-z0-9]+([_\.][A-Za-z0-9]+)*@([A-Za-z0-9\-]+\.)+[A-Za-z]{2,7}$",
    to_lower=True,
    strip_whitespace=True,
    max_length=50,
)

__all__ = ["_NameType", "_EmailStrType"]
