from flask import Flask, make_response, request, jsonify
import uuid
from datetime import datetime
from db import get_db_connection
import requests
import re
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso à variável de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
url_path_sid_analytics = os.getenv("URL_PATH_ANALYTICS_SID")
schema_db = os.getenv("SCHEMA_DB")

app = Flask(__name__)

def create_segmento_data_base():
    data = request.get_json()
    
    # Verificar se 'is_ativo' está presente no JSON e é um valor booleano
    if "is_ativo" not in data or not isinstance(data["is_ativo"], bool):
        return jsonify({"error": "'is_ativo' é obrigatório e deve ser um booleano","campos_error":["is_ativo"]}), 400

    nome = data.get('nome')
    descricao = data.get('descricao', '')

    if not nome:
        return jsonify({"error": "'nome' é obrigatório","campos_error":["nome"]}), 400
    
    elif not descricao:
        return jsonify({"error": "'descricao' é obrigatório ","campos_error":["descricao"]}), 400

    # Verificar se 'nome' e 'descricao' estão presentes e são válidos
    elif len(descricao) > 350:
        return jsonify({"error": "Descrição deve ter no máximo 350 caracteres","campos_error":["descricao"]}), 400

    # Validação do campo 'nome' usando expressão regular
    name_regex = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_regex.match(nome):
        return jsonify({"error": "Nome deve conter apenas letras, números ou underscores","campos_error":["nome"]}), 400

    # Pegar o valor de 'is_ativo' do JSON
    is_ativo = data.get('is_ativo', True)

    conn = get_db_connection()
    cur = conn.cursor()
    segmento_id = str(uuid.uuid4())
    try:
        cur.execute(f"SELECT * FROM {schema_db}.segmento WHERE nome = %s",(nome,))
        existing_cluster = cur.fetchone()
        if existing_cluster: 
            return jsonify({"error": "O segmento ja existe","campos_error":["nome"]}), 400
        
        cur.execute(
            f"""
            INSERT INTO {schema_db}.segmento (id, nome, descricao, is_ativo)
            VALUES (%s, %s, %s, %s)
            """,
            (segmento_id, nome, descricao, is_ativo)
        )
        conn.commit()

            
        return jsonify({"message": "Segmento Criado com Sucesso", "id": segmento_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


def edit_segmento(segmento_id):
    data = request.get_json()
    nome = data.get('nome')
    descricao = data.get('descricao', '')
    is_ativo = data.get('is_ativo', True)

     # Verificar se 'is_ativo' está presente no JSON e é um valor booleano
    if "is_ativo" not in data or not isinstance(data["is_ativo"], bool):
        return jsonify({"error": "'is_ativo' é obrigatório e deve ser um booleano","campos_error":["is_ativo"]}), 400

    if not segmento_id:
        return jsonify({"error": "segmento_id é obrigatório","campos_error":["segmento_id"]}), 400
    
    if not descricao:
        return jsonify({"error": "'descricao' é obrigatório","campos_error":["descricao"]}), 400

    if len(descricao) > 350:
        return jsonify({"error": "Descrição deve ter no máximo 350 caracteres","campos_error":["descricao"]}), 400
    
    # Validação do campo 'nome' usando expressão regular
    if nome is not None:
        name_regex = re.compile(r"^[A-Za-z0-9_]+$")
        if not name_regex.match(nome):
            return jsonify({"error": "Nome deve conter apenas letras, números ou underscores","campos_error":["nome"]}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    updated_at = datetime.now()
    
    has_association = False

    try:
        # verifica se existe o id na tabela
        cur.execute(f"SELECT 1 FROM {schema_db}.segmento WHERE id = %s",(segmento_id,))
        segmento_existe = cur.fetchone()

        if not segmento_existe:
            return jsonify({"error":"Segmento nao encontrado"}),404
        
        cur.execute(f"SELECT segmento_id FROM {schema_db}.clusters WHERE segmento_id = %s", (segmento_id,))
        association = cur.fetchone()

        if association:
            has_association = True

        if has_association and nome:
            return jsonify({"error": "O 'nome' nao pode ser alterado, esta associado a um cluster","campos_error":["nome"]})
        
        # verificar se o nome ja existe, se ele existe
        if nome and not has_association:
            cur.execute(f"SELECT * FROM {schema_db}.segmento WHERE nome = %s AND id != %s",(nome,segmento_id,))
            existing_cluster = cur.fetchone()
            

            if existing_cluster: 
                return jsonify({"error": "O segmento ja existe","campos_error":["nome"]}), 400    

            query = f"""
                UPDATE {schema_db}.segmento
                SET nome = %s, descricao = %s, is_ativo = %s, updated_at = %s
                WHERE id = %s
            """
            params = (nome, descricao, is_ativo, updated_at, segmento_id)
        else:
            query = f"""
                UPDATE {schema_db}.segmento
                SET descricao = %s, is_ativo = %s, updated_at = %s
                WHERE id = %s
            """
            params = (descricao, is_ativo, updated_at, segmento_id)
        
        cur.execute(query, params)
        conn.commit()

        return jsonify({"message": "Segmento Atualizado com Sucesso","id":segmento_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()



def list_segmentos():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(f"SELECT id, nome, descricao, is_ativo, sas_folder_id, sas_parent_uri,sas_test_folder_id, sas_test_parent_uri FROM {schema_db}.segmento")
        segmentos = cur.fetchall()
        result = [
            {
                "id": row[0],
                "nome": row[1],
                "descricao": row[2],
                "is_ativo": row[3],
                "sas_folder_id": row[4],
                "sas_parent_uri": row[5],
                "sas_test_folder_id": row[6],
                "sas_test_parent_uri": row[7]
            }
            for row in segmentos
        ]
        return result
    except Exception as e:
        print(f"Erro ao listar segmentos: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def list_segmentos_id(segmento_id):
    has_association = False
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT id, nome, descricao, is_ativo, sas_folder_id, sas_parent_uri FROM {schema_db}.segmento WHERE id = %s", (segmento_id,))
        segmento = cur.fetchone()
        if segmento:
            # Usando a função de associação para verificar se há alguma associação do segmento com clusters
            # Verifica se há alguma associação do segmento com clusters
            cur.execute(f"SELECT segmento_id FROM {schema_db}.clusters WHERE segmento_id = %s", (segmento_id,))
            association = cur.fetchone()
            if association:
                has_association = True

            result = {
                "id": segmento[0],
                "nome": segmento[1],
                "descricao": segmento[2],
                "is_ativo": segmento[3],
                "sas_folder_id": segmento[4],
                "sas_parent_uri": segmento[5],
                "has_association": has_association
            }
            return result
        else:
            return jsonify({"error": "Segmento não encontrado"}), 500
    except Exception as e:
        print(f"Erro ao listar segmentos: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def delete_segmento(segmento_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Verifica se o segmento existe
        cur.execute(f"SELECT 1 FROM {schema_db}.segmento WHERE id = %s", (segmento_id,))
        segmento_existe = cur.fetchone()

        if not segmento_existe:
            return jsonify({"error": "Segmento não encontrado"}), 404

        # Verifica se o segmento está associado a algum cluster
        cur.execute(f"SELECT segmento_id FROM {schema_db}.clusters WHERE segmento_id = %s", (segmento_id,))
        association = cur.fetchone()

        if association:
            return jsonify({"error": "Não é possível excluir o segmento pois está associado a um cluster","campos_error":["segmento_associado"]}), 400
        else:
            cur.execute(f"DELETE FROM {schema_db}.segmento WHERE id = %s", (segmento_id,))
            conn.commit()
            return jsonify({"message": "Segmento excluído com sucesso"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
