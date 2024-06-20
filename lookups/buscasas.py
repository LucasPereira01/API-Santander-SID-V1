from flask import Flask, make_response, jsonify, request
import requests
import schedule
from db import get_db_connection
from dotenv import load_dotenv
import os
import uuid

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso à variável de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
url_path_sid_analytics = os.getenv("URL_PATH_ANALYTICS_SID")
user_name_sid = os.getenv("USER_NAME_SID")
password_sid = os.getenv("PASSWORD_SID")
schema_db = os.getenv("SCHEMA_DB")


# Função para ler o token de um arquivo
def read_file():
    file_path = 'token.dat'
    with open(file_path, 'r') as file:
        for line in file:
            return line.strip()
    print('token salvo')


# Função para escrever o token em um arquivo
def write_file(s):
    with open('token.dat', 'w') as file:
        file.write(s)
    print('arquivo token.dat criado')


# Função para obter o token
def get_token():
    url = f"{url_path_sid}/SASLogon/oauth/token"
    payload = f'username={user_name_sid}&password={password_sid}&grant_type=password'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic c2FzLmVjOg==',
        'Cookie': 'sas-ingress-nginx=9e9148b7e9ef1d961e906ed16b3ad80e|999d8d05a8ecead1a5884cb51c3c5d02; JSESSIONID=468CB9D45ED2DDDA01AC50C37F5C9ADA'
    }
    response = requests.post(url, headers=headers, data=payload, verify=False)
    if response.status_code == 200:
        print('token gerado')
        return response.json()['access_token']
    else:
        response.raise_for_status()


# Função para obter o token e escrever no arquivo
def get_token_and_write():
    token = get_token()
    write_file(token)


# Função para configurar o SAS
def conf_sas(token):
    url = f"{url_path_sid}/catalog/instances"
    headers = {
        'Authorization': f'Bearer {token}',
        'Cookie': 'sas-ingress-nginx=18f200a6fe34881de5eda1d98bcfcc5e|c71550a7073ca099de18546200bef179'
    }
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        return jsonify({"error": response.text}), response.status_code


# Função para obter os domínios e retornar id e nome
def get_domains(token):
    try:
        url =f"{url_path_sid}/referenceData/domains"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.sas.collection+json, application/json, application/vnd.sas.error+json'
        }
        response = requests.get(url, headers=headers, verify=False)
       
        if response.status_code == 200:
            domain_info = []
            for item in response.json()["items"]:
                domain_data = {
                    "id": item["id"],
                    "name": item["name"],
                    "creationTimeStamp": item["creationTimeStamp"],
                    "modifiedTimeStamp": item["modifiedTimeStamp"],
                    "createdBy": item["createdBy"],
                    "modifiedBy": item["modifiedBy"]
                }
                domain_info.append(domain_data)
            return domain_info
        else:
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        return {"error": str(e)}, 500


def get_content(token, name=None):
    domain_name = request.json.get("name") if not name else name
    if not domain_name:
        return {"error": "O nome do domínio não foi fornecido."}, 400

     # Obtém os dados dos domínios
    domain_info = get_domains(token)

    # Verifica se foi obtido corretamente
    if isinstance(domain_info, list):
        # Procura o ID do domínio com base no nome fornecido
        domain = next((domain for domain in domain_info if domain["name"] == domain_name), None)

        if domain:
            domainId = domain["id"]

            url = f"{url_path_sid}/referenceData/domains/{domainId}/contents/"

            authorization = f'Bearer {token}'
            headers = {
                'Authorization': authorization,
                'Accept': 'application/vnd.sas.collection+json, application/json, application/vnd.sas.error+json'
            }

            response = requests.get(url, headers=headers, verify=False)

            if response.status_code == 200:
                etag = response.headers.get('ETag')

                content_list = []

                for item in response.json().get('items', []):
                    for link in item.get('links', []):
                        if link.get('rel') == 'self':
                            uri = link.get('uri')
                            break  
                    else:
                        uri = None

                    content_data = {
                        "id": item.get("id"),
                        "label": item.get("label"),
                        "createdBy": item.get("createdBy"),
                        "creationTimeStamp": item.get("creationTimeStamp"),
                        "modifiedTimeStamp": item.get("modifiedTimeStamp"),
                        "uri": uri,  # Usa a URI obtida dos links
                        "majorNumber": item.get("majorNumber"),
                        "minorNumber": item.get("minorNumber"),
                        "status": item.get("status"),
                        "standing": item.get("standing"),
                        "version": f"{item.get('majorNumber')}.{item.get('minorNumber')}"
                    }
                    content_list.append(content_data)

                # Retorna a lista de itens e o ETAG em um dicionário
                return {"content_list": content_list, "etag": etag}
            else:
                return {"error": response.text}, response.status_code
        else:
            return {"error": f"O domínio '{domain_name}' não foi encontrado."}, 404
    else:
        return domain_info


