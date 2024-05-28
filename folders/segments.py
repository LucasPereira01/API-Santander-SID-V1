from flask import Flask, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from db import get_db_connection
import requests

app = Flask(__name__)

# Endpoint para criar segmento
def create_segmento(token=None):
    data = request.get_json()

    nome = data.get('nome')
    descricao = data.get('descricao', '')
    is_ativo = data.get('is_ativo', True)

    if not nome or len(descricao) > 140:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    headers = {
    "Content-Type": "application/vnd.sas.content.folder+json",
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.sas.content.folder+json, application/json"
}
    segmento_id = str(uuid.uuid4())

    try:
        """ # Simulando a chamada para a API do SAS Intelligence Design
        response = requests.post('http://mock-folders.apifirst.unx.sas.com/folders/folders', headers=headers, json={
            #"id": segmento_id,
            "name": nome,
            "description": descricao,
            "type":"folder"
            #"is_ativo": is_ativo
        })

        if response.status_code != 201:
            raise Exception("Failed to create segmento in SAS Intelligence Design")
         """
        # Simulação de resposta da API para fins de teste
        teste = {
            "id": "7e92c5d9-47a0-48b8-bb09-84c164d1f3fe",
            "parentFolderUri": "/folders/folders/c0e8ccf9-ac43-4303-a1ce-40d7ffbd7450"
        }
        
        response_data = teste
        sas_folder_id = response_data["id"]
        sas_parent_folder_uri = response_data["parentFolderUri"]
        
        cur.execute(
            """
            INSERT INTO segmento (id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (segmento_id, nome, descricao, is_ativo, sas_folder_id, sas_parent_folder_uri)
        )
        conn.commit()
            
        return jsonify({"message": "Segmento created successfully", "id": segmento_id}), 201
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

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
