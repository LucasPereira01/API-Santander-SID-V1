from flask import Flask, make_response, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from db import get_db_connection
import requests
import re

app = Flask(__name__)

def verify_folder_root_or_create(token):
    print('Dentro do verify_folder_root')
    url = "https://server.demo.sas.com/folders/rootFolders"
    folder_name = "Lucas"  # Mantendo o nome correto da pasta conforme fornecido

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.sas.collection+json, application/vnd.sas.summary+json, application/json"
    }

    print('Antes do request')
    try:
        response = requests.get(url, headers=headers, verify=False)
        print('Depois do request')
        if response.status_code == 200:
            print('Status code 200')
            folders = response.json()["items"]
            for folder in folders:
                if folder["name"] == folder_name:
                    name = folder["name"]
                    uri = folder['links'][0]['uri']
                    print("URI:", uri)
                    return {"name": name, "uri": uri}
            # Se a pasta não foi encontrada, criar ela
            print("Pasta não encontrada, criando...")

            # Lógica para criar a pasta
            create_folder_url = "https://server.demo.sas.com/folders/folders"
            create_folder_payload = {
                "name": folder_name,
                "type": "folder"
            }
            create_folder_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            create_folder_response = requests.post(create_folder_url, json=create_folder_payload, headers=create_folder_headers, verify=False)
            if create_folder_response.status_code == 201:
                folder_data = create_folder_response.json()
                uri = folder_data['links'][0]['uri']
                print("Pasta criada com sucesso. URI:", uri)
                return {"name": folder_name, "uri": uri}
            else:
                print("Falha ao criar a pasta.")
                print("Status code:", create_folder_response.status_code)
                print("Texto da resposta:", create_folder_response.text)
                # Se houver um problema com a solicitação, retornar um erro
                raise Exception("Failed to create folder.")
        else:
            print("Falha ao recuperar as pastas.")
            print("Status code:", response.status_code)
            print("Texto da resposta:", response.text)
            # Se houver um problema com a solicitação, retornar um erro
            raise Exception("Failed to retrieve folders.")
    except Exception as e:
        print("Erro durante a solicitação:", e)
        # Se houver uma exceção, retornar um erro
        raise Exception("Failed to retrieve folders.")


def create_segmento(token,global_uri):
    data = request.get_json()

    # Verificar se 'is_ativo' está presente no JSON e é um valor booleano
    if "is_ativo" not in data or not isinstance(data["is_ativo"], bool):
        return jsonify({"error": "'is_ativo' é obrigatório e deve ser um booleano"}), 400

    nome = data.get('nome')
    descricao = data.get('descricao', '')

    # Verificar se 'nome' e 'descricao' estão presentes e são válidos
    if not nome or not descricao or len(descricao) > 140:
        return jsonify({"error": "Nome e descrição são obrigatórios e a descrição deve ter no máximo 140 caracteres"}), 400

    # Validação do campo 'nome' usando expressão regular
    name_regex = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_regex.match(nome):
        return jsonify({"error": "Nome deve conter apenas letras, números ou underscores"}), 400

    # Pegar o valor de 'is_ativo' do JSON
    is_ativo = data.get('is_ativo', True)

    
    conn = get_db_connection()
    cur = conn.cursor()

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
        url = "https://server.demo.sas.com/folders/folders"

        if global_uri is not None:
            path_segmentos = {"parentFolderUri": global_uri["uri"]}  # Define o path_segmentos se a pasta raiz foi encontrada
            response = requests.post(url, json=payload, headers=headers, params=path_segmentos, verify=False)
        else:
            response = requests.post(url, json=payload, headers=headers, verify=False)

        if response.status_code != 201:
            raise Exception("Failed to create segmento in SAS Intelligence Design")
        
        response_data = response.json()

        sas_folder_id = response_data.get("id")
        if 'links' in response_data and len(response_data['links']) > 0:
            sas_parent_folder_uri = response_data['links'][0]['uri']
        else:
            sas_parent_folder_uri = None
        
        if not sas_folder_id or not sas_parent_folder_uri:
            raise Exception("'parentFolderUri' or 'id' not found in response data")
        
        cur.execute(
            """
            INSERT INTO segmento (id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (segmento_id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri)
        )
        conn.commit()
            
        return jsonify({"message": "Segmento created successfully", "id": segmento_id, "response": response_data}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()



def edit_segmento(segmento_id=None):
    # Verificar se segmento_id foi passado como argumento da função ou na requisição
    if not segmento_id:
        data = request.get_json()
        segmento_id = data.get('id') if data else None

    if not segmento_id:
        return jsonify({"error": "Segmento ID is required"}), 400
    
    data = request.get_json()
    descricao = data.get('descricao', '')
    is_ativo = data.get('is_ativo', True)

    if len(descricao) > 140:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    updated_at = datetime.now()

    try:
        cur.execute(
            """
            UPDATE segmento
            SET descricao = %s, is_ativo = %s, updated_at = %s
            WHERE id = %s
            """,
            (descricao, is_ativo, updated_at, segmento_id)
        )
        conn.commit()

        return jsonify({"message": "Segmento updated successfully"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Endpoint para listar segmentos
def list_segmentos():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri FROM segmento")
        segmentos = cur.fetchall()
        result = [
            {
                "id": row[0],
                "nome": row[1],
                "descricao": row[2],
                "is_ativo": row[3],
                "sas_folder_id": row[4],
                "sas_parent_folder_uri": row[5]
            }
            for row in segmentos
        ]

        return result  # Retornar diretamente a lista de segmentos
    except Exception as e:
        print(f"Erro ao listar segmentos: {e}")
        return []  # Retornar uma lista vazia em caso de erro
    finally:
        cur.close()
        conn.close()