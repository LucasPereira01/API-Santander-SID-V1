from flask import Flask, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from db import get_db_connection
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import re
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso à variável de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
URL_PATH_ANALYTICS_SID = os.getenv("URL_PATH_ANALYTICS_SID")
schema_db = os.getenv("SCHEMA_DB")
app = Flask(__name__)

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

def busca_all_cluster():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Executa a consulta com junção para obter dados dos clusters e segmentos
        cur.execute(f"""
            SELECT
                c.id, c.nome, c.descricao, c.is_ativo, c.sas_folder_id,
                c.sas_parent_uri,c.sas_test_folder_id,c.sas_test_parent_uri, c.created_at, c.updated_at, c.segmento_id,
                s.nome AS segmento_nome, s.is_ativo AS segmento_ativo
            FROM  {schema_db}.clusters c
            JOIN {schema_db}.segmento s ON c.segmento_id = s.id
        """)
        clusters = cur.fetchall()

        # Formata o resultado como uma lista de dicionários
        result = []
        for cluster in clusters:
            result.append({
                "id": cluster[0],
                "nome": cluster[1],
                "descricao": cluster[2],
                "is_ativo": cluster[3],
                "sas_folder_id": cluster[4],
                "sas_parent_uri": cluster[5],
                "sas_test_folder_id": cluster[6],
                "sas_test_parent_uri": cluster[7],
                "created_at": cluster[8],
                "updated_at": cluster[9],
                "segmento_id": cluster[10],
                "segmento": {
                    "id": cluster[10],
                    "nome": cluster[11],
                    "is_ativo": cluster[12]
                }
            })

        return jsonify(result)
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"error": "Falha ao tentar buscar os clusters"}), 500
    finally:
        cur.close()
        conn.close()


