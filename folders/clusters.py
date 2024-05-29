from flask import Flask, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from db import get_db_connection
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import os
import requests

from folders.segments import list_segmentos




app = Flask(__name__)




# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()


def busca_all_cluster():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri, created_at, updated_at, segmento_id FROM clusters")
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
                "segmento_id": cluster[8]
            })

        return jsonify(result)
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro ao buscar os clusters: {error}")
        return jsonify({"error": "Failed to retrieve clusters"}), 500
    finally:
        if conn is not None:
            conn.close()


def buscar_cluster_id():
    data = request.get_json()
    id = data.get('id')
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM clusters WHERE id = %s", (id,))
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
                "segmento_id": cluster[8]
            }
            return jsonify(result)
    
        else:
            return None  # ou uma mensagem indicando que o cluster não foi encontrado
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Erro ao buscar o cluster: {error}")
    finally:
        if conn is not None:
            conn.close()





def criar_cluster(token):
    try:
        # Obtém todos os segmentos
        all_segmentos = list_segmentos()
        
        # Obtém os dados da requisição JSON
        data = request.get_json()

        # Extrai os dados do JSON
        nome_segmento = data.get('nome_segmento')
        nome = data.get('nome')
        descricao = data.get('descricao', '')
        is_ativo = data.get('is_ativo', True)

        print(nome)
        print(nome_segmento)
        print(descricao)
        print(is_ativo)

        # Verifica a validade dos dados
        if not nome or len(descricao) > 140:
            return jsonify({"error": "Invalid input"}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        sas_parent_folder_uri_seg = None
        segmento_id = None

        # Itera sobre todos os segmentos para encontrar o segmento correto
        for segmento in all_segmentos:
            print(segmento)
            if segmento['nome'] == nome_segmento:
                sas_parent_folder_uri_seg = segmento['sas_parent_folder_uri']
                segmento_id = segmento['id']
                break
        else:
            # Se o segmento não for encontrado, retorna um erro
            return jsonify({"error": "Segmento not found"}), 404
            
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

        url = "https://server.demo.sas.com/folders/folders"

        path_segmentos = {"parentFolderUri": sas_parent_folder_uri_seg}  # Define o path_segmentos se a pasta raiz foi encontrada
        
        # Realiza a solicitação POST
        response = requests.post(url, json=payload, headers=headers, params=path_segmentos, verify=False)
        
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
            INSERT INTO clusters (id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri, segmento_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (cluster_id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri, segmento_id))
        cluster_id = cur.fetchone()[0]

        conn.commit()
        return jsonify({"message": "Cluster created successfully", "id": cluster_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn is not None:
            conn.close()



