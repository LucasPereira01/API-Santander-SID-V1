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

app = Flask(__name__)

def create_segmento(token,global_uri):
    data = request.get_json()
    # Verifica se o cabeçalho Authorization está presente na requisição
    

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
    if 'Authorization' in request.headers:
        token = request.headers.get('Authorization').split('Bearer ')[1]
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.sas.content.folder+json, application/json"
    }

    segmento_id = str(uuid.uuid4())
    payload = {
        "name": nome,
        "description": descricao,
        "type": "folder"
    }
    
    try:
        url = f"{url_path_sid}/folders/folders"

        if global_uri is not None:
            path_segmentos = {"parentFolderUri": global_uri["uri"]}  # Define o path_segmentos se a pasta raiz foi encontrada
            response = requests.post(url, json=payload, headers=headers, params=path_segmentos, verify=False)
        else:
            response = requests.post(url, json=payload, headers=headers, verify=False)

        if response.status_code != 201:
            cur.execute("SELECT * FROM segmento WHERE nome = %s",(nome,))
            existing_cluster = cur.fetchone()
            if existing_cluster: 
                return jsonify({"error": "O segmento ja existe","campos_error":["nome"]}), 400
            error_type = response.json()
            raise Exception("Falha ao criar o segmento no SAS Intelligence Design ", error_type["message"])
        
        response_data = response.json()

        sas_folder_id = response_data.get("id")
        if 'links' in response_data and len(response_data['links']) > 0:
            sas_parent_uri = response_data['links'][0]['uri']
        else:
            sas_parent_uri = None
        
        if not sas_folder_id or not sas_parent_uri:
            raise Exception("'parentFolderUri' or 'id' not found in response data")
        
        cur.execute(
            """
            INSERT INTO segmento (id, nome, descricao, is_ativo, sas_folder_id, sas_parent_uri)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (segmento_id, nome, descricao, is_ativo, sas_folder_id, sas_parent_uri)
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

    conn = get_db_connection()
    cur = conn.cursor()

    updated_at = datetime.now()

    try:
        # verifica se exite o id na table
        cur.execute("SELECT 1 FROM  segmento WHERE id = %s",(segmento_id,))
        segmento_existe = cur.fetchone()

        if not segmento_existe:
            return jsonify({"error":"Segmento nao encontrado"}),404
        
        cur.execute(
            """
            UPDATE segmento
            SET descricao = %s, is_ativo = %s, updated_at = %s
            WHERE id = %s
            """,
            (descricao, is_ativo, updated_at, segmento_id)
        )
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
        cur.execute("SELECT id, nome, descricao, is_ativo, sas_folder_id, sas_parent_uri FROM segmento")
        segmentos = cur.fetchall()
        result = [
            {
                "id": row[0],
                "nome": row[1],
                "descricao": row[2],
                "is_ativo": row[3],
                "sas_folder_id": row[4],
                "sas_parent_uri": row[5]
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
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, nome, descricao, is_ativo, sas_folder_id, sas_parent_uri  FROM segmento WHERE id = %s",(segmento_id,))
        segmento = cur.fetchone()
        
        if segmento:
            result = {
                "id": segmento[0],
                "nome": segmento[1],
                "descricao": segmento[2],
                "is_ativo": segmento[3],
                "sas_folder_id": segmento[4],
                "sas_parent_uri ": segmento[5]
            }
        else:
           return jsonify({"error": "Segmento não encontrado"}), 500

        return result
    except Exception as e:
        print(f"Erro ao listar segmentos: {e}")
        return None
    finally:
        cur.close()
        conn.close()
