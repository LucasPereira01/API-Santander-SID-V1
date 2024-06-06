from flask import Flask, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from db import get_db_connection
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import re
import requests
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso à variável de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
URL_PATH_ANALYTICS_SID = os.getenv("URL_PATH_ANALYTICS_SID")

app = Flask(__name__)

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

def busca_all_cluster():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Executa a consulta com junção para obter dados dos clusters e segmentos
        cur.execute("""
            SELECT
                c.id, c.nome, c.descricao, c.is_ativo, c.sas_folder_id,
                c.sas_parent_folder_uri, c.created_at, c.updated_at, c.segmento_id,
                s.nome AS segmento_nome, s.is_ativo AS segmento_ativo
            FROM clusters c
            JOIN segmento s ON c.segmento_id = s.id
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
                "sas_parent_folder_uri": cluster[5],
                "created_at": cluster[6],
                "updated_at": cluster[7],
                "segmento_id": cluster[8],
                "segmento": {
                    "id": cluster[8],
                    "nome": cluster[9],
                    "segmento_ativo": cluster[10]
                }
            })

        return jsonify(result)
    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"error": "Falha ao tentar buscar o clusters"}), 500
    finally:
        cur.close()
        conn.close()


def buscar_cluster_id(cluster_id):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                c.id, c.nome, c.descricao, c.is_ativo, c.sas_folder_id,
                c.sas_parent_folder_uri, c.created_at, c.updated_at, c.segmento_id,
                s.nome AS segmento_nome, s.is_ativo AS segmento_ativo
            FROM clusters c
            JOIN segmento s ON c.segmento_id = s.id
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
                "sas_parent_folder_uri": cluster[5],
                "created_at": cluster[6],
                "updated_at": cluster[7],
                "segmento_id": cluster[8],
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



def criar_cluster(token,segmento_id):
        data = request.get_json()
        nome = data.get('nome')
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

        cur.execute("SELECT * FROM clusters WHERE nome = %s AND segmento_id = %s",(nome,segmento_id))
        existing_cluster = cur.fetchone()

        if existing_cluster:
            return jsonify({"error":"Nome do cluster ja existe para este segmento","campos_error":["nome"]}),400
        
        cur.execute("SELECT * FROM segmento WHERE id = %s",(segmento_id,))
        segmento = cur.fetchone()
        if not segmento:
            return jsonify({"error":"Segmento nao encontrado"}),400
        

        sas_parent_folder_uri_seg = segmento[5]
        print('Path segmento:')
        print(sas_parent_folder_uri_seg)


        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.sas.content.folder+json, application/json"
        }

        cluster_id = str(uuid.uuid4())
        payload = {
            "name": nome,
            "description": descricao,
            "type": "folder"
        }
        try:

            url = f"{url_path_sid}/folders/folders"

            path_segmentos = {"parentFolderUri": sas_parent_folder_uri_seg}  # Define o path_segmentos se a pasta raiz foi encontrada
            
            response = requests.post(url, json=payload, headers=headers, params=path_segmentos, verify=False)

            if response.status_code != 201:
                cur.execute("SELECT * FROM clusters WHERE nome = %s",(nome,))
                existing_cluster = cur.fetchone()
                if existing_cluster:
                    return jsonify({"error": "O Cluster ja existe","campos_error":["nome"]}), 400
                error_type = response.json()
                raise Exception("Falha ao criar o Cluster no SAS Intelligence Design ", error_type["message"])
        
            response.raise_for_status()

            response_data = response.json()
            
            # Obtém os dados relevantes da resposta
            sas_folder_id = response_data.get("id")
            sas_parent_folder_uri = response_data.get("links", [{}])[0].get("uri")

            # Verifica se os dados necessários foram obtidos
            if not sas_folder_id or not sas_parent_folder_uri:
                return jsonify({"error": "'parentFolderUri' or 'id' not found in response data"}), 500
            
            # Insere os dados do cluster no banco de dados
            cur.execute("""
                INSERT INTO clusters (id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri, segmento_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (cluster_id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri, segmento_id))
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
    is_ativo = data.get('is_ativo', True)

    # Verificar se 'is_ativo' está presente no JSON e é um valor booleano
    if "is_ativo" not in data or not isinstance(data["is_ativo"], bool):
        return jsonify({"error": "'is_ativo' é obrigatório e deve ser um booleano","campos_error":["is_ativo"]}), 400

    if not cluster_id:
        return jsonify({"error": "cluster_id é obrigatório","campos_error":["cluster_id"]}), 400
    
    if not descricao:
         return jsonify({"error": "'descricao' é obrigatório ","campos_error":["descricao"]}), 400

    if len(descricao) > 350:
        return jsonify({"error": "Descrição deve ter no máximo 350 caracteres","campos_error":["descricao"]}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    updated_at = datetime.now()

    try:
        # verifica se exite o id na table
        cur.execute("SELECT 1 FROM  clusters WHERE id = %s",(cluster_id,))
        cluster_existe = cur.fetchone()

        if not cluster_existe:
            return jsonify({"error":"Cluster nao encontrado"}),404

        cur.execute(
            """
            UPDATE clusters
            SET descricao = %s, is_ativo = %s, updated_at = %s
            WHERE id = %s
            """,
            (descricao, is_ativo, updated_at, cluster_id)
        )
        conn.commit()

        return jsonify({"message": "Cluster Atualizado com Sucesso","id":cluster_id}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()



