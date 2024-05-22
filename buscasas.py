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

# Função para escrever o token em um arquivo
def write_file(s):
    with open('token.dat', 'w') as file:
        file.write(s)

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
        response.raise_for_status()

# Função para obter os domínios
def get_domains(token):
    url = "https://server.demo.sas.com/referenceData/domains"
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.sas.collection+json, applcation/json, application/vnd.sas.errpr+json'
    }
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

def get_content(token):
    url = f"https://server.demo.sas.com/referenceData/domains/{domainId}/contents/"
    ## retorna todas  as informaçoes de alterações e updates do domains e suas colunas

    autorization = f'Bearer {token}'
    headers = {
    'Authorization': autorization,
    'Accept': 'application/vnd.sas.collection+json, applcation/json, application/vnd.sas.errpr+json'
    }
    response = requests.request("GET", url, headers=headers, verify = False)
    if response.status_code ==200:
        r = response.json()

        """ for i in r['items']:
            print(i['name'])
            print(i[id]) """
        return r
    else:
        print(response)
        get_token()

def get_curren_contents(token):
    
    url = f"https://server.demo.sas.com/referenceData/domains/{domainId}/currentContents/"
    ## retorna todas  as informaçoes de alterações e updates do domains e suas colunas

    payload = {}
    #crio a autorizacao Bearer
    autorization = f'Bearer {token}'
    headers = {
    'Authorization': autorization,
    'Accept': 'application/vnd.sas.collection+json, applcation/json, application/vnd.sas.errpr+json'
    }
    response = requests.request("GET", url, headers=headers, verify = False)
    if response.status_code ==200:
        r = response.json()

        """ for i in r['items']:
            print(i['name'])
            print(i[id]) """
        return r
    else:
        print(response)
        get_token()



def create_domains(token):
    url = "https://server.demo.sas.com/referenceData/domains/"
    ## retorna todas  as informaçoes de alterações e updates do domains e suas colunas

    payload = "{\n  \"name\": \"serviceLevel\",\n  \"description\": \"The service level designation.\",\n  \"domainType\": \"lookup\"\n}"
    #crio a autorizacao Bearer
    autorization = f'Bearer {token}'
    headers = {
    "Content-Type": "application/vnd.sas.data.reference.domain+json",
    'Authorization': autorization,
    "Accept": "application/vnd.sas.data.reference.domain+json, application/vnd.sas.data.reference.value.list+json, application/json, application/vnd.sas.error+json"
    }
    response = requests.request("POST", url, headers=headers,data=payload, verify = False)
    if response.status_code ==201:
        r = response.json()
        return r
    else:
        print(response)
        get_token()


def create_domains_entries(token):
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
        print(response)
        get_token()

# Função para atualizar as entradas
def update_entries(token):
    etag = get_etag(token)
    if not etag:
        print("Não foi possível obter o ETAG")
        return None
   
    url = "https://server.demo.sas.com/referenceData/domains/e9abe3c6-5ca9-4432-87fe-006c7236fec7/contents/5411fcbc-250a-4dd8-ad4e-38cb65d9ed6f/entries"
   
    payload = [
        {
            "op": "replace",
            "path": "/z",
            "value": "Super Urgente"

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
schedule.every(55).minutes.do(get_token_and_write)