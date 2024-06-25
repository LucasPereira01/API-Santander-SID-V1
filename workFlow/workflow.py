import requests
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso às variáveis de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
user_name_sid = os.getenv("USER_NAME_SID")
password_sid = os.getenv("PASSWORD_SID")

def login(url_sid, user, password):
    url = f"{url_sid}/SASLogon/oauth/token"
    headers = { "Content-Type": "application/x-www-form-urlencoded" }
    data = {
        "grant_type": "password",
        "username": user,
        "password": password
    }

    authToken = ("sas.cli", "")

    try:
        response = requests.post(
            url=url,
            data=data,
            headers=headers,
            verify=False,
            auth=authToken
        )
        res = response.json()
        token = res['access_token']
        return token
    except Exception as e:
        print(str(e))
        raise

try:
    # Obter o token de autenticação
    token = 'Bearer ' + login(url_path_sid, user_name_sid, password_sid)

    # Exemplo de requisição GET para workflowAssociations
    url = f"{url_path_sid}/modelManagement/workflowAssociations"
    headers = {
        "Authorization": token,
        "Accept": "application/vnd.sas.collection+json, application/json"
    }

    response = requests.get(url, headers=headers, verify=False)
    response.raise_for_status()

    # Converter a resposta JSON em um dicionário Python
    data = response.json()

    # Verificar se há itens na resposta
    if 'items' in data and len(data['items']) > 0:
        # Acessar o primeiro item (no caso de haver mais de um, pode precisar ajustar)
        first_item = data['items'][0]

        # Acessar os campos desejados
        process_id = first_item.get('processId')
        process_name = first_item.get('processName')
        solution_object_id = first_item.get('solutionObjectId')
        solution_object_name = first_item.get('solutionObjectName')
        solution_bject_type = first_item.get('solutionObjectType')

        # Imprimir os valores obtidos
        print(f"ID do processo: {process_id}")
        print(f"Nome do processo: {process_name}")
        print(f"Nome do solution_object_id: {solution_object_id}")
        print(f"Nome do solution_object_name: {solution_object_name}")
        print(f"Nome do solution_bject_type: {solution_bject_type}")
    else:
        print("Nenhuma associação de workflow encontrada.")

    # Adicionar a requisição GET adicional para performanceJobs
    url_performance_jobs = f"{url_path_sid}/modelManagement/performanceTasks/{process_id}/performanceJobs"
    headers_performance_jobs = {
        "Authorization": token,
        "Accept": "application/vnd.sas.collection+json, application/json"
    }

    response_performance_jobs = requests.get(url_performance_jobs, headers=headers_performance_jobs, verify=False)
    response_performance_jobs.raise_for_status()

    # Imprimir a resposta da requisição adicional
    print("\nResposta da requisição para performanceJobs:")
    print(response_performance_jobs.json())

except requests.exceptions.RequestException as e:
    print(f"Erro durante a requisição: {e}")
