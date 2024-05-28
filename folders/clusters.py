from flask import Flask, request, jsonify
import psycopg2
import uuid
from datetime import datetime
from db import get_db_connection
import requests

app = Flask(__name__)


# Endpoint para criar um novo cluster
def create_cluster():
    data = request.get_json()

    nome = data.get('nome')
    descricao = data.get('descricao', '')
    is_ativo = data.get('is_ativo', True)
    segmento_id = data.get('segmento_id')  # Id do segmento ao qual o cluster pertence

    if not nome:
        return jsonify({"error": "Nome do cluster é obrigatório"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cluster_id = str(uuid.uuid4())  # Gerar um UUID para o cluster

    try:
        cur.execute(
            """
            INSERT INTO clusters (id, nome, descricao, is_ativo, segmento_id)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (cluster_id, nome, descricao, is_ativo, segmento_id)
        )
        conn.commit()

        return jsonify({"message": "Cluster criado com sucesso", "id": cluster_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()
        
        
# Endpoint para obter todos os clusters
def get_clusters():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("SELECT * FROM clusters")
        clusters = cur.fetchall()
        return jsonify(clusters), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Endpoint para obter um cluster pelo ID
def get_cluster(cluster_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("SELECT * FROM clusters WHERE id = %s", (cluster_id,))
        cluster = cur.fetchone()
        if cluster:
            return jsonify(cluster), 200
        else:
            return jsonify({"error": "Cluster não encontrado"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Endpoint para atualizar um cluster
def update_cluster(cluster_id):
    data = request.get_json()

    nome = data.get('nome')
    descricao = data.get('descricao', '')
    is_ativo = data.get('is_ativo', True)

    if not nome:
        return jsonify({"error": "Nome do cluster é obrigatório"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            UPDATE clusters
            SET nome = %s, descricao = %s, is_ativo = %s
            WHERE id = %s
            """,
            (nome, descricao, is_ativo, cluster_id)
        )
        conn.commit()

        return jsonify({"message": "Cluster atualizado com sucesso"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

# Endpoint para deletar um cluster
def delete_cluster(cluster_id):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("DELETE FROM clusters WHERE id = %s", (cluster_id,))
        conn.commit()

        return jsonify({"message": "Cluster deletado com sucesso"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()