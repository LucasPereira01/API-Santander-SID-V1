import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import os

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

# Obter URL do banco de dados a partir da variável de ambiente
DATABASE_URL = 'postgres://postgres:Soldadowolooko1@localhost:5432/postgres'
TARGET_DB = 'santander-cirrus'

def create_database():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()

        # Verificar se o banco de dados já existe
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TARGET_DB}'")
        exists = cur.fetchone()
        
        if not exists:
            cur.execute(f'CREATE DATABASE "{TARGET_DB}"')
            print(f"Banco de dados {TARGET_DB} criado com sucesso.")
        else:
            print(f"Banco de dados {TARGET_DB} já existe.")
        
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro ao criar o banco de dados: {error}")
    finally:
        if conn is not None:
            conn.close()

def create_tables():
    commands = (
        """
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        """,
        """
        CREATE TABLE IF NOT EXISTS parametro_status (
            code VARCHAR(3) NOT NULL,
            type VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            PRIMARY KEY (code)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS segmento (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            nome VARCHAR(255) NOT NULL UNIQUE,
            descricao TEXT,
            is_ativo BOOLEAN NOT NULL,
            sas_folder_id VARCHAR(255),
            sas_parent_uri VARCHAR(255),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS clusters (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            nome VARCHAR(100) NOT NULL,
            descricao TEXT,
            is_ativo BOOLEAN NOT NULL,
            sas_folder_id VARCHAR(255),
            sas_parent_uri TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            segmento_id UUID NOT NULL,
            FOREIGN KEY (segmento_id) REFERENCES segmento(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS politica (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            nome VARCHAR(100) NOT NULL,
            descricao TEXT NOT NULL,
            is_ativo BOOLEAN NOT NULL,
            sas_folder_id VARCHAR(255),
            sas_parent_uri TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            cluster_id UUID NOT NULL,
            FOREIGN KEY (cluster_id) REFERENCES clusters(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS parametrizador (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            versao VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            deleted_at TIMESTAMP,
            politica_id UUID NOT NULL,
            parametrizador_id UUID,
            usuario_id UUID NOT NULL,
            FOREIGN KEY (politica_id) REFERENCES politica(id),
            FOREIGN KEY (parametrizador_id) REFERENCES parametrizador(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS parametro (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            nome VARCHAR(100) NOT NULL,
            descricao TEXT,
            modo VARCHAR(10) NOT NULL,
            data_hora_vigencia TIMESTAMP NOT NULL,
            versao VARCHAR(255) NOT NULL,
            is_vigente BOOLEAN NOT NULL,
            sas_domain_id VARCHAR(255),
            sas_content_id VARCHAR(255),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            deleted_at TIMESTAMP,
            status_code VARCHAR(3) NOT NULL,
            parametro_parent_id UUID,
            politica_id UUID NOT NULL,
            sas_user_id VARCHAR(255) NOT NULL,
            FOREIGN KEY (parametro_parent_id) REFERENCES parametro(id),
            FOREIGN KEY (politica_id) REFERENCES politica(id),
            FOREIGN KEY (status_code) REFERENCES parametro_status(code)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS variavel (
            id UUID NOT NULL DEFAULT uuid_generate_v4(),
            nome VARCHAR(100) NOT NULL,
            descricao TEXT,
            tipo VARCHAR(255) NOT NULL,
            is_chave BOOLEAN NOT NULL,
            tamanho INTEGER NOT NULL,
            qtd_casas_decimais INTEGER,
            parametro_id UUID NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (parametro_id) REFERENCES parametro(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS variavel_lista (
            id UUID NOT NULL DEFAULT uuid_generate_v4(),
            nome VARCHAR(100) NOT NULL,
            is_visivel BOOLEAN NOT NULL,
            variavel_id UUID NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (variavel_id) REFERENCES variavel(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS dado (
            id UUID NOT NULL DEFAULT uuid_generate_v4(),
            informacao JSON NOT NULL,
            sas_key TEXT,
            sas_value TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            deleted_at TIMESTAMP,
            parametro_id UUID NOT NULL,
            PRIMARY KEY (id),
            FOREIGN KEY (parametro_id) REFERENCES parametro(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS parametrizador_sas (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            status VARCHAR(255) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            deleted_at TIMESTAMP,
            sas_id UUID,
            parametrizador_id UUID NOT NULL,
            FOREIGN KEY (parametrizador_id) REFERENCES parametrizador(id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS parametrizador_sas_historico (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            evento VARCHAR(255) NOT NULL,
            data_hora_ocorrencia TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            usuario_id UUID NOT NULL,
            parametrizador_sas_id UUID NOT NULL,
            FOREIGN KEY (parametrizador_sas_id) REFERENCES parametrizador_sas(id)
        );
        """
    )
    
    conn = None
    try:
        # Conectar ao banco de dados específico
        conn = psycopg2.connect(f'postgres://postgres:Soldadowolooko1@localhost:5432/{TARGET_DB}')
        cur = conn.cursor()
        # Criar cada tabela
        for command in commands:
            print(f"Executando comando: {command}")
            cur.execute(command)
        # Confirmar mudanças
        conn.commit()
        cur.close()
        print("Tabelas criadas com sucesso.")
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro ao criar tabelas: {error}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    create_database()
    create_tables()
