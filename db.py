import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import DictCursor

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()


# Acesso à variável de ambiente DATABASE_URL
DATABASE_URL_DB_NAME = os.getenv("DATABASE_URL_DB_NAME")
DATABASE_URL_USER = os.getenv("DATABASE_URL_USER")
DATABASE_URL_PASSWORD = os.getenv("DATABASE_URL_PASSWORD")
DATABASE_URL_HOST = os.getenv("DATABASE_URL_HOST")
DATABASE_URL_PORTA = os.getenv("DATABASE_URL_PORTA")

# Função para obter conexão com o banco de dados usando DictCursor
def get_db_connection():
    try:
        conn = psycopg2.connect(
        dbname=DATABASE_URL_DB_NAME,
        user=DATABASE_URL_USER,
        password=DATABASE_URL_PASSWORD,
        host=DATABASE_URL_HOST,
        port=DATABASE_URL_PORTA,
        cursor_factory=DictCursor
    )
        return conn
    except psycopg2.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        raise

# Definindo DictCursor como o cursor padrão globalmente
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)