def get_current_contents(token):
    domain_name = request.json.get("name")  # Obtém o nome do domínio do JSON da solicitação
    if not domain_name:
        return {"error": "O nome do domínio não foi fornecido no corpo da solicitação."}, 400

    # Obtém os dados dos domínios
    domain_info = get_domains(token)
   
    if isinstance(domain_info, list):
        # Procura o ID do domínio com base no nome fornecido
        domain = next((domain for domain in domain_info if domain["name"] == domain_name), None)
       
        if domain:
            domainId = domain["id"]
           
            # Agora que temos o ID do domínio, podemos usar para fazer a solicitação de conteúdo
            url = f"{url_path_sid}/referenceData/domains/{domainId}/currentContents/"
           
            # Autorização e headers
            authorization = f'Bearer {token}'
            headers = {
                'Authorization': authorization,
                'Accept': 'application/vnd.sas.collection+json, application/json, application/vnd.sas.error+json'
            }
           
            # Fazendo a solicitação GET
            response = requests.get(url, headers=headers, verify=False)
           
            if response.status_code == 200:
                # Inicializa uma lista para armazenar os itens
                content_list = []

                # Itera sobre os itens do JSON de resposta
                for item in response.json().get('items', []):
                    # Extrai as informações relevantes de cada item
                    content_data = {
                        "commencedTimeStamp": item.get("commencedTimeStamp"),
                        "contentId": item.get("contentId"),
                        "domainId": item.get("domainId"),
                        "id": item.get("id"),
                        "status": item.get("status"),
                        "versionId": item.get("versionId"),
                        "name": request.json.get("name")
                    }
                    # Adiciona o dicionário à lista de itens
                    content_list.append(content_data)

                return make_response(jsonify(content_list))
            else:
                return {"error": response.text}, response.status_code
        else:
            return {"error": f"O domínio '{domain_name}' não foi encontrado."}, 404
    else:
        return domain_info


def create_domains(token):
    domains = get_domains(token)
    body = request.json
    name = body.get("name")
    id_politica = body.get("id_politica")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(f"SELECT * FROM {schema_db}.politica WHERE id = %s",(id_politica,))
    politica = cur.fetchone()
    if not politica:
        return jsonify({"error":"Politica nao encontrado"}),400
        

    sas_parent_folder_uri_cluster = politica[5]
    
    # Verifica se o nome do novo domínio já existe
    for domain in domains:
        if domain["name"] == name:
            return jsonify({"error": f"O domínio '{name}' já existe."}), 400
    
    url = f"{url_path_sid}/referenceData/domains?parentFolderUri={sas_parent_folder_uri_cluster}"

    # Criação do payload com base nos dados recebidos na solicitação
    payload = {
        "name": name,
        "description": body.get("description"),
        "domainType": "lookup",
        "checkout":True
    }

    # Criação do cabeçalho de autorização
    authorization = f'Bearer {token}'
    headers = {
        "Content-Type": "application/vnd.sas.data.reference.domain+json",
        "Authorization": authorization,
        "Accept": "application/vnd.sas.data.reference.domain+json, application/vnd.sas.data.reference.value.list+json, application/json, application/vnd.sas.error+json"
    }

    # Envio da solicitação POST para criar o domínio
    response = requests.post(url, headers=headers, json=payload, verify=False)
    if response.status_code == 201:
        # Extrai informações importantes do JSON de resposta
        domain_info = response.json()
        relevant_info = {
            "name": domain_info["name"],
            "description": domain_info["description"],
            "domainType": domain_info["domainType"],
            "id": domain_info["id"],
            "creationTimeStamp": domain_info["creationTimeStamp"],
            "modifiedBy": domain_info["modifiedBy"],
            "modifiedTimeStamp": domain_info["modifiedTimeStamp"]
        }
        
        # Retorna as informações importantes junto com a resposta
        return jsonify({"domain_created": relevant_info}), 201
    else:
        # Se houver um erro, podemos retornar uma mensagem de erro
        return jsonify({"error": "Failed to create domain","json":response.json()}), response.status_code
    

