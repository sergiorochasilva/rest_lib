import os
import sqlalchemy

from rest_lib.settings import DATABASE_HOST
from rest_lib.settings import DATABASE_PASS
from rest_lib.settings import DATABASE_PORT
from rest_lib.settings import DATABASE_NAME
from rest_lib.settings import DATABASE_USER
from rest_lib.settings import DATABASE_DRIVER
from rest_lib.settings import CLOUD_SQL_CONN_NAME
from rest_lib.settings import ENV
from rest_lib.settings import DB_POOL_SIZE


def create_url(
    username: str,
    password: str,
    host: str,
    port: str,
    database: str,
    db_dialect: str = "postgresql+pg8000",
):
    return sqlalchemy.engine.URL.create(
        db_dialect,
        username=username,
        password=password,
        host=host,
        port=int(port),
        database=database,
    )


def create_pool(database_conn_url):
    # Creating database connection pool
    db_pool = sqlalchemy.create_engine(
        database_conn_url,
        # pool_size=DB_POOL_SIZE,
        # max_overflow=2,
        # pool_timeout=30,
        # pool_recycle=1800,
        poolclass=sqlalchemy.pool.NullPool,
    )
    return db_pool


if os.getenv("ENV") != "erp_sql":
    if DATABASE_DRIVER.upper() in ["SINGLE_STORE", "MYSQL"]:
        database_conn_url = create_url(
            DATABASE_USER,
            DATABASE_PASS,
            DATABASE_HOST,
            DATABASE_PORT,
            DATABASE_NAME,
            "mysql+pymysql",
        )
        # database_conn_url = f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASS}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
    else:
        if ENV.upper() == "GCP":
            database_conn_url = f"postgresql+pg8000://{DATABASE_USER}:{DATABASE_PASS}@/{DATABASE_NAME}?unix_sock=/cloudsql/{CLOUD_SQL_CONN_NAME}/.s.PGSQL.{DATABASE_PORT}"
        else:
            database_conn_url = create_url(
                DATABASE_USER,
                DATABASE_PASS,
                DATABASE_HOST,
                DATABASE_PORT,
                DATABASE_NAME,
            )
            # database_conn_url = f"postgresql+pg8000://{DATABASE_USER}:{DATABASE_PASS}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"


def default_create_pool():
    return create_pool(database_conn_url)


# db_pool = create_pool(database_conn_url)
