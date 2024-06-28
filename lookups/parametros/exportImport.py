import requests
import time
from dotenv import load_dotenv
import os

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso às variáveis de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
user_name_sid = os.getenv("USER_NAME_SID")
password_sid = os.getenv("PASSWORD_SID")
user_name_sid_analitico = os.getenv("USER_NAME_ANALYTICS_SID")
password_sid_analitico = os.getenv("PASSWORD_ANALYTICS_SID")
url_path_sid_analytics = os.getenv("URL_PATH_ANALYTICS_SID")

def login(url_sid, user, password):
    url = f"{url_sid}/SASLogon/oauth/token"
    headers = { 
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic c2FzLmNsaTo="  # Base64 encoding do cliente SAS
    }
    data = {
        "grant_type": "password",
        "username": user,
        "password": password
    }

    try:
        response = requests.post(url=url, data=data, headers=headers, verify=False)
        response.raise_for_status()
        res = response.json()
        token = res['access_token']
        return token
    except requests.exceptions.HTTPError as http_err:
        print(f'Erro HTTP ao fazer login: {http_err}')
    except Exception as err:
        print(f'Erro ao fazer login: {err}')

try:
    # Configurações
    access_token = login(url_path_sid, user_name_sid, password_sid)
    access_token_anlitic = login(url_path_sid_analytics, user_name_sid_analitico, password_sid_analitico)

    # Passo 1: Exportação do conteúdo
    export_url = f'{url_path_sid_analytics}/transfer/exportJobs'

    # Headers correspondentes ao exemplo CURL
    headers = {
        'accept': 'application/vnd.sas.transfer.export.job+json',
        'content-type': 'application/vnd.sas.transfer.export.request+json',
        'Authorization': f'Bearer {access_token_anlitic}',
        'Accept-Encoding': 'application/gzip'
    }
    item_id = '/referenceData/globalVariables/2a7265c3-b958-4c26-a9c7-24c7eeffaa0f'
    

    export_payload = {
        'name': 'Package',
        'items': [item_id],
        'options': None
    }
    print('Export URL',export_url)
    response = requests.post(export_url, headers=headers, json=export_payload, verify=False)

    response.raise_for_status()

    export_id = response.json()['id']
    print(f'Exportação iniciada. Export ID: {export_id}')

    # Passo 2: Verificação do status da exportação
    check_export_url = f'{url_path_sid_analytics}/transfer/exportJobs/{export_id}'
    while True:
        try:
            response = requests.get(check_export_url, headers=headers, verify=False)
            response.raise_for_status()

            data = response.json()
            status = data['state']
            print(f'Status da exportação: {status}')

            if status == 'completed':
                package_uri = data['packageUri']
                print(f'Exportação concluída. Package URI: {package_uri}')
                break
            elif status == 'failed':
                raise Exception('A exportação falhou.')

        except requests.exceptions.HTTPError as http_err:
            print(f'Erro HTTP ao verificar status da exportação: {http_err}')
            break
        except Exception as err:
            print(f'Erro ao verificar status da exportação: {err}')
            break

        time.sleep(10)  # Espera 10 segundos antes de verificar novamente

    if status == 'completed':
        # Passo 3: Download do conteúdo exportado
        download_url = f'{url_path_sid_analytics}{package_uri}'
        download_headers = {
            'Content-Type': 'application/json',
            'accept': 'application/vnd.sas.transfer.package+json',
            'Authorization': f'Bearer {access_token_anlitic}'
        }

        response_download = requests.get(download_url, headers=download_headers, verify=False)
        response_download.raise_for_status()

        with open('conteudo_exportado.json', 'wb') as f:
            f.write(response_download.content)
        print('Conteúdo exportado baixado com sucesso.')

        # Passo 4: Preparação para importação
        upload_url = f'{url_path_sid}/transfer/packages'
        upload_headers = {
            'Authorization': f'Bearer {access_token}'
        }
        files = {
            'file': open('conteudo_exportado.json', 'rb')  # Substitua pelo caminho do seu arquivo local
        }

        response_upload = requests.post(upload_url, headers=upload_headers, files=files, verify=False)
        response_upload.raise_for_status()

        upload_id = response_upload.json()['id']
        print(f'Upload concluído. Upload ID: {upload_id}')

        # Nome do arquivo importado
        imported_filename = response_upload.json()['name']
        print(f'Nome do arquivo importado: {imported_filename}')



        # Passo 5: Importação do conteúdo
        import_url = f'{url_path_sid}/transfer/importJobs'
        import_headers = {
            'Content-type': 'application/vnd.sas.transfer.import.request+json',
            'Accept': 'application/vnd.sas.transfer.import.job+json',
            'Authorization': f'Bearer {access_token}'
        }

        import_data = {
            'name': imported_filename,
            'packageUri': f'/transfer/packages/{upload_id}',
            'mapping': {
                'version': 1
            }
        }
        # /folders/folders/bf48e7eb-7e7d-4d6b-912b-00cf0ad382b4
        #/folders/folders/bf48e7eb-7e7d-4d6b-912b-00cf0ad382b4
        print(import_data)

        response_import = requests.post(import_url, headers=import_headers, json=import_data, verify=False)
        response_import.raise_for_status()

        import_id = response_import.json()['id']
        print(f'Importação iniciada. Import ID: {import_id}')

        # Passo 6: Verificação do status da importação
        check_import_url = f'{url_path_sid}/transfer/importJobs/{import_id}/state'
        header_check = {
            'Content-type': 'application/vnd.sas.collection+json',
            'Authorization': f'Bearer {access_token}'
        }

        while True:
            try:
                response = requests.get(check_import_url, headers=header_check, verify=False)
                data = response.text
                status = data
                print(f'Status da importação: {status}')

                if status == 'completed':
                    print('Importação concluída com sucesso.')
                    break
                elif status == 'failed':
                    raise Exception('A importação falhou.')

                time.sleep(10)  # Espera 10 segundos antes de verificar novamente

            except requests.exceptions.RequestException as req_err:
                print(f'Erro na requisição ao verificar status da importação: {req_err}')
                break
            except ValueError as val_err:
                print(f'Erro de valor ao analisar JSON: {val_err}')
                break
            except Exception as err:
                print(f'Erro desconhecido ao verificar status da importação: {err}')
                break

except requests.exceptions.HTTPError as http_err:
    print(f'Erro HTTP ao iniciar processo: {http_err}')
except Exception as err:
    print(f'Erro ao iniciar processo: {err}')