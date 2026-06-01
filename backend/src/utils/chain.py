class Chain:
    def __init__(self, path=""):
        self._path = path

    def __getattr__(self, path):
        if path == "users":
            return lambda name: Chain(f"{self._path}/{name}")
        return Chain(f"{self._path}/{path}")

    def __str__(self):
        return self._path

    __repr__ = __str__
