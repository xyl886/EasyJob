class EntityBase:
    def dict(self):
        return {
            k: v
            for k, v in self.__class__.__dict__.items()
            if not k.startswith("__") and not callable(v)
        } | self.__dict__
