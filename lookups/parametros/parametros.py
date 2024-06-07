from flask import Flask, make_response, jsonify, request
from db import get_db_connection

def create_parametro(id_politica):
    body = request.json
    name = body.get("name")
    descricao = body.get("description")
    modo = body.get("modo")
    data_hora_vigencia = body.get("data_hora_vigencia")
    versao = body.get("versao")
    status_code = body.get("status_code")
    is_vigente = body.get("is_vigente")
    sas_user_id = body.get("sas_user_id")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT * FROM politica WHERE id = %s", (id_politica,))
        politica = cur.fetchone()
        if not politica:
            return jsonify({"error": "Política não encontrada"}), 400

        cur.execute(
            """
            INSERT INTO parametro (nome, descricao, modo, data_hora_vigencia, versao, is_vigente, status_code, politica_id, sas_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name, descricao, modo, data_hora_vigencia, versao, is_vigente, status_code, id_politica, sas_user_id)
        )
        conn.commit()
        return jsonify({"message": "Parâmetro criado com sucesso"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()
