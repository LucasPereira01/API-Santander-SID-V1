from dotenv import load_dotenv
import os
import psycopg2

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso à variável de ambiente DATABASE_URL
db_url = os.getenv("DATABASE_URL")


def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(db_url)
    return conn