def create_domains_entries(token):
    body = request.json
    domain_name = body.get("name")
    
    # Verifica se o nome do domínio existe na lista de domínios
    domain_exists = False
    domain_id = None
    all_domains = get_domains(token)
    for domain in all_domains:
        if domain["name"] == domain_name:
            domain_exists = True
            domain_id = domain["id"]
            break
    
    if not domain_exists:
        return jsonify({"error": f"O domínio '{domain_name}' não foi encontrado."}), 404
    
    # Constrói a URL com o ID do domínio para criar as entradas
    url = f"{url_path_sid}/referenceData/domains/{domain_id}/contents"
    
    # Payload com os dados das entradas
    payload = {
        "label": body.get("name"),  # Use o nome do domínio como label
        "status": "developing",
        "majorNumber": 1,
        "minorNumber": 1,
        "entries": body.get("entries")
    }

    # Cabeçalhos e autorização
    authorization = f'Bearer {token}'
    headers = {
        "Content-Type": "application/vnd.sas.data.reference.domain.content.full+json",
        "Authorization": authorization,
        "Accept": "application/vnd.sas.data.reference.domain.content.full+json, application/vnd.sas.data.reference.value.list.content.full+json, application/json, application/vnd.sas.error+json"
    }
    
    # Solicitação POST para criar as entradas
    response = requests.post(url, headers=headers, json=payload, verify=False)
    if response.status_code == 201:
        return jsonify(response.json()), 201
    else:
        return jsonify({"error": response.text}), response.status_code
    
    
def extract_id_from_uri(uri):
    # A URI é geralmente uma string no formato '/referenceData/domains/{domain_id}/contents/{content_id}'
    # Para extrair o ID, podemos dividir a string pelo caractere '/' e pegar o penúltimo elemento
    uri_parts = uri.split('/')
    return uri_parts[-2] if len(uri_parts) >= 2 else None


def update_entries(token):
    try:
        # Verifica se o nome do domínio foi fornecido
        domain_name = request.json.get("name")
        if not domain_name:
            return {"error": "O nome do domínio não foi fornecido no corpo da solicitação"}, 400
        
        # Obtém informações sobre o conteúdo e o ETAG apenas se o domínio existir
        result = get_content(token, domain_name)
        if "error" in result:
            return result  # Retorna o erro diretamente se ocorrer um erro na função get_content

        content_info = result["content_list"]
        etag = result["etag"]
        
        # Verifica se o conteúdo e o ETAG foram obtidos corretamente
        if not content_info:
            return {"error": "Failed to get content information"}, 500
        if not etag:
            return {"error": "Failed to get ETAG"}, 500
        
        # Lista para armazenar os URIs dos conteúdos correspondentes
        matching_uris = []
        
        # Itera sobre os itens do JSON de resposta da função get_content
        for item in content_info:
            # Obtém o URI do item
            uri = item.get('uri')
            if uri:
                # Extrai o ID da URI
                uri_id = extract_id_from_uri(uri)
                matching_uris.append(uri)
        # Verifica se há URIs correspondentes
        if not matching_uris:
            return {"error": "Nenhuma URI correspondente encontrada para o domínio."}, 404
        
        # Se houver mais de uma URI correspondente, retorne um erro, pois a correspondência é ambígua
        if len(matching_uris) >= 2:
            matched_uri = matching_uris[2]
        else:
            return {"error": "Não há URI correspondente suficiente para atualização"}, 404
        
        
        # Constrói a URL com base na URI correspondente
        url = f"{url_path_sid}{matched_uri}/entries"
        
        # Payload com as operações de atualização
        payload = request.json.get("data")
        
        # Cabeçalhos da requisição
        headers = {
            "If-Match": etag,
            "Content-Type": "application/json-patch+json",
            "Authorization": f'Bearer {token}',
            "Accept": "application/vnd.sas.collection+json, application/json, application/vnd.sas.error+json"
        }
        
        # Solicitação PATCH para atualizar as entradas
        response = requests.patch(url, headers=headers, json=payload, verify=False)
        
        # Verifica se a resposta foi um erro 412 (Precondition Failed)
        if response.status_code == 412:
            # Se sim, obtemos o novo ETag
            new_etag = response.headers.get('ETag')
            
            # Fazemos uma nova solicitação GET para obter as informações atualizadas
            updated_content_info, _ = get_content(token, domain_name)
            
            # Iteramos sobre as informações atualizadas para encontrar o novo ETag correspondente
            for item in updated_content_info:
                if item.get('uri') == matched_uri:
                    new_etag = item.get('etag')
                    break
            
            # Atualizamos os cabeçalhos com o novo ETag
            headers["If-Match"] = new_etag
            
            # Fazemos uma nova solicitação PATCH
            response = requests.patch(url, headers=headers, json=payload, verify=False)
        
        # Verifica se houve sucesso na solicitação PATCH
        if response.status_code == 200:
            return response.json(), response.status_code
        else:
            return {"error": response.text}, response.status_code
    except Exception as e:
        # Se houver um erro, retorna uma mensagem de erro
        return {"error": str(e)}, 500


