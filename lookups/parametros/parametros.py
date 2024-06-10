from flask import Flask, make_response, jsonify, request
from db import get_db_connection
import uuid
import json
import re

def create_parametro():
    body = request.json
    nome = body.get("nome")
    id_politica = body.get("id_politica")
    descricao = body.get("description")
    modo = body.get("modo")
    data_hora_vigencia = body.get("data_hora_vigencia")
    versao = body.get("versao")
    is_vigente = body.get("is_vigente")
    sas_user_id = body.get("sas_user_id")
    justificativa = body.get("justificativa")
    parametro_id = str(uuid.uuid4())
    status_code = "001"

    # Validando os campos
    if not isinstance(is_vigente, bool):
        return jsonify({"error": "'is_vigente' deve ser um booleano", "campos_error": ["is_vigente"]}), 400
    if not nome:
        return jsonify({"error": "'nome' é obrigatório", "campos_error": ["nome"]}), 400
    if not id_politica:
        return jsonify({"error": "'id_politica' é obrigatório", "campos_error": ["id_politica"]}), 400
    if not sas_user_id:
        return jsonify({"error": "'sas_user_id' é obrigatório", "campos_error": ["sas_user_id"]}), 400
    if not versao:
        return jsonify({"error": "'versao' é obrigatório", "campos_error": ["versao"]}), 400
    if not data_hora_vigencia:
        return jsonify({"error": "'data_hora_vigencia' é obrigatório", "campos_error": ["data_hora_vigencia"]}), 400
    if not descricao:
        return jsonify({"error": "'descricao' é obrigatório", "campos_error": ["descricao"]}), 400
    if len(descricao) > 350:
        return jsonify({"error": "Descrição deve ter no máximo 350 caracteres", "campos_error": ["descricao"]}), 400
    name_regex = re.compile(r"^[A-Za-z0-9_]+$")
    if not name_regex.match(nome):
        return jsonify({"error": "Nome deve conter apenas letras, números ou underscores", "campos_error": ["nome"]}), 400
    
                # Validando o campo 'tipo'
    if modo not in ["CHAVE", "GLOBAL"]:
        return jsonify({"error": "'modo' é obrigatório e deve ser um desses valores (CHAVE, GLOBAL)", "campos_error": ["modo"]}), 400


    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM parametro WHERE nome = %s AND politica_id = %s",(nome, id_politica))
        existing_cluster = cur.fetchone()

        if existing_cluster:
            return jsonify({"error":"Nome do Parametro ja existe para esta Politca","campos_error":["nome"]}),400
        # Verificar se a política existe

        cur.execute("SELECT * FROM politica WHERE id = %s", (id_politica,))
        politica = cur.fetchone()
        if not politica:
            return jsonify({"error": "Política não encontrada"}), 400

        # Inserir o parâmetro
        cur.execute(
            """
            INSERT INTO parametro (id, nome, descricao, modo, data_hora_vigencia, versao, is_vigente, status_code, politica_id, sas_user_id)
            VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (parametro_id, nome, descricao, modo, data_hora_vigencia, versao, is_vigente, status_code, id_politica, sas_user_id)
        )
        conn.commit()

        # Inserir o evento associado ao parâmetro
        cur.execute(
            """
            INSERT INTO evento (justificativa, status_code, sas_user_id, parametro_id,created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (justificativa, status_code, sas_user_id, parametro_id)
        )
        conn.commit()

        return jsonify({"message": "Parâmetro criado com sucesso", "id": parametro_id}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

def get_all_parametro():
    ...


def create_variaveis(parametro_id):
    body = request.json

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        for value in body:
            variavel_lista = value.get("variavel_lista")
            nome = value.get("nome")
            descricao = value.get("descricao")
            tipo = value.get("tipo")
            is_chave = value.get("is_chave")
            tamanho = value.get("tamanho")
            qtd_casas_decimais = value.get("qtd_casas_decimais")

            # Validando os campos
            if not isinstance(is_chave, bool):
                return jsonify({"error": "'is_chave' deve ser um booleano", "campos_error": ["is_chave"]}), 400
            if not nome:
                return jsonify({"error": "'nome' é obrigatório", "campos_error": ["nome"]}), 400
            if not descricao:
                return jsonify({"error": "'descricao' é obrigatório", "campos_error": ["descricao"]}), 400
            if not tamanho:
                return jsonify({"error": "'tamanho' é obrigatório", "campos_error": ["tamanho"]}), 400
            if len(descricao) > 350:
                return jsonify({"error": "Descrição deve ter no máximo 350 caracteres", "campos_error": ["descricao"]}), 400
            name_regex = re.compile(r"^[A-Za-z0-9_]+$")
            if not name_regex.match(nome):
                return jsonify({"error": "Nome deve conter apenas letras, números ou underscores", "campos_error": ["nome"]}), 400

            # Validando o campo 'tipo'
            if tipo not in ["LISTA", "DECIMAL", "TEXTO", "NUMERICO"]:
                return jsonify({"error": "'tipo' é obrigatório e deve ser um desses valores (LISTA, DECIMAL, TEXTO, NUMERICO)", "campos_error": ["tipo"]}), 400

            var_id  = str(uuid.uuid4())
            # Inserindo na tabela 'variavel'
            cur.execute(
                """
                INSERT INTO variavel (id,nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id)
                VALUES (%s,%s, %s, %s, %s, %s, %s, %s)
                """,
                (var_id, nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id)
            )
            conn.commit()

            # Verificar se o campo 'tipo' é uma lista e se 'variavel_lista' possui elementos
            if tipo == "LISTA" and variavel_lista and len(variavel_lista) > 0:
                for variavel in variavel_lista:
                    var_name = variavel['nome']
                    is_visivel = variavel['is_visivel']

                    cur.execute(
                        """
                        INSERT INTO variavel_lista (nome, is_visivel, variavel_id)
                        VALUES (%s, %s, %s)
                        """,
                        (var_name, is_visivel, var_id)
                    )
                    conn.commit()

        return jsonify({"message": "Variaveis criadas com sucesso"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


def create_dados(parametro_id):
    body = request.json

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        for value in body:
            informacao = value.get("informacao")
            sas_key = value.get("sas_key")
            sas_value = value.get("sas_value")
            


            # Verificar se a informacao é um JSON válido
            try:
                informacao_json = json.loads(informacao)
            except json.JSONDecodeError:
                return jsonify({"error": "'informacao' deve ser um JSON válido", "campos_error": ["informacao"]}), 400

            # Validando os campos
            if not informacao:
                return jsonify({"error": "'informacao' é obrigatório", "campos_error": ["informacao"]}), 400
            if not sas_key:
                return jsonify({"error": "'descricao' é obrigatório", "campos_error": ["descricao"]}), 400
            if not sas_value:
                return jsonify({"error": "'tamanho' é obrigatório", "campos_error": ["tamanho"]}), 400
            
            # Inserindo na tabela 'variavel'
            cur.execute(
                """
                INSERT INTO dado (informacao, sas_key, sas_value, parametro_id,created_at)
                VALUES (%s,%s, %s, %s, NOW())
                """,
                (informacao, sas_key, sas_value, parametro_id)
            )
            conn.commit()
        return jsonify({"message": "Variaveis criadas com sucesso"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()