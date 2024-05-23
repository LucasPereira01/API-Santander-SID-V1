from flask import Flask, make_response, jsonify, request
import requests
import warnings
import schedule
import threading
import time

domainId = 'e9abe3c6-5ca9-4432-87fe-006c7236fec7'
warnings.filterwarnings("ignore")

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
    url = "https://server.demo.sas.com/SASLogon/oauth/token"
    payload = 'username=sasdemo&password=Orion123&grant_type=password'
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
    url = "https://server.demo.sas.com/catalog/instances"
    headers = {
        'Authorization': f'Bearer {token}',
        'Cookie': 'sas-ingress-nginx=18f200a6fe34881de5eda1d98bcfcc5e|c71550a7073ca099de18546200bef179'
    }
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        # Se houver um erro, podemos retornar uma mensagem de erro
        return jsonify({"error": response.text}), response.status_code



# Função para obter os domínios e retornar id e nome
def get_domains(token):
    try:
        url = "https://server.demo.sas.com/referenceData/domains"
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.sas.collection+json, application/json, application/vnd.sas.error+json'
        }
        response = requests.get(url, headers=headers, verify=False)
       
        # Verifica se a solicitação foi bem-sucedida (código de status 200)
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
                # Printando informações de debug para cada domínio
                print(f"ID: {domain_data['id']}, Name: {domain_data['name']}")
            return domain_info
        else:
            # Se houver um erro, podemos retornar uma mensagem de erro
            return jsonify({"error": response.text}), response.status_code
    except Exception as e:
        # Se ocorrer uma exceção, retorna uma mensagem de erro genérica
        return {"error": str(e)}, 500  # Código de status HTTP 500 para erro interno do servidor


def get_content(token):
    domain_name = request.json.get("name")  # Obtém o nome do domínio do JSON da solicitação
    if not domain_name:
        return {"error": "O nome do domínio não foi fornecido no corpo da solicitação."}, 400

    # Obtém os dados dos domínios
    domain_info = get_domains(token)
   
    # Verifica se foi obtido corretamente
    if isinstance(domain_info, list):
        # Procura o ID do domínio com base no nome fornecido
        domain = next((domain for domain in domain_info if domain["name"] == domain_name), None)
       
        if domain:
            domainId = domain["id"]
           
            # Agora que temos o ID do domínio, podemos usar para fazer a solicitação de conteúdo
            url = f"https://server.demo.sas.com/referenceData/domains/{domainId}/contents/"
           
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
                    # Cria um novo dicionário para armazenar as informações relevantes
                    content_data = {
                        "id": item.get("id"),
                        "label": item.get("label"),
                        "createdBy": item.get("createdBy"),
                        "creationTimeStamp": item.get("creationTimeStamp"),
                        "modifiedTimeStamp": item.get("modifiedTimeStamp"),
                        "majorNumber": item.get("majorNumber"),
                        "minorNumber": item.get("minorNumber"),            
                        "status": item.get("status"),
                        "standing": item.get("standing"),
                        "version": f"{item.get('majorNumber')}.{item.get('minorNumber')}"
            }
                    # Adiciona o dicionário à lista de itens
                    content_list.append(content_data)

                # Retorna a lista de itens como JSON
                return jsonify(content_list)
            else:
                # Se houver um erro, retornamos a mensagem de erro
                return {"error": response.text}, response.status_code
        else:
            # Se o domínio não for encontrado, retornamos uma mensagem de erro
            return {"error": f"O domínio '{domain_name}' não foi encontrado."}, 404
    else:
        # Se houver um erro ao obter os dados do domínio, retornamos a mensagem de erro
        return domain_info




def get_curren_contents(token): # Busca a ultima versao que esta em produção.
    domain_name = request.json.get("name")  # Obtém o nome do domínio do JSON da solicitação
    if not domain_name:
        return {"error": "O nome do domínio não foi fornecido no corpo da solicitação."}, 400

    # Obtém os dados dos domínios
    domain_info = get_domains(token)
   
    # Verifica se foi obtido corretamente
    if isinstance(domain_info, list):
        # Procura o ID do domínio com base no nome fornecido
        domain = next((domain for domain in domain_info if domain["name"] == domain_name), None)
       
        if domain:
            domainId = domain["id"]
           
            # Agora que temos o ID do domínio, podemos usar para fazer a solicitação de conteúdo
            url = f"https://server.demo.sas.com/referenceData/domains/{domainId}/currentContents/"
           
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
                    # Cria um novo dicionário para armazenar as informações relevantes
                    content_data = {
                        "id": item.get("id"),
                        "label": item.get("label"),
                        "createdBy": item.get("createdBy"),
                        "creationTimeStamp": item.get("creationTimeStamp"),
                        "modifiedTimeStamp": item.get("modifiedTimeStamp"),
                        "majorNumber": item.get("majorNumber"),
                        "minorNumber": item.get("minorNumber"),            
                        "status": item.get("status"),
                        "standing": item.get("standing"),
                        "version": f"{item.get('majorNumber')}.{item.get('minorNumber')}"
            }
                    # Adiciona o dicionário à lista de itens
                    content_list.append(content_data)

                # Retorna a lista de itens como JSON
                return jsonify(content_list)
            else:
                # Se houver um erro, retornamos a mensagem de erro
                return {"error": response.text}, response.status_code
        else:
            # Se o domínio não for encontrado, retornamos uma mensagem de erro
            return {"error": f"O domínio '{domain_name}' não foi encontrado."}, 404
    else:
        # Se houver um erro ao obter os dados do domínio, retornamos a mensagem de erro
        return domain_info