def create_parametro( id_politica):
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
        cur.execute(f"SELECT * FROM {schema_db}.politica WHERE id = %s", (id_politica,))
        politica = cur.fetchone()
        if not politica:
            return jsonify({"error": "Política não encontrada"}), 400

        segmento_id = str(uuid.uuid4())

        cur.execute(
                    f"""
                        INSERT INTO {schema_db}.parametro (id ,nome, descricao, modo, data_hora_vigencia, versao, is_vigente, status_code, politica_id, sas_user_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (segmento_id, name, descricao,modo,data_hora_vigencia,versao,is_vigente, status_code, id_politica, sas_user_id)
                    )
        conn.commit()
        return jsonify({"error": f"Nao foi possivel Criar o parametro"}), 400

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

def create_domains_and_entries(token, id_politica):
    domains = get_domains(token)
    body = request.json
    name = body.get("name")
    descricao = body.get("description")
    modo = body.get("modo")
    data_hora_vigencia = body.get("data_hora_vigencia")
    versao = body.get("versao")
    status_code = body.get("status_code")
    is_vigente = body.get("is_vigente")
    entries = body.get("entries")

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(f"SELECT * FROM {schema_db}.politica WHERE id = %s", (id_politica,))
        politica = cur.fetchone()
        if not politica:
            return jsonify({"error": "Política não encontrada"}), 400

        sas_parent_folder_uri_cluster = politica[5]

        for domain in domains:
            if domain["name"] == name:
                return jsonify({"error": f"O domínio '{name}' já existe."}), 400

        url = f"{url_path_sid}/referenceData/domains?parentFolderUri={sas_parent_folder_uri_cluster}"

        payload = {
            "name": name,
            "description": body.get("description"),
            "domainType": "lookup",
            "checkout": body.get("checkout")
        }

        authorization = f'Bearer {token}'
        headers = {
            "Content-Type": "application/vnd.sas.data.reference.domain+json",
            "Authorization": authorization,
            "Accept": "application/vnd.sas.data.reference.domain+json, application/vnd.sas.data.reference.value.list+json, application/json, application/vnd.sas.error+json"
        }

        response = requests.post(url, headers=headers, json=payload, verify=False)
        if response.status_code == 201:
            domain_info = response.json()
            relevant_info = {
                "name": domain_info["name"],
                "description": domain_info["description"],
                "domainType": domain_info["domainType"],
                "id": domain_info["id"],
                "creationTimeStamp": domain_info["creationTimeStamp"],
                "modifiedBy": domain_info["modifiedBy"],
                "modifiedTimeStamp": domain_info["modifiedTimeStamp"]
            }

            if entries:
                url_entries = f"{url_path_sid}/referenceData/domains/{domain_info['id']}/contents"

                payload = {
                    "label": body.get("name"),
                    "status": "developing",
                    "entries": body.get("entries")
                }

                headers = {
                    "Content-Type": "application/vnd.sas.data.reference.domain.content.full+json",
                    "Authorization": authorization,
                    "Accept": "application/vnd.sas.data.reference.domain.content.full+json, application/vnd.sas.data.reference.value.list.content.full+json, application/json, application/vnd.sas.error+json"
                }

                response_entries = requests.post(url_entries, headers=headers, json=payload, verify=False)
                if response_entries.status_code == 201:
                    entries_info = response_entries.json()

                    segmento_id = str(uuid.uuid4())

                    cur.execute(
                        f"""
                        INSERT INTO {schema_db}.parametro (id, nome, descricao, modo, data_hora_vigencia, versao, is_vigente, sas_domain_id, sas_content_id, status_code, politica_id, sas_user_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (segmento_id, name, descricao,modo,data_hora_vigencia,versao,True, relevant_info["id"], entries_info["id"], status_code, id_politica, relevant_info["modifiedBy"])
                    )
                    conn.commit()

                    return jsonify({
                        "domain_created": relevant_info,
                        "entries_created": entries_info
                    }), 201

                else:
                    return jsonify({"error": response_entries.text}), response_entries.status_code

            else:
                return jsonify({"domain_created": relevant_info}), 201

        else:
            return jsonify({"error": "Falha ao criar domínio", "json": response.json()}), response.status_code

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()
        conn.close()





# Programamos a atualização do token a cada 55 minutos
get_token_and_write()
schedule.every(55).minutes.do(get_token_and_write)