from flask import Flask, make_response, jsonify, request
from db import get_db_connection
import uuid
import json
import re


# Parametros 
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
    status_code = body.get("status_code")
    parametro_id = str(uuid.uuid4())
    

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
            return jsonify({"error":"Nome do Parametro ja existe para esta Politica","campos_error":["nome"]}),400

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

def lista_parametros_data_table():
    # Obtenha o corpo da solicitação
    body = request.get_json()

    # Extraia os parâmetros do corpo da solicitação
    offset = body.get('offset', 0)
    limit = body.get('limit', 25)
    order = body.get('order', None)
    count = body.get('count', 0)
    filters = body.get('filters', [])

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Construa a consulta SQL baseada nos parâmetros fornecidos
        query = "SELECT * FROM parametro"

        # Aplicar filtros
        if filters:
            query += " WHERE "
            for i, f in enumerate(filters):
                query += f"{f['column']} ILIKE '%{f['value']}%'"
                if i < len(filters) - 1:
                    query += " AND "

        # Aplicar a ordenação
        if order:
            query += f" ORDER BY {order['column']} {order['direction']}"

        # Aplicar limite e deslocamento
        query += f" LIMIT {limit} OFFSET {offset}"

        # Executar a consulta SQL
        cur.execute(query)
        parametros = cur.fetchall()

        # Verificar se precisa retornar o total de registros
        if count:
            cur.execute("SELECT COUNT(*) FROM parametro")
            total_registros = cur.fetchone()[0]
        else:
            total_registros = None

        # Montar a resposta
        response = {
            "offset": offset,
            "limit": limit,
            "order": order,
            "count": total_registros,
            "items": parametros
        }

        return response

    except Exception as e:
        print(f"Erro ao listar parâmetros: {e}")
        return None

    finally:
        cur.close()
        conn.close()

def get_all_parametro():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT 
                p.id, p.nome, p.descricao, p.modo, p.data_hora_vigencia, p.versao, p.is_vigente, 
                p.sas_domain_id, p.sas_content_id, p.created_at, p.updated_at, p.deleted_at, 
                p.status_code, p.parametro_parent_id, p.politica_id, p.sas_user_id,
                po.*,
                c.*, 
                s.*,
                d.informacao, d.sas_key, d.sas_value,
                COALESCE(c.sas_test_folder_id::text, null) as sas_test_folder_id,
                COALESCE(c.sas_test_parent_uri, null) as sas_test_parent_uri
            FROM public.parametro p
            JOIN politica po ON p.politica_id = po.id
            JOIN clusters c ON po.cluster_id = c.id
            JOIN segmento s ON c.segmento_id = s.id
            LEFT JOIN dado d ON p.id = d.parametro_id
            """
        )
        parametros = cur.fetchall()

    
        parametros_json = [
                    {
                        "id": row[0],
                        "nome": row[1],
                        "descricao": row[2],
                        "modo": row[3],
                        "data_hora_vigencia": row[4],
                        "versao": row[5],
                        "is_vigente": row[6],
                        "sas_domain_id": row[7],
                        "sas_content_id": row[8],
                        "created_at": row[9],
                        "updated_at": row[10],
                        "deleted_at": row[11],
                        "status_code": row[12],
                        "parametro_parent_id": row[13],
                        "politica_id": row[14],
                        "sas_user_id": row[15],
                        "politica": {    #  nome, descricao, is_ativo, sas_folder_id, sas_parent_uri, created_at, updated_at, sas_test_folder_id, sas_test_parent_uri
                            "id": row[16],
                            "nome": row[17],
                            "descricao": row[18],
                            "is_ativo": row[19],
                            "sas_folder_id": row[20],
                            "sas_parent_uri": row[21],
                            "created_at": row[22],
                            "updated_at": row[23],
                            "cluster_id": row[24],
                            "sas_test_folder_id": row[25],
                            "sas_test_parent_uri": row[26],
                            "cluster": {
                                "id": row[27],
                                "nome": row[28],
                                "descricao": row[29],
                                "is_ativo": row[30],
                                "sas_folder_id": row[31],
                                "sas_parent_uri": row[32],
                                "created_at": row[33],
                                "updated_at": row[34],
                                "segmento_id": row[35],
                                "sas_test_folder_id": row[36],
                                "sas_test_parent_uri": row[37],
                                "segmento": {
                                    "id": row[38],
                                    "nome": row[39],
                                    "descricao": row[40],
                                    "is_ativo": row[41],
                                    "sas_folder_id": row[42],
                                    "sas_parent_uri": row[43],
                                    "created_at": row[44],
                                    "updated_at": row[45],
                                    "sas_test_folder_id": row[46],
                                    "sas_test_parent_uri": row[47],
                                }
                            }
                        },
                        "dado": {
                            "informacao": row[48],
                            "sas_key": row[49],
                            "sas_value": row[50]
                        }
                    }
                    for row in parametros
                ]

        return parametros_json
    except Exception as e:
        print(f"Erro ao listar segmentos: {e}")
        return []
    finally:
        cur.close()
        conn.close()



def get_parametro_by_id(parametro_id):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT p.id, p.nome, p.descricao, p.modo, p.data_hora_vigencia, p.versao, p.is_vigente, 
                   p.sas_domain_id, p.sas_content_id, p.created_at, p.updated_at, p.deleted_at, 
                   p.status_code, p.parametro_parent_id, p.politica_id, p.sas_user_id,
                   po.id AS politica_id, po.nome AS politica_nome, po.descricao AS politica_descricao, po.is_ativo AS politica_ativo,
                   c.id AS cluster_id, c.nome AS cluster_nome, c.descricao AS cluster_descricao, c.is_ativo AS cluster_ativo,
                   s.id AS segmento_id, s.nome AS segmento_nome, s.descricao AS segmento_descricao, s.is_ativo AS segmento_ativo
            FROM public.parametro p
            JOIN politica po ON p.politica_id = po.id
            JOIN clusters c ON po.cluster_id = c.id
            JOIN segmento s ON c.segmento_id = s.id
            WHERE p.id = %s
            """
        , (parametro_id,))
        parametro = cur.fetchone()

        if not parametro:
            return jsonify({"error": "Parametro não encontrado"}), 404

        parametro_json ={
            "id": parametro[0],
            "nome": parametro[1],
            "descricao": parametro[2],
            "modo": parametro[3],
            "data_hora_vigencia": parametro[4],
            "versao": parametro[5],
            "is_vigente": parametro[6],
            "sas_domain_id": parametro[7],
            "sas_content_id": parametro[8],
            "created_at": parametro[9],
            "updated_at": parametro[10],
            "deleted_at": parametro[11],
            "status_code": parametro[12],
            "parametro_parent_id": parametro[13],
            "politica_id": parametro[14],
            "sas_user_id": parametro[15],
            "politica": {
                "id": parametro[16],
                "nome": parametro[17],
                "descricao": parametro[18],
                "is_ativo": parametro[19],
                "cluster": {
                    "id": parametro[20],
                    "nome": parametro[21],
                    "descricao": parametro[22],
                    "is_ativo": parametro[23],
                    "segmento": {
                        "id": parametro[24],
                        "nome": parametro[25],
                        "descricao": parametro[26],
                        "segmento_ativo": parametro[27]
                    }
                }
            }
        }

        return jsonify(parametro_json), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