def buscar_cluster_id(cluster_id):
    conn = None

    has_association = False
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(f"SELECT cluster_id FROM  {schema_db}.politica WHERE cluster_id = %s", (cluster_id,))
        association = cur.fetchone()
        if association:
            has_association = True

        cur.execute(f"""
            SELECT
                c.id, c.nome, c.descricao, c.is_ativo, c.sas_folder_id,
                c.sas_parent_uri, c.created_at, c.updated_at, c.segmento_id,
                s.nome AS segmento_nome, s.is_ativo AS segmento_ativo
            FROM  {schema_db}.clusters c
            JOIN {schema_db}.segmento s ON c.segmento_id = s.id
            WHERE c.id = %s
        """, (cluster_id,))

        cluster = cur.fetchone()
        if cluster:
            result = {
                "id": cluster[0],
                "nome": cluster[1],
                "descricao": cluster[2],
                "is_ativo": cluster[3],
                "sas_folder_id": cluster[4],
                "sas_parent_uri": cluster[5],
                "created_at": cluster[6],
                "updated_at": cluster[7],
                "segmento_id": cluster[8],
                "has_association":has_association,
                "segmento": {
                    "id": cluster[8],
                    "nome": cluster[9],
                    "segmento_ativo": cluster[10]
                }
            }
            
            return jsonify(result)
        else:
            return jsonify({"error": "Cluster não encontrado"}), 404
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro ao buscar o cluster: {error}")
        return jsonify({"error": f"Erro ao buscar o cluster: {error}"}), 500
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def criar_cluster_data_base():
        data = request.get_json()
        nome = data.get('nome')
        segmento_id = data.get('segmento_id')
        descricao = data.get('descricao', '')
        is_ativo = data.get('is_ativo', True)

            # Verificar se 'is_ativo' está presente no JSON e é um valor booleano
        if "is_ativo" not in data or not isinstance(data["is_ativo"], bool):
            return jsonify({"error": "'is_ativo' é obrigatório e deve ser um booleano","campos_error":["is_ativo"]}), 400

        if not nome:
            return jsonify({"error": "'nome' é obrigatório","campos_error":["nome"]}), 400
    
        elif not descricao:
            return jsonify({"error": "'descricao' é obrigatório ","campos_error":["descricao"]}), 400
        # Verificar se 'nome' e 'descricao' estão presentes e são válidos

        elif not segmento_id:
            return jsonify({"error": "'segmento_id' é obrigatório ","campos_error":["segmento_id"]}), 400
        # Verificar se 'nome' e 'descricao' estão presentes e são válidos

        elif len(descricao) > 350:
            return jsonify({"error": "Descrição deve ter no máximo 350 caracteres","campos_error":["descricao"]}), 400

        
        # Validação do campo 'nome' usando expressão regular
        name_regex = re.compile(r"^[A-Za-z0-9_]+$")
        if not name_regex.match(nome):
             return jsonify({"error": "Nome deve conter apenas letras, números ou underscores","campos_error":["nome"]}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM  {schema_db}.clusters WHERE nome = %s AND segmento_id = %s",(nome, segmento_id))
        existing_cluster = cur.fetchone()

        if existing_cluster:
            return jsonify({"error":"Nome do cluster ja existe para este segmento","campos_error":["nome"]}),400
        
        cur.execute(f"SELECT * FROM  {schema_db}.segmento WHERE id = %s",(segmento_id,))
        segmento = cur.fetchone()
        if not segmento:
            return jsonify({"error":"Segmento nao encontrado"}),400
    
        cluster_id = str(uuid.uuid4())
        try:
            
            # Insere os dados do cluster no banco de dados
            cur.execute(f"""
                INSERT INTO {schema_db}.clusters (id, nome, descricao, is_ativo,segmento_id) 
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (cluster_id, nome, descricao, is_ativo, segmento_id))
            cluster_id = cur.fetchone()[0]

            conn.commit()
            return jsonify({"message": "Cluster Criado com Sucesso", "id": cluster_id}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            cur.close()
            conn.close()


def edit_cluster(cluster_id):
    data = request.get_json()
    descricao = data.get('descricao', '')
    nome = data.get('nome')
    segmento_id = data.get('segmento_id')
    is_ativo = data.get('is_ativo', True)

    # Verificar se 'is_ativo' está presente no JSON e é um valor booleano
    if "is_ativo" not in data or not isinstance(data["is_ativo"], bool):
        return jsonify({"error": "'is_ativo' é obrigatório e deve ser um booleano", "campos_error": ["is_ativo"]}), 400

    if not cluster_id:
        return jsonify({"error": "cluster_id é obrigatório", "campos_error": ["cluster_id"]}), 400
    
    if not descricao:
        return jsonify({"error": "'descricao' é obrigatório ", "campos_error": ["descricao"]}), 400

    if len(descricao) > 350:
        return jsonify({"error": "Descrição deve ter no máximo 350 caracteres", "campos_error": ["descricao"]}), 400
    
    # Validação do campo 'nome' usando expressão regular
    name_regex = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_regex.match(nome):
         return jsonify({"error": "Nome deve conter apenas letras, números ou underscores","campos_error":["nome"]}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    updated_at = datetime.now()
    has_association = False
    try:
        # verifica se existe o id na tabela
        cur.execute(f"SELECT 1 FROM  {schema_db}.clusters WHERE id = %s", (cluster_id,))
        cluster_existe = cur.fetchone()

        if not cluster_existe:
            return jsonify({"error": "Cluster não encontrado"}), 404

        # Verifica se há alguma associação do cluster com políticas
        cur.execute(f"SELECT cluster_id FROM  {schema_db}.politica WHERE cluster_id = %s", (cluster_id,))
        association = cur.fetchone()
        if association:
            has_association = True

        # Atualiza apenas se houver nome na requisição ou se não houver associação com políticas
        if has_association and nome:
            return jsonify({"error": "O 'nome' não pode ser alterado, está associado a uma Política", "campos_error": ["nome"]})
        
        cur.execute(f"SELECT * FROM  {schema_db}.clusters WHERE nome = %s AND segmento_id = %s",(nome, segmento_id))
        existing_cluster = cur.fetchone()

        if existing_cluster:
            return jsonify({"error":"Nome do cluster ja existe para este segmento","campos_error":["nome"]}),400

        if nome:
            query = f"""
                UPDATE {schema_db}.clusters
                SET nome = %s, descricao = %s, is_ativo = %s, updated_at = %s ,segmento_id = %s
                WHERE id = %s
            """
            params = (nome, descricao, is_ativo, updated_at, segmento_id, cluster_id)
        else:
            query = f"""
                UPDATE {schema_db}.clusters
                SET descricao = %s, is_ativo = %s, updated_at = %s
                WHERE id = %s
            """
            params = (descricao, is_ativo, updated_at, cluster_id)
        
        cur.execute(query, params)
        conn.commit()

        return jsonify({"message": "Cluster Atualizado com Sucesso", "id": cluster_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


def delete_cluster(cluster_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Verifica se o cluster existe
        cur.execute(f"SELECT 1 FROM  {schema_db}.clusters WHERE id = %s", (cluster_id,))
        cluster_existe = cur.fetchone()

        if not cluster_existe:
            return jsonify({"error": "Cluster não encontrado"}), 404

        # Verifica se o cluster está associado a alguma política
        cur.execute(f"SELECT cluster_id FROM  {schema_db}.politica WHERE cluster_id = %s", (cluster_id,))
        association = cur.fetchone()

        if association:
            return jsonify({"error": "Não é possível excluir o cluster pois está associado a uma política", "campos_error": ["cluster_associado"]}), 400
        else:
            cur.execute(f"DELETE FROM  {schema_db}.clusters WHERE id = %s", (cluster_id,))
            conn.commit()
            return jsonify({"message": "Cluster excluído com sucesso"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()