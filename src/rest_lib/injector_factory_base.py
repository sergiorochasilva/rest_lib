from sqlalchemy.engine.base import Connection

db_pool = None


class NsjInjectorFactoryBase:
    _db_connection: Connection

    def __enter__(self):
        from rest_lib.db_pool_config import default_create_pool

        if db_pool is not None:
            pool = db_pool
        else:
            pool = default_create_pool()

        self._db_connection = pool.connect()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._db_connection.close()

    def db_adapter(self):
        from rest_lib.util.db_adapter2 import DBAdapter2

        return DBAdapter2(self._db_connection)

    def get_service_by_name(self, name: str):
        if not hasattr(self, name):
            raise Exception(f"Service not found: {name}")

        service_method = getattr(self, name)

        return service_method()
