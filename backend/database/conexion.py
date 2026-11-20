import os
import pymysql

from dotenv import load_dotenv
from pymysql.cursors import DictCursor

load_dotenv()

def conectar():

    try:

        conexion = pymysql.connect(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 3306)),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),

            charset="utf8mb4",

            cursorclass=DictCursor,

            autocommit=False
        )

        print("Conexión exitosa con MariaDB")

        return conexion

    except pymysql.MySQLError as error:

        print("Error al conectar:", error)

        return None