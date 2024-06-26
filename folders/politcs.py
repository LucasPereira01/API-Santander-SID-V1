from flask import Flask, request, jsonify
import psycopg2
import uuid
import re
from datetime import datetime
from db import get_db_connection
import requests
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso à variável de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
URL_PATH_ANALYTICS_SID = os.getenv("URL_PATH_ANALYTICS_SID")

app = Flask(__name__)

def criar_politica(token):
        # Obtém os dados da requisição JSON
        data = request.get_json()
        
        # Extrai os dados do JSON
        nome = data.get('nome')
        cluster_id = data.get('cluster_id')
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

        elif not cluster_id:
                return jsonify({"error": "'cluster_id' é obrigatório ","campos_error":["cluster_id"]}), 400
            # Verificar se 'nome' e 'descricao' estão presentes e são válidos

        elif len(descricao) > 350:
                return jsonify({"error": "Descrição deve ter no máximo 350 caracteres","campos_error":["descricao"]}), 400

            
            # Validação do campo 'nome' usando expressão regular
        name_regex = re.compile(r"^[A-Za-z0-9_]+$")
        if not name_regex.match(nome):
            return jsonify({"error": "Nome deve conter apenas letras, números ou underscores","campos_error":["nome"]}), 400


        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM politica WHERE nome = %s AND cluster_id = %s",(nome,cluster_id))
        existing_cluster = cur.fetchone()

        if existing_cluster:
            return jsonify({"error":"Nome do Politica ja existe para este Cluster","campos_error":["nome"]}),400
        
        cur.execute("SELECT * FROM clusters WHERE id = %s",(cluster_id,))
        cluster = cur.fetchone()
        if not cluster:
            return jsonify({"error":"Cluster nao encontrado"}),400
        

        sas_parent_uri_cluster = cluster[5]
        if 'Authorization' in request.headers:
            token = request.headers.get('Authorization').split('Bearer ')[1]

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.sas.content.folder+json, application/json"
        }

        politica_id = str(uuid.uuid4())
        payload = {
            "name": nome,
            "description": descricao,
            "type": "folder"
        }
        try:

            url = f"{url_path_sid}/folders/folders"

            path_cluster = {"parentFolderUri": sas_parent_uri_cluster}  # Define o path_cluster se a pasta raiz foi encontrada
            
            # Realiza a solicitação POST
            response = requests.post(url, json=payload, headers=headers, params=path_cluster, verify=False)

            if response.status_code != 201:
                cur.execute("SELECT * FROM politica WHERE nome = %s",(nome,))
                existing_cluster = cur.fetchone()
                if existing_cluster:
                    return jsonify({"error": "A Politica ja existe","campos_error":["nome"]}), 400
                error_type = response.json()
                raise Exception("Falha ao criar a Politica no SAS Intelligence Design ", error_type["message"])
            
            # Verifica se a solicitação foi bem-sucedida
            response.raise_for_status()

            # Processa a resposta JSON
            response_data = response.json()
            
            # Obtém os dados relevantes da resposta
            sas_folder_id = response_data.get("id")
            sas_parent_uri = response_data.get("links", [{}])[0].get("uri")

            # Verifica se os dados necessários foram obtidos
            if not sas_folder_id or not sas_parent_uri:
                return jsonify({"error": "'parentFolderUri' or 'id' not found in response data"}), 500
            
            # Insere os dados do cluster no banco de dados
            cur.execute("""
                INSERT INTO politica (id, nome, descricao, is_ativo, sas_folder_id, sas_parent_uri, cluster_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (politica_id, nome, descricao, is_ativo, sas_folder_id, sas_parent_uri, cluster_id))
            politica_id = cur.fetchone()[0]

            conn.commit()
            return jsonify({"message": "Politica Criada com Sucesso", "id": politica_id}), 201
        except Exception as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            if conn is not None:
                conn.close()



def edit_politica(politica_id):
    data = request.get_json()
    descricao = data.get('descricao', '')
    is_ativo = data.get('is_ativo', True)

    # Verificar se 'is_ativo' está presente no JSON e é um valor booleano
    if "is_ativo" not in data or not isinstance(data["is_ativo"], bool):
        return jsonify({"error": "'is_ativo' é obrigatório e deve ser um booleano","campos_error":["is_ativo"]}), 400
    
    elif not descricao:
        return jsonify({"error": "'descricao' é obrigatório ","campos_error":["descricao"]}), 400

    elif not politica_id:
            return jsonify({"error": "'politica_id' é obrigatório ","campos_error":["politica_id"]}), 400

    elif len(descricao) > 350:
                return jsonify({"error": "Descrição deve ter no máximo 350 caracteres","campos_error":["descricao"]}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    updated_at = datetime.now()

    try:
        # verifica se exite o id na table
        cur.execute("SELECT 1 FROM  politica WHERE id = %s",(politica_id,))
        politica_existe = cur.fetchone()

        if not politica_existe:
            return jsonify({"error":"Politica nao encontrado"}),404

        cur.execute(
            """
            UPDATE politica
            SET descricao = %s, is_ativo = %s, updated_at = %s
            WHERE id = %s
            """,
            (descricao, is_ativo, updated_at, politica_id)
        )
        conn.commit()

        return jsonify({"message": "Politica Atualizada com Sucesso","id":politica_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


def busca_all_politica():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        

        cur.execute("""SELECT p.id, p.nome, p.descricao, p.is_ativo, p.sas_folder_id, p.sas_parent_uri, p.created_at, p.updated_at, p.cluster_id,
                    c.nome AS cluster_nome, c.is_ativo AS cluster_ativo, s.id ,s.nome AS segmento_name, s.is_ativo AS segmento_ativo
                     FROM politica p
                    JOIN clusters c ON p.cluster_id = c.id
                    JOIN segmento s ON c.segmento_id = s.id
                """)
        clusters = cur.fetchall()

        result = []
        for cluster in clusters:
            result.append({
                "id": cluster[0],
                "nome": cluster[1],
                "descricao": cluster[2],
                "is_ativo": cluster[3],
                "sas_folder_id": cluster[4],
                "sas_parent_uri": cluster[5],
                "created_at": cluster[6],
                "updated_at": cluster[7],
                "cluster_id": cluster[8],
                "cluster": {
                    "id": cluster[8],
                    "nome": cluster[9],
                    "cluster_ativo": cluster[10],
                    "segmento": {
                        "id": cluster[11],
                        "nome": cluster[12],
                        "segmento_ativo": cluster[13]
                    }
                }
            })

        return jsonify(result)
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro ao buscar as politicas: {error}")
        return jsonify({"error": "Failed to retrieve politicas"}), 500
    finally:
        if conn is not None:
            conn.close()



def list_politica_id(politica_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                p.id, p.nome, p.descricao, p.is_ativo, p.sas_folder_id, p.sas_parent_uri, p.created_at, p.updated_at, 
                c.id AS cluster_id, c.nome AS cluster_nome, c.is_ativo AS cluster_ativo, 
                s.id AS segmento_id, s.nome AS segmento_nome, s.is_ativo AS segmento_ativo
            FROM politica p
            JOIN clusters c ON p.cluster_id = c.id
            JOIN segmento s ON c.segmento_id = s.id
            WHERE p.id = %s
        """, (politica_id,))
        politica = cur.fetchone()
        
        if politica:
            result = {
                "id": politica[0],
                "nome": politica[1],
                "descricao": politica[2],
                "is_ativo": politica[3],
                "sas_folder_id": politica[4],
                "sas_parent_uri": politica[5],
                "created_at": politica[6],
                "updated_at": politica[7],
                "cluster_id": politica[8],
                "cluster": {
                    "id": politica[8],
                    "nome": politica[9],
                    "cluster_ativo": politica[10],
                    "segmento": {
                        "id": politica[11],
                        "nome": politica[12],
                        "segmento_ativo": politica[13]
                    }
                }
            }
        else:
            return jsonify({"error": "Política não encontrada"}), 404

        return jsonify(result)
    except Exception as e:
        print(f"Erro ao listar política: {e}")
        return None
    finally:
        cur.close()
        conn.close()