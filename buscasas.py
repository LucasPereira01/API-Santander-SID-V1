import requests
import ssl
import warnings


domainId = 'e9abe3c6-5ca9-4432-87fe-006c7236fec7'
warnings.filterwarnings("ignore")


#se quiser armazenar num arquivo
def read_file():
    file_path = 'token.dat' 
    with open(file_path, 'r') as file:
        for line in file:
            return(line.strip())


def write_file(s):
    file1 = open('token.dat', 'w')
    # Writing a string to file
    file1.write(s)   
    # Closing file
    file1.close()


#a cada uma hora o token fica invalido
def get_token():
    url = "https://server.demo.sas.com/SASLogon/oauth/token"

    payload = 'username=sasdemo&password=Orion123&grant_type=password'
    headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Authorization': 'Basic c2FzLmVjOg==',
    'Cookie': 'sas-ingress-nginx=9e9148b7e9ef1d961e906ed16b3ad80e|999d8d05a8ecead1a5884cb51c3c5d02; JSESSIONID=468CB9D45ED2DDDA01AC50C37F5C9ADA'
    }
    #para resolver o erro de certificado da maquina:
    #requests.get('https://github.com', verify='/path/to/certfile')
    response = requests.request("POST", url, headers=headers, data=payload, verify=False)
    r = response.json()
    #print(r['access_token'])
    return(r['access_token'])
    schedule.every(55).minutes.do(get_token)    


#1000 requisies => 1 token
def conf_sas(token):
    
    url = "https://server.demo.sas.com/catalog/instances"

    payload = {}
    #crio a autorizacao Bearer
    autorization = f'Bearer {token}'
    headers = {
    'Authorization': autorization,
    'Cookie': 'sas-ingress-nginx=18f200a6fe34881de5eda1d98bcfcc5e|c71550a7073ca099de18546200bef179'
    }
    response = requests.request("GET", url, headers=headers, data=payload, verify = False)
    if response.status_code ==200:
        r = response.json()
        return r
    else:
        print(response)
        get_token()        


def armaze_token():
    token = get_token()
    #gravo o token no arquivo
    write_file(token)
    return


def get_domains(token):
    url = "https://server.demo.sas.com/referenceData/domains"

    payload = {}
    #crio a autorizacao Bearer
    autorization = f'Bearer {token}'
    headers = {
    'Authorization': autorization,
    'Accept': 'application/vnd.sas.collection+json, applcation/json, application/vnd.sas.errpr+json'
    
    }
    response = requests.request("GET", url, headers=headers, data=payload, verify = False)
    if response.status_code ==200:
        r = response.json()

        for i in r['items']:
            print(i['id'])
            print(i['name'])

        return r
    else:
        print(response)
        get_token()


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


def get_etag(token):
    url = "https://server.demo.sas.com/referenceData/domains/e9abe3c6-5ca9-4432-87fe-006c7236fec7/currentContents/"
    ## retorna todas  as informaçoes de alterações e updates do domains e suas colunas

    autorization = f'Bearer {token}'
    headers = {
    'Authorization': autorization,
    'Accept': 'application/vnd.sas.collection+json, application/json, application/vnd.sas.errpr+json'
    }
    response = requests.request("GET", url, headers=headers, verify = False)
    if response.status_code ==200:
        etag = response.headers.get('ETag')
        print(etag)

        return etag
    else:
        print(response)
        print(response.text)


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
    
    autorization = f'Bearer {token}'
    headers = {
        "If-Match": etag,
        "Content-Type": "application/json-patch+json",
        "Authorization": autorization,
        "Accept": "application/vnd.sas.collection+json, application/json, application/vnd.sas.error+json"
    }
    
    response = requests.request("PATCH", url, headers=headers, json=payload, verify=False)
    print(response.json())
    
    if response.status_code == 200:
        r = response.json()
        if not r:
            raise ValueError("Dados não fornecidos")
        return r
    else:
        print(response)
        get_token()