def create_domains(token):
    body = request.json
    url = "https://server.demo.sas.com/referenceData/domains/"

    # Criação do payload com base nos dados recebidos na solicitação
    payload = {
        "name": body.get("name"),  # Usando get() para evitar erros se a chave não existir
        "description": body.get("description"),
        "domainType": body.get("domainType")
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
        # Se a criação for bem-sucedida, retornamos os dados do domínio criado
        return jsonify(response.json())
    else:
        # Se houver um erro, podemos retornar uma mensagem de erro
        return jsonify({"error": "Failed to create domain"}), response.status_code


def create_domains_entries(token):
    body = request.json
    url = "https://server.demo.sas.com/referenceData/domains/e9abe3c6-5ca9-4432-87fe-006c7236fec7/contents"
    ## retorna todas  as informaçoes de alterações e updates do domains e suas colunas

    payload = "{\n  \"label\": \"lookup1.0\",\n  \"keyLabel\": \"Severity\",\n  \"valueLabel\": \"SLA Class\",\n  \"status\": \"developing\",\n  \"majorNumber\": 1,\n  \"minorNumber\": 1,\n  \"entries\": [\n    {\n      \"key\": \"A\",\n      \"value\": \"5\"\n    },\n    {\n      \"key\": \"B\",\n      \"value\": \"10\"\n    }\n  ]\n}"
    #crio a autorizacao Bearer
    autorization = f'Bearer {token}'
    headers = {
    "Content-Type": "application/vnd.sas.data.reference.domain.content.full+json",
    "Authorization": autorization,
    "Accept": "application/vnd.sas.data.reference.domain.content.full+json, application/vnd.sas.data.reference.value.list.content.full+json, application/json, application/vnd.sas.error+json"
}
    response = requests.request("POST", url, headers=headers,data=payload, verify = False)
    if response.status_code ==201:
        r = response.json()
        if not r:
            raise ValueError("Dados não fornecidos")
        return r
    else:
        # Se houver um erro, podemos retornar uma mensagem de erro
        return jsonify({"error": response.text}), response.status_code
# Função para atualizar as entradas
def update_entries(token):
    try:
        etag = get_etag(token)
        if not etag:
            raise ValueError("Failed to get ETAG")
       
        url = "https://server.demo.sas.com/referenceData/domains/e9abe3c6-5ca9-4432-87fe-006c7236fec7/contents/5411fcbc-250a-4dd8-ad4e-38cb65d9ed6f/entries"
       
        payload =[
    {
        "op": "replace",
        "path": "/z",
        "value": "Novo Valor Aqui"
    },
    {
        "op": "add",
        "path": "/teste",
        "value": "Super Urgente"
    },
    {
        "op": "replace",
        "path": "/b",
        "value": "Critical"
    }
]
       
        headers = {
            "If-Match": etag,
            "Content-Type": "application/json-patch+json",
            "Authorization": f'Bearer {token}',
            "Accept": "application/vnd.sas.collection+json, application/json, application/vnd.sas.error+json"
        }
       
        response = requests.patch(url, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        return response.json()
    except:
        # Se houver um erro, podemos retornar uma mensagem de erro
        return jsonify({"error": response.text}), response.status_code

# Função para obter o ETAG
def get_etag(token):
    url = "https://server.demo.sas.com/referenceData/domains/e9abe3c6-5ca9-4432-87fe-006c7236fec7/currentContents/"
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.sas.collection+json, application/json, application/vnd.sas.errpr+json'
    }
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.headers.get('ETag')
    else:
        response.raise_for_status()

# Programamos a atualização do token a cada 55 minutos
get_token_and_write()
schedule.every(55).minutes.do(get_token_and_write)