from flask import Flask, make_response, jsonify, request
from db import get_db_connection
import uuid
import json
import re
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

schema_db = os.getenv("SCHEMA_DB")

# Parametros 
def create_parametro():
    sas_user_id = None
    sas_user_name = None
    sas_user_email = None

    if 'Sas-User-Id' in request.headers:
        sas_user_id = request.headers.get('Sas-User-Id')
    if 'Sas-User-Name' in request.headers:
        sas_user_name = request.headers.get('Sas-User-Name')
    if 'Sas-User-Email' in request.headers:
        sas_user_email = request.headers.get('Sas-User-Email')

    body = request.json
    nome = body.get("nome")
    politica_id = body.get("politica_id")
    descricao = body.get("descricao")
    modo = body.get("modo")
    data_hora_vigencia = body.get("data_hora_vigencia")
    versao = body.get("versao")

    parametro_id = str(uuid.uuid4())
    is_vigente = True
    status_code = "001"

    # Validando os campos
    if not nome:
        return jsonify({"error": "'nome' é obrigatório", "campos_error": ["nome"]}), 400
    if not politica_id:
        return jsonify({"error": "'politica_id' é obrigatório", "campos_error": ["politica_id"]}), 400
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
        cur.execute(f"SELECT * FROM  {schema_db}.parametro WHERE nome = %s AND politica_id = %s",(nome, politica_id))
        existing_cluster = cur.fetchone()

        if existing_cluster:
            return jsonify({"error":"Nome do Parametro ja existe para esta Politica","campos_error":["nome"]}),400

        # Verificar se a política existe
        cur.execute(f"SELECT * FROM  {schema_db}.politica WHERE id = %s", (politica_id,))
        politica = cur.fetchone()
        if not politica:
            return jsonify({"error": "Política não encontrada"}), 400

        # Inserir o parâmetro
        cur.execute(
            f"""
            INSERT INTO {schema_db}.parametro (id, nome, descricao, modo, data_hora_vigencia, versao, is_vigente, status_code, politica_id, sas_user_id, sas_user_name, sas_user_email)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (parametro_id, nome, descricao, modo, data_hora_vigencia, versao, is_vigente, status_code, politica_id, sas_user_id, sas_user_name, sas_user_email)
        )
        conn.commit()

        # Inserir o evento associado ao parâmetro
        cur.execute(
            f"""
            INSERT INTO {schema_db}.evento (status_code, parametro_id, sas_user_id, sas_user_name, sas_user_email, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """,
            (status_code, parametro_id, sas_user_id, sas_user_name, sas_user_email)
        )
        conn.commit()

        return jsonify({"message": "Parâmetro criado com sucesso", "id": parametro_id}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

def lista_parametros_data_table():
    # Obtenha o corpo da solicitação
    body = request.get_json()

    # Extraia os parâmetros do corpo da solicitação
    offset = body.get('offset', 0)
    limit = body.get('limit', 25)
    order = body.get('order', None)
    filters = body.get('filters', [])

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Construa a consulta SQL baseada nos parâmetros fornecidos para contar os registros
        query_count = f"""
            SELECT 
                COUNT(*)
            FROM  {schema_db}.parametro p
                JOIN {schema_db}.parametro_status st ON p.status_code = st.code
                JOIN {schema_db}.politica po ON p.politica_id = po.id
                JOIN {schema_db}.clusters c ON po.cluster_id = c.id
                JOIN {schema_db}.segmento s ON c.segmento_id = s.id
            WHERE
                p.deleted_at IS NULL AND p.is_vigente IS true
            """
        # Construa a consulta SQL baseada nos parâmetros fornecidos
        query = f"""
            SELECT 
                p.id, p.nome, p.descricao, p.modo, p.versao,
                st.code as status_code, st.type as status_type, st.description as status_description,
                po.id as politica_id, po.nome as politica_nome,
                c.id as cluster_id, c.nome as cluster_nome,
                s.id as segmento_id, s.nome as segmento_nome
                FROM  {schema_db}.parametro p
                JOIN {schema_db}.parametro_status st ON p.status_code = st.code
                JOIN {schema_db}.politica po ON p.politica_id = po.id
                JOIN {schema_db}.clusters c ON po.cluster_id = c.id
                JOIN {schema_db}.segmento s ON c.segmento_id = s.id
            WHERE
                p.deleted_at IS NULL AND p.is_vigente IS true
            """

        # Aplicar filtros
        if filters:
            for filter in filters:
                if filter['column'] == "nome":
                    query_count += f" AND p.nome ILIKE '%{filter['value']}%'"
                    query += f" AND p.nome ILIKE '%{filter['value']}%'"

                if filter['column'] == "segmento":
                    query_count += f" AND s.id = '{filter['value']}'"
                    query += f" AND s.id = '{filter['value']}'"
                
                if filter['column'] == "cluster":
                    query_count += f" AND c.id = '{filter['value']}'"
                    query += f" AND c.id = '{filter['value']}'"

                if filter['column'] == "politica":
                    query_count += f" AND po.id = '{filter['value']}'"
                    query += f" AND po.id = '{filter['value']}'"

                if filter['column'] == "variavel":
                    query_count += f" AND p.modo = '{filter['value']}'"
                    query += f" AND p.modo = '{filter['value']}'"

                if filter['column'] == "status":
                    status_list = filter['value'].split(",")

                    query_count += " AND st.code IN ("
                    query += " AND st.code IN ("

                    for sl in status_list:
                        query_count += "'" + sl + "',"
                        query += "'" + sl + "',"

                    query_count = query_count[:-1] + ")"
                    query = query[:-1] + ")"

        # Aplicar a ordenação
        if order:
            if order['column'] == "nome":
                query += f" ORDER BY p.nome {order['direction']}"

            if order['column'] == "segmento":
                query += f" ORDER BY s.nome {order['direction']}"

            if order['column'] == "cluster":
                query += f" ORDER BY c.nome {order['direction']}"
            
            if order['column'] == "politica":
                query += f" ORDER BY po.nome {order['direction']}"

            if order['column'] == "variavel":
                query += f" ORDER BY p.modo {order['direction']}"

            if order['column'] == "versao":
                query += f" ORDER BY p.versao {order['direction']}"

            if order['column'] == "status":
                query += f" ORDER BY st.description {order['direction']}"
        else:
            query += f" ORDER BY p.created_at DESC"

        # Aplicar limite e deslocamento
        query += f" LIMIT {limit} OFFSET {offset}"

        # Executar o consulta SQL para contar os registros
        cur.execute(query_count)
        total_registros = cur.fetchone()[0]

        # Executar a consulta SQL
        cur.execute(query)
        parametros = cur.fetchall()

        parametros_json = [
            {
                "id": row[0],
                "nome": row[1],
                "descricao": row[2],
                "modo": row[3],
                "versao": row[4],
                "status_code": row[5],
                "status": {
                    "code": row[5],
                    "type": row[6],
                    "description": row[7]
                },
                "politica_id": row[8],
                "politica": {
                    "id": row[8],
                    "nome": row[9],
                    "cluster_id": row[10],
                    "cluster": {
                        "id": row[10],
                        "nome": row[11],
                        "segmento_id": row[12],
                        "segmento": {
                            "id": row[12],
                            "nome": row[13]
                        }
                    }
                }
            }

            for row in parametros
        ]

        # Montar a resposta
        response = {
            "offset": offset,
            "limit": limit,
            "order": order,
            "count": total_registros,
            "filters": filters,
            "items": parametros_json
        }

        return response

    except Exception as e:
        print(f"Erro ao listar parâmetros: {e}")
        return None

    finally:
        cur.close()
        conn.close()


def get_all_parametro():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            f"""
            SELECT 
                p.id AS parametro_id, p.nome AS parametro_nome, p.descricao AS parametro_descricao, 
                p.modo AS parametro_modo, p.data_hora_vigencia, p.versao, p.is_vigente, 
                p.sas_domain_id, p.sas_content_id, p.created_at AS parametro_created_at, 
                p.updated_at AS parametro_updated_at, p.deleted_at, p.status_code, 
                p.parametro_parent_id, p.politica_id, p.sas_user_id,
                po.id AS politica_id, po.nome AS politica_nome, po.descricao AS politica_descricao,
                po.is_ativo AS politica_is_ativo, po.sas_folder_id AS politica_sas_folder_id,
                po.sas_parent_uri AS politica_sas_parent_uri, po.created_at AS politica_created_at,
                po.updated_at AS politica_updated_at, po.sas_test_folder_id AS politica_sas_test_folder_id,
                po.sas_test_parent_uri AS politica_sas_test_parent_uri,
                c.id AS cluster_id, c.nome AS cluster_nome, c.descricao AS cluster_descricao,
                c.is_ativo AS cluster_is_ativo, c.sas_folder_id AS cluster_sas_folder_id,
                c.sas_parent_uri AS cluster_sas_parent_uri, c.created_at AS cluster_created_at,
                c.updated_at AS cluster_updated_at, c.sas_test_folder_id AS cluster_sas_test_folder_id,
                c.sas_test_parent_uri AS cluster_sas_test_parent_uri,
                s.id AS segmento_id, s.nome AS segmento_nome, s.descricao AS segmento_descricao,
                s.is_ativo AS segmento_is_ativo, s.sas_folder_id AS segmento_sas_folder_id,
                s.sas_parent_uri AS segmento_sas_parent_uri, s.created_at AS segmento_created_at,
                s.updated_at AS segmento_updated_at, s.sas_test_folder_id AS segmento_sas_test_folder_id,
                s.sas_test_parent_uri AS segmento_sas_test_parent_uri,
                d.informacao AS dado_informacao, d.sas_key AS dado_sas_key, d.sas_value AS dado_sas_value
            FROM  {schema_db}.parametro p
            JOIN  {schema_db}.politica po ON p.politica_id = po.id
            JOIN  {schema_db}.clusters c ON po.cluster_id = c.id
            JOIN  {schema_db}.segmento s ON c.segmento_id = s.id
            LEFT JOIN {schema_db}.dado d ON p.id = d.parametro_id
            """
        )

        parametros = cur.fetchall()

        parametros_json = [
            {
                "id": row["parametro_id"],
                "nome": row["parametro_nome"],
                "descricao": row["parametro_descricao"],
                "modo": row["parametro_modo"],
                "data_hora_vigencia": row["data_hora_vigencia"].isoformat(),
                "versao": row["versao"],
                "is_vigente": row["is_vigente"],
                "sas_domain_id": row["sas_domain_id"],
                "sas_content_id": row["sas_content_id"],
                "created_at": row["parametro_created_at"].isoformat(),
                "updated_at": row["parametro_updated_at"],
                "deleted_at": row["deleted_at"],
                "status_code": row["status_code"],
                "parametro_parent_id": row["parametro_parent_id"],
                "politica_id": row["politica_id"],
                "sas_user_id": row["sas_user_id"],
                "politica": {
                    "id": row["politica_id"],
                    "nome": row["politica_nome"],
                    "descricao": row["politica_descricao"],
                    "is_ativo": row["politica_is_ativo"],
                    "sas_folder_id": row["politica_sas_folder_id"],
                    "sas_parent_uri": row["politica_sas_parent_uri"],
                    "created_at": row["politica_created_at"].isoformat(),
                    "updated_at": row["politica_updated_at"],
                    "sas_test_folder_id": row["politica_sas_test_folder_id"],
                    "sas_test_parent_uri": row["politica_sas_test_parent_uri"],
                        "cluster": {
                            "id": row["cluster_id"],
                            "nome": row["cluster_nome"],
                            "descricao": row["cluster_descricao"],
                            "is_ativo": row["cluster_is_ativo"],
                            "sas_folder_id": row["cluster_sas_folder_id"],
                            "sas_parent_uri": row["cluster_sas_parent_uri"],
                            "created_at": row["cluster_created_at"].isoformat(),
                            "updated_at": row["cluster_updated_at"],
                            "sas_test_folder_id": row["cluster_sas_test_folder_id"],
                            "sas_test_parent_uri": row["cluster_sas_test_parent_uri"],
                                "segmento": {
                                    "id": row["segmento_id"],
                                    "nome": row["segmento_nome"],
                                    "descricao": row["segmento_descricao"],
                                    "is_ativo": row["segmento_is_ativo"],
                                    "sas_folder_id": row["segmento_sas_folder_id"],
                                    "sas_parent_uri": row["segmento_sas_parent_uri"],
                                    "created_at": row["segmento_created_at"].isoformat(),
                                    "updated_at": row["segmento_updated_at"],
                                    "sas_test_folder_id": row["segmento_sas_test_folder_id"],
                                    "sas_test_parent_uri": row["segmento_sas_test_parent_uri"]
                                }
                        },
                },
                
                "dado": {
                    "informacao": row["dado_informacao"],
                    "sas_key": row["dado_sas_key"],
                    "sas_value": row["dado_sas_value"]
                }
            }
            for row in parametros
        ]

        return parametros_json

    except Exception as e:
        print(f"Erro ao listar parâmetros: {e}")
        return []

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_parametro_by_id(parametro_id):
    try:
        conn = get_db_connection() 
        cur = conn.cursor()  

        # Consulta SQL para buscar todas as informações necessárias
        cur.execute(
            f"""
            SELECT 
                p.id AS parametro_id, p.nome AS parametro_nome, p.descricao AS parametro_descricao,
                p.modo AS parametro_modo, p.data_hora_vigencia, p.versao, p.is_vigente, 
                p.sas_domain_id, p.sas_content_id, p.created_at AS parametro_created_at,
                p.updated_at AS parametro_updated_at, p.deleted_at, p.status_code,
                p.parametro_parent_id, p.politica_id, p.sas_user_id, p.sas_user_name, p.sas_user_email,
                po.id AS politica_id, po.nome AS politica_nome, po.descricao AS politica_descricao,
                po.is_ativo AS politica_is_ativo, po.sas_folder_id AS politica_sas_folder_id,
                po.sas_parent_uri AS politica_sas_parent_uri, po.sas_test_folder_id AS politica_sas_test_folder_id,
                po.sas_test_parent_uri AS politica_sas_test_parent_uri,
                c.id AS cluster_id, c.nome AS cluster_nome, c.descricao AS cluster_descricao,
                c.is_ativo AS cluster_is_ativo, c.sas_folder_id AS cluster_sas_folder_id,
                c.sas_parent_uri AS cluster_sas_parent_uri, c.sas_test_folder_id AS cluster_sas_test_folder_id,
                c.sas_test_parent_uri AS cluster_sas_test_parent_uri,
                s.id AS segmento_id, s.nome AS segmento_nome, s.descricao AS segmento_descricao,
                s.is_ativo AS segmento_is_ativo, s.sas_folder_id AS segmento_sas_folder_id,
                s.sas_parent_uri AS segmento_sas_parent_uri, s.sas_test_folder_id AS segmento_sas_test_folder_id,
                s.sas_test_parent_uri AS segmento_sas_test_parent_uri,
                v.id AS variavel_id, v.nome AS variavel_nome, v.descricao AS variavel_descricao,
                v.tipo AS variavel_tipo, v.is_chave AS variavel_is_chave, v.tamanho AS variavel_tamanho,
                v.qtd_casas_decimais AS variavel_qtd_casas_decimais,
                vl.id AS variavel_lista_id, vl.nome AS variavel_lista_nome,
                vl.is_visivel AS variavel_lista_is_visivel, vl.variavel_id AS variavel_lista_variavel_id,
                dado.id AS dado_id, dado.informacao AS dado_informacao,
                dado.sas_key AS dado_sas_key, dado.sas_value AS dado_sas_value
            FROM  {schema_db}.parametro p
            JOIN  {schema_db}.politica po ON p.politica_id = po.id
            JOIN  {schema_db}.clusters c ON po.cluster_id = c.id
            JOIN  {schema_db}.segmento s ON c.segmento_id = s.id
            LEFT JOIN {schema_db}.variavel v ON p.id = v.parametro_id
            LEFT JOIN {schema_db}.variavel_lista vl ON v.id = vl.variavel_id
            LEFT JOIN {schema_db}.dado dado ON p.id = dado.parametro_id
            WHERE p.id = %s
            """,
            (parametro_id,)
        )

        rows = cur.fetchall()

        cur.execute(
            f"""
            SELECT id, justificativa, created_at, status_code, file_id, sas_user_id, parametro_id, sas_user_name, sas_user_email
            FROM  {schema_db}.evento
            WHERE parametro_id = %s
            """,
            (parametro_id,)
        )
        rows2 = cur.fetchall()
        
        cur.execute( #id, informacao, sas_key, sas_value, created_at, deleted_at, parametro_id, sas_type
            f"""
            SELECT id, informacao, sas_key, sas_value, created_at, deleted_at, parametro_id, sas_type
            FROM  {schema_db}.dado
            WHERE parametro_id = %s
            """,
            (parametro_id,)
        )
        dados = cur.fetchall()

        if not rows:
            return jsonify({"error": "Parametro não encontrado"}), 404

        # Construindo o JSON de retorno
        parametro_json = {
            "id": rows[0]["parametro_id"],
            "nome": rows[0]["parametro_nome"],
            "descricao": rows[0]["parametro_descricao"],
            "modo": rows[0]["parametro_modo"],
            "data_hora_vigencia": rows[0]["data_hora_vigencia"].isoformat(),
            "versao": rows[0]["versao"],
            "is_vigente": rows[0]["is_vigente"],
            "sas_domain_id": rows[0]["sas_domain_id"],
            "sas_content_id": rows[0]["sas_content_id"],
            "status_code": rows[0]["status_code"],
            "parametro_parent_id": rows[0]["parametro_parent_id"],
            "politica_id": rows[0]["politica_id"],
            "sas_user_id": rows[0]["sas_user_id"],
            "sas_user_name": rows[0]["sas_user_name"],
            "sas_user_email": rows[0]["sas_user_email"],
            "politica": {
                "id": rows[0]["politica_id"],
                "nome": rows[0]["politica_nome"],
                "descricao": rows[0]["politica_descricao"],
                "is_ativo": rows[0]["politica_is_ativo"],
                "sas_folder_id": rows[0]["politica_sas_folder_id"],
                "sas_parent_uri": rows[0]["politica_sas_parent_uri"],
                "sas_test_folder_id": rows[0]["politica_sas_test_folder_id"],
                "sas_test_parent_uri": rows[0]["politica_sas_test_parent_uri"],
                "cluster": {
                    "id": rows[0]["cluster_id"],
                    "nome": rows[0]["cluster_nome"],
                    "descricao": rows[0]["cluster_descricao"],
                    "is_ativo": rows[0]["cluster_is_ativo"],
                    "sas_folder_id": rows[0]["cluster_sas_folder_id"],
                    "sas_parent_uri": rows[0]["cluster_sas_parent_uri"],
                    "sas_test_folder_id": rows[0]["cluster_sas_test_folder_id"],
                    "sas_test_parent_uri": rows[0]["cluster_sas_test_parent_uri"],
                    "segmento": {
                        "id": rows[0]["segmento_id"],
                        "nome": rows[0]["segmento_nome"],
                        "descricao": rows[0]["segmento_descricao"],
                        "is_ativo": rows[0]["segmento_is_ativo"],
                        "sas_folder_id": rows[0]["segmento_sas_folder_id"],
                        "sas_parent_uri": rows[0]["segmento_sas_parent_uri"],
                        "sas_test_folder_id": rows[0]["segmento_sas_test_folder_id"],
                        "sas_test_parent_uri": rows[0]["segmento_sas_test_parent_uri"],
                    },
                },
            },
            "variaveis": [],
            "dados": [],
            "eventos": []
        }

        # Montando a lista de variáveis e suas listas associadas
        variaveis = {}
        for row in rows:
            variavel_id = row["variavel_id"]
            if variavel_id:
                if variavel_id not in variaveis:
                    variaveis[variavel_id] = {
                        "id": row["variavel_id"],
                        "nome": row["variavel_nome"],
                        "descricao": row["variavel_descricao"],
                        "tipo": row["variavel_tipo"],
                        "is_chave": row["variavel_is_chave"],
                        "tamanho": row["variavel_tamanho"],
                        "qtd_casas_decimais": row["variavel_qtd_casas_decimais"],
                        "variaveis_lista": []
                    }
            else:
                parametro_json["variaveis"] = []

            if row["variavel_lista_id"]:
                variaveis[variavel_id]["variaveis_lista"].append({
                    "id": row["variavel_lista_id"],
                    "nome": row["variavel_lista_nome"],
                    "is_visivel": row["variavel_lista_is_visivel"],
                    "variavel_id": row["variavel_lista_variavel_id"]
                })
        parametro_json["variaveis"] = list(variaveis.values())

        # Montando a lista de dados associados ao parâmetro
        for row in dados:
            if row["id"]:  # Certifique-se de que o dado existe
                parametro_json["dados"].append({
                    "id": row["id"],
                    "informacao": row["informacao"],
                    "sas_key": row["sas_key"],
                    "sas_value": row["sas_value"]
                })

        # Montando a lista de evento associados ao parâmetro
        for evento in rows2:
            if evento['id']:
                evento_dict = {
                    "id": evento[0],
                    "justificativa": evento[1],
                    "created_at": evento[2].isoformat(),
                    "status_code": evento[3],
                    "file_id": evento[4],
                    "sas_user_id": evento[5],
                    "parametro_id": evento[6],
                    "sas_user_name": evento[7],
                    "sas_user_email": evento[8]
                }
                parametro_json["eventos"].append(evento_dict)
            else:
                parametro_json["eventos"] = []

        return jsonify(parametro_json), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def update_parametro(parametro_id):
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    sas_user_id = request.headers.get('sas_user_id')

    try:    
        # Verificar se o parâmetro existe
        cur.execute(f"SELECT * FROM  {schema_db}.parametro WHERE id = %s", (parametro_id,))
        existing_parametro = cur.fetchone()

        if not existing_parametro:
            return jsonify({"error": "Parametro não encontrado"}), 404

        # Extrair os dados do JSON
        nome = data.get("nome")
        descricao = data.get("descricao")
        modo = data.get("modo")
        data_hora_vigencia = data.get("data_hora_vigencia")
        versao = data.get("versao")
        sas_domain_id = data.get("sas_domain_id")
        sas_content_id = data.get("sas_content_id")
        parametro_parent_id = data.get("parametro_parent_id")
        politica_id = data.get("politica_id")

        # Atualizar o parâmetro no banco de dados
        cur.execute(f"""
            UPDATE {schema_db}.parametro
            SET nome = %s, descricao = %s, modo = %s, data_hora_vigencia = %s, versao = %s,
                sas_domain_id = %s, sas_content_id = %s, updated_at = NOW(), parametro_parent_id = %s, politica_id = %s, sas_user_id = %s
            WHERE id = %s
        """, (nome, descricao, modo, data_hora_vigencia, versao, sas_domain_id, sas_content_id,
             parametro_parent_id, politica_id, sas_user_id, parametro_id))

        conn.commit()

        cur.execute(f"""
                DELETE FROM  {schema_db}.dado
                WHERE parametro_id = %s
                """, (parametro_id,))
        
        cur.execute(f"""
                DELETE FROM  {schema_db}.variavel_lista
                WHERE variavel_id  IN (SELECT id FROM  {schema_db}.variavel WHERE parametro_id = %s)
                """, (parametro_id,))
        
        cur.execute(f"""
                DELETE  FROM  {schema_db}.variavel
                WHERE parametro_id = %s
                """, (parametro_id,))
            
        conn.commit()
        
        return jsonify({"message": "Parametro atualizado com sucesso"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

def delete_parametro(parametro_id):
    sas_user_id = request.headers.get('sas_user_id')
    sas_user_name = request.headers.get('sas_user_name')
    sas_user_email = request.headers.get('sas_user_email')

    if not sas_user_id:
        return jsonify({"error": "Não foi possível determinar o usuário que está realizando a ação"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Atualizar o registro na tabela parametro
        cur.execute(f"""
            UPDATE {schema_db}.parametro
            SET status_code = '003',
                updated_at = NOW(),
                deleted_at = NOW()
            WHERE id = %s
        """, (parametro_id,))
        conn.commit()
        
        # Inserir um novo registro na tabela evento
        cur.execute(f"""
            INSERT INTO {schema_db}.evento (created_at, status_code, sas_user_id, parametro_id, sas_user_name, sas_user_email)
            VALUES (NOW(), '003', %s, %s, %s, %s)
        """, (sas_user_id, parametro_id, sas_user_name, sas_user_email))
        conn.commit()
        
        # Retornar uma resposta JSON indicando sucesso
        return jsonify({"message": "Registro deletado com sucesso"}), 200
    
    except Exception as e:
        conn.rollback()
        print(f"Erro ao deletar parâmetro: {e}")
        return jsonify({"error": "Erro ao deletar parâmetro"}), 500
    
    finally:
        cur.close()
        conn.close()


# Variaveis
def create_variaveis(parametro_id):
    body = request.json
    conn = get_db_connection()
    cur = conn.cursor()

    print("body",body)
    try:
        variaveis_to_insert = []
        listas_to_insert = []

        for value in body:
            variaveis_lista = value.get("variaveis_lista")
            nome = value.get("nome")
            descricao = value.get("descricao")
            tipo = value.get("tipo")
            is_chave = value.get("is_chave")
            tamanho = value.get("tamanho")
            qtd_casas_decimais = value.get("qtd_casas_decimais")

            print("value",value)

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
            

            cur.execute(f"""
                DELETE FROM  {schema_db}.variavel_lista
                WHERE variavel_id  IN (SELECT id FROM  {schema_db}.variavel WHERE parametro_id = %s)
                """, (parametro_id,))
        
            cur.execute(f"""
                DELETE  FROM  {schema_db}.variavel
                WHERE parametro_id = %s
                """, (parametro_id,))
            
            # Adicionando informações à lista temporária
            variaveis_to_insert.append((nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id, variaveis_lista))

        # Inserindo variáveis na tabela temporária
        for var_info in variaveis_to_insert:
            nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id, variaveis_lista = var_info
            var_id = str(uuid.uuid4())


            # Verifica se o nome da variável já existe
            cur.execute(f"SELECT 1 FROM  {schema_db}.variavel WHERE nome = %s AND parametro_id = %s", (nome, parametro_id))
            existing_variable = cur.fetchone()

            if existing_variable:
                return jsonify({"error": "Nome da variável já existe para este parâmetro","campos_error": ["nome_variavel"]}), 400
            
            cur.execute(
                f"""
                INSERT INTO {schema_db}.variavel (id, nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (var_id, nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id)
            )

            cur.execute(
                f"""
                DELETE FROM  {schema_db}.dado
                WHERE parametro_id = %s
                """,
                (parametro_id,))

            # Se o tipo for LISTA e houver variáveis de lista, adicione à lista temporária
            if tipo == "LISTA" and variaveis_lista and len(variaveis_lista) > 0:
                existing_list_names = set()  # Conjunto para armazenar nomes de lista existentes

                for lista_info in variaveis_lista:
                    lista_nome = lista_info['nome']
                    is_visivel = lista_info['is_visivel']

                    # Verificar se o nome da lista já existe
                    if lista_nome in existing_list_names:
                        return jsonify({"error": f"Nome da lista '{lista_nome}' já existe na variável '{nome}'","campos_error": ["nome_lista"]}), 400

                    existing_list_names.add(lista_nome)

                    listas_to_insert.append((lista_nome, is_visivel, var_id))

        # Inserindo listas na tabela temporária
        for lista_info in listas_to_insert:
            lista_nome, is_visivel, var_id = lista_info
            cur.execute(
                f"""
                INSERT INTO {schema_db}.variavel_lista (nome, is_visivel, variavel_id)
                VALUES (%s, %s, %s)
                """,
                (lista_nome, is_visivel, var_id)
            )

        conn.commit()
        return jsonify({"message": "Variáveis criadas com sucesso"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()



def create_dados(parametro_id):
    body = request.json  # Recebe o JSON do corpo da requisição

    # Verifica se o corpo da requisição é uma lista
    if not isinstance(body, list):
        return jsonify({"error": "Corpo da requisição deve ser uma lista de objetos"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            f"""
                DELETE FROM  {schema_db}.dado
                WHERE parametro_id = %s
            """, (parametro_id,))
            

        for value in body:
            informacao = json.dumps(value.get("informacao"))  # Serializa o dicionário para JSON
            sas_key = value.get("sas_key")
            sas_value = value.get("sas_value")
            sas_type = value.get('sas_type')

            # Validando os campos
            if not informacao:
                return jsonify({"error": "'informacao' é obrigatório", "campos_error": ["informacao"]}), 400
            if not sas_key:
                sas_key = ''
            if not sas_value:
                return jsonify({"error": "'sas_value' é obrigatório", "campos_error": ["sas_value"]}), 400
            

            # Inserindo na tabela 'dado'
            cur.execute(
                f"""
                INSERT INTO {schema_db}.dado (informacao, sas_key, sas_value, parametro_id, created_at, sas_type)
                VALUES (%s, %s, %s, %s, NOW(), %s)
                """,
                (informacao, sas_key, sas_value, parametro_id, sas_type)
            )
            conn.commit()

        return jsonify({"message": "Dados criados com sucesso"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()


def atualizar_status(parametro_id):
    sas_user_id = request.headers.get('Sas-User-Id')
    sas_user_name = request.headers.get('Sas-User-Name')
    sas_user_email = request.headers.get('Sas-User-Email')

    data = request.get_json()
    status_code  =  data.get('status_code')
    justificativa = data.get('justificativa') if data.get('justificativa') is not None else None

    try:
        if status_code is None:
            return jsonify({"error": "O campo 'status_code' é obrigatório"}), 400

        # Conectar ao banco de dados
        conn = get_db_connection()
        cur = conn.cursor()

                # 1. Criar um novo evento na tabela 'evento'
        cur.execute(f"""
                INSERT INTO {schema_db}.evento (justificativa, status_code, sas_user_id, sas_user_name, sas_user_email, parametro_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (justificativa, status_code, sas_user_id, sas_user_name, sas_user_email, parametro_id))
        evento_id = cur.fetchone()[0]

        cur.execute(f"""
                UPDATE {schema_db}.parametro
                SET status_code = '005'
                WHERE id = %s
        """, (parametro_id,))
            
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({"message": "Status atualizado com sucesso", "evento_id": evento_id}), 200

    except (Exception) as error:
            return jsonify({"error": f"Falha ao atualizar o status: {error}"}), 500