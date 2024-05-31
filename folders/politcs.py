from flask import Flask, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from db import get_db_connection
import requests

app = Flask(__name__)



def criar_politica(token):
    try:
        # Obtém os dados da requisição JSON
        data = request.get_json()

        # Extrai os dados do JSON
        cluster_id = data.get('cluster_id')
        nome = data.get('nome')
        descricao = data.get('descricao', '')
        is_ativo = data.get('is_ativo', True)

        print(nome)
        print(cluster_id)
        print(descricao)
        print(is_ativo)

        # Verifica a validade dos dados
        if not nome or len(descricao) > 140:
            return jsonify({"error": "Invalid input"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT * FROM politica WHERE nome = %s AND cluster_id = %s",(nome,cluster_id))
        existing_cluster = cur.fetchone()

        if existing_cluster:
            return jsonify({"error":"Nome do Politica ja exite para este Cluster"}),400
        
        cur.execute("SELECT * FROM clusters WHERE id = %s",(cluster_id,))
        cluster = cur.fetchone()
        if not cluster:
            return jsonify({"error":"Cluster nao encontrado"}),400
        

        sas_parent_folder_uri_cluster = cluster[5]
        

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

        url = "https://server.demo.sas.com/folders/folders"

        path_cluster = {"parentFolderUri": sas_parent_folder_uri_cluster}  # Define o path_cluster se a pasta raiz foi encontrada
        
        # Realiza a solicitação POST
        response = requests.post(url, json=payload, headers=headers, params=path_cluster, verify=False)
        
        # Verifica se a solicitação foi bem-sucedida
        response.raise_for_status()

        # Processa a resposta JSON
        response_data = response.json()
        
        # Obtém os dados relevantes da resposta
        sas_folder_id = response_data.get("id")
        sas_parent_folder_uri = response_data.get("links", [{}])[0].get("uri")

        # Verifica se os dados necessários foram obtidos
        if not sas_folder_id or not sas_parent_folder_uri:
            return jsonify({"error": "'parentFolderUri' or 'id' not found in response data"}), 500
        
        # Insere os dados do cluster no banco de dados
        cur.execute("""
            INSERT INTO politica (id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri, cluster_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (politica_id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri, cluster_id))
        politica_id = cur.fetchone()[0]

        conn.commit()
        return jsonify({"message": "Politca created successfully", "id": politica_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn is not None:
            conn.close()



def edit_politica():
    
    data = request.get_json()
    politca_id = data.get('id')
    descricao = data.get('descricao', '')
    is_ativo = data.get('is_ativo', True)

     # Verificar se 'is_ativo' está presente no JSON e é um valor booleano
    if "is_ativo" not in data or not isinstance(data["is_ativo"], bool):
        return jsonify({"error": "'is_ativo' é obrigatório e deve ser um booleano"}), 400

    if not politca_id:
        return jsonify({"error": "politca_id is required"}), 400
    
    if not descricao:
        return jsonify({"error": "descricao is required"}), 400

    if len(descricao) > 140:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    updated_at = datetime.now()

    try:
        # verifica se exite o id na table
        cur.execute("SELECT 1 FROM  politica WHERE id = %s",(politca_id,))
        politica_existe = cur.fetchone()

        if not politica_existe:
            return jsonify({"error":"Politica nao encontrado"}),404

        cur.execute(
            """
            UPDATE politica
            SET descricao = %s, is_ativo = %s, updated_at = %s
            WHERE id = %s
            """,
            (descricao, is_ativo, updated_at, politca_id)
        )
        conn.commit()

        return jsonify({"message": "Politica updated successfully"}), 200
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

        cur.execute("SELECT id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri, created_at, updated_at, cluster_id FROM politica")
        clusters = cur.fetchall()

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
                "cluster_id": cluster[8]
            })

        return jsonify(result)
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro ao buscar as politcas: {error}")
        return jsonify({"error": "Failed to retrieve politcas"}), 500
    finally:
        if conn is not None:
            conn.close()