def update_parametro(parametro_id):
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()

    try:    
        # Verificar se o parâmetro existe
        cur.execute("SELECT * FROM public.parametro WHERE id = %s", (parametro_id,))
        existing_parametro = cur.fetchone()

        if not existing_parametro:
            return jsonify({"error": "Parametro não encontrado"}), 404

        # Extrair os dados do JSON
        nome = data.get("nome")
        descricao = data.get("descricao")
        modo = data.get("modo")
        data_hora_vigencia = data.get("data_hora_vigencia")
        versao = data.get("versao")
        is_vigente = data.get("is_vigente")
        sas_domain_id = data.get("sas_domain_id")
        sas_content_id = data.get("sas_content_id")
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        deleted_at = data.get("deleted_at")
        status_code = data.get("status_code")
        parametro_parent_id = data.get("parametro_parent_id")
        politica_id = data.get("politica_id")
        sas_user_id = data.get("sas_user_id")

        # Atualizar o parâmetro no banco de dados
        cur.execute("""
            UPDATE public.parametro
            SET nome = %s, descricao = %s, modo = %s, data_hora_vigencia = %s, versao = %s, is_vigente = %s,
                sas_domain_id = %s, sas_content_id = %s, created_at = %s, updated_at = %s, deleted_at = %s,
                status_code = %s, parametro_parent_id = %s, politica_id = %s, sas_user_id = %s
            WHERE id = %s
        """, (nome, descricao, modo, data_hora_vigencia, versao, is_vigente, sas_domain_id, sas_content_id,
              created_at, updated_at, deleted_at, status_code, parametro_parent_id, politica_id, sas_user_id,
              parametro_id))

        conn.commit()

        return jsonify({"message": "Parametro atualizado com sucesso"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

def delete_parametro(parametro_id):
    ...


# Variaveis
def create_variaveis(parametro_id):
    body = request.json
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        variaveis_to_insert = []
        listas_to_insert = []

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
            
            # Adicionando informações à lista temporária
            variaveis_to_insert.append((nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id, variavel_lista))

        # Inserindo variáveis na tabela temporária
        for var_info in variaveis_to_insert:
            nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id, variavel_lista = var_info
            var_id = str(uuid.uuid4())

            # Verifica se o nome da variável já existe
            cur.execute("SELECT 1 FROM variavel WHERE nome = %s AND parametro_id = %s", (nome, parametro_id))
            existing_variable = cur.fetchone()

            if existing_variable:
                return jsonify({"error": "Nome da variável já existe para este parâmetro","campos_error": ["nome_variavel"]}), 400
            cur.execute(
                """
                INSERT INTO variavel (id, nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (var_id, nome, descricao, tipo, is_chave, tamanho, qtd_casas_decimais, parametro_id)
            )

            # Se o tipo for LISTA e houver variáveis de lista, adicione à lista temporária
            if tipo == "LISTA" and variavel_lista and len(variavel_lista) > 0:
                existing_list_names = set()  # Conjunto para armazenar nomes de lista existentes

                for lista_info in variavel_lista:
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
                """
                INSERT INTO variavel_lista (nome, is_visivel, variavel_id)
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