from db import get_db_connection
import requests
from dotenv import load_dotenv
import os 
import time
from lookups.parametros.parametros import get_all_parametro

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso à variável de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
url_path_sid_analytics = os.getenv("URL_PATH_ANALYTICS_SID")
user_name_sid = os.getenv("USER_NAME_SID")
password_sid = os.getenv("PASSWORD_SID")
user_name_sid_analitico = os.getenv("USER_NAME_ANALYTICS_SID")
password_sid_analitico = os.getenv("PASSWORD_ANALYTICS_SID")
schema_db = os.getenv("SCHEMA_DB")


def login(url_sid,user,password):
    url = url_sid + "/SASLogon/oauth/token"
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

def create_segmento_sid(token, url_sid, segmento_id, nome, descricao,sas_test_folder_id):
    if sas_test_folder_id is None:
        conn = get_db_connection()
        cur = conn.cursor()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.sas.content.folder+json, application/json"
        }
        payload = {
            "name": nome,
            "description": descricao,
            "type": "folder"
        }

        try:
            
            url = f"{url_sid}/folders/folders"
            response = requests.post(url, json=payload, headers=headers, verify=False)
            if response.status_code != 201:
                error_type = response.json()
                raise Exception("Falha ao criar o segmento no SAS Intelligence Design ", error_type["message"])
            
            response_data = response.json()

            sas_folder_id = response_data.get("id")
            if 'links' in response_data and len(response_data['links']) > 0:
                sas_parent_uri = response_data['links'][0]['uri']
            else:
                sas_parent_uri = None
            
            if not sas_folder_id or not sas_parent_uri:
                raise Exception("'parentFolderUri' or 'id' not found in response data")
            
            cur.execute(
                f""" 
                UPDATE {schema_db}.segmento 
                SET sas_test_folder_id = %s, sas_test_parent_uri = %s 
                WHERE id = %s
                """,
                (sas_folder_id, sas_parent_uri ,segmento_id) 
            )
            # Commit the transaction
            conn.commit()
            print("Registro de segmento atualizado com sucesso!")
            print({"message": "Segmento Criado com Sucesso", "id": segmento_id}, 201)
        except Exception as e:
            conn.rollback()
            print(str(e))
            print({"error": str(e)}, 500)
        finally:
            cur.close()
            conn.close()

    else: print('Segmento ja existe')

def criar_cluster_sid(token, url_sid, nome,descricao,segmento_id,cluster_id,sas_test_folder_id):
    if sas_test_folder_id is None:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(f"SELECT * FROM  {schema_db}.segmento WHERE id = %s",(segmento_id,))
        segmento = cur.fetchone()
        print("segmento",segmento)
        if not segmento:
            print("Segmento não encontrado")
            print({"error":"Segmento não encontrado"},400)
            return

        sas_parent_uri_seg = segmento['sas_test_parent_uri']
        print("sas_parent_uri_seg",sas_parent_uri_seg)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.sas.content.folder+json, application/json"
        }

        payload = {
            "name": nome,
            "description": descricao,
            "type": "folder"
        }
        try:
            url = f"{url_sid}/folders/folders"

            path_segmentos = {"parentFolderUri": sas_parent_uri_seg}  # Define o path_segmentos se a pasta raiz foi encontrada

            # TODO verificar no sid se ja existe o cluster
            
            response = requests.post(url, json=payload, headers=headers, params=path_segmentos, verify=False)
            if response.status_code != 201:
                error_type = response.json()
                raise Exception("Falha ao criar o Cluster no SAS Intelligence Design ", error_type["message"])
        
            response.raise_for_status()

            response_data = response.json()
            
            # Obtém os dados relevantes da resposta
            sas_folder_id = response_data.get("id")
            sas_parent_uri = response_data.get("links", [{}])[0].get("uri")

            # Verifica se os dados necessários foram obtidos
            if not sas_folder_id or not sas_parent_uri:
                print({"error": "'parentFolderUri' or 'id' not found in response data"}, 500)
                return
            
            # Insere os dados do cluster no banco de dados
            cur.execute(
                        f"""
                        UPDATE {schema_db}.clusters 
                        SET sas_test_parent_uri = %s, sas_test_folder_id = %s
                        WHERE id = %s
                        """,
                        (sas_parent_uri, sas_folder_id, cluster_id)
                    )
            conn.commit()
            print({"message": "Cluster Criado com Sucesso", "id": cluster_id}, 201)
        except Exception as e:
            conn.rollback()
            print(str(e))
            print({"error": str(e)}, 500)
        finally:
            cur.close()
            conn.close()
    else: print('Cluster ja Existe')
    
def criar_politica_sid(token, url_sid, nome,descricao,cluster_id,politica_id,sas_test_folder_id):
    if  sas_test_folder_id is None:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(f"SELECT * FROM  {schema_db}.clusters WHERE id = %s",(cluster_id,))
        cluster = cur.fetchone()
        print("cluster",cluster)
        if not cluster:
            print({"error":"Cluster não encontrado"})
            return
        sas_parent_uri_cluster = cluster['sas_test_parent_uri']

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.sas.content.folder+json, application/json"
        }
        payload = {
            "name": nome,
            "description": descricao,
            "type": "folder"
        }
        try:
            url = f"{url_sid}/folders/folders"

            path_cluster = {"parentFolderUri": sas_parent_uri_cluster}  # Define o path_cluster se a pasta raiz foi encontrada

            # TODO verificar se ja existe a politica no sid
            
            # Realiza a solicitação POST
            response = requests.post(url, json=payload, headers=headers, params=path_cluster, verify=False)

            if response.status_code != 201:
                error_type = response.json()
                raise Exception("Falha ao criar a Politica no SAS Intelligence Design ", error_type["message"])
            
            # Verifica se a solicitação foi bem-sucedida
            response.raise_for_status()

            # Processa a resposta JSON
            response_data = response.json()
            
            # Obtém os dados relevantes da resposta
            sas_folder_id = response_data.get("id")
            sas_parent_uri = response_data.get("links", [{}])[0].get("uri")

            # Verifica se os dados necessários foram obtidos
            if not sas_folder_id or not sas_parent_uri:
                print({"error": "'parentFolderUri' or 'id' not found in response data"}, 500)
                return
            
            # Insere os dados do cluster no banco de dados
            cur.execute(
            f"""
            UPDATE {schema_db}.politica 
            SET sas_test_parent_uri = %s, sas_test_folder_id = %s
            WHERE id = %s
            """,
            (sas_parent_uri, sas_folder_id, politica_id)
            )
            # Commit the transaction
            conn.commit()
            print({"message": "Politica Criada com Sucesso", "id": politica_id}, 201)
        except Exception as e:
            conn.rollback()
            print(str(e))
            print({"error": str(e)}, 500)
        finally:
            if conn is not None:
                conn.close()
    else:
        print("Politica ja existe")  

def check_exites_domains(parametro_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT sas_domain_id FROM  {schema_db}.parametro WHERE id = %s", (parametro_id,))
    sas_domain_id = cur.fetchone()

    if sas_domain_id[0] is not None:
        return sas_domain_id[0]
    else: 
        return None

def create_domains_and_entries_sid(token, url_sid, name, descricao, id_politica, parametro_id, entries=None):
    sas_domain_id = check_exites_domains(parametro_id)
    sas_user_id = 'teste'
    
    if sas_domain_id is None:
        status_code = '004'
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # Verificar se o parâmetro já possui um domínio SAS atribuído
            cur.execute(f"SELECT * FROM {schema_db}.parametro WHERE id = %s", (parametro_id,))
            parametro = cur.fetchone()

            if not parametro:
                print("Parâmetro não encontrado")
                return {"error": "Parâmetro não encontrado"}, 404

            if parametro['sas_domain_id']:
                print("O parâmetro já possui um domínio SAS atribuído:", parametro['sas_domain_id'])
                return

            # Verificar se já existe um domínio SAS com o mesmo nome na política associada
            cur.execute(f"SELECT * FROM {schema_db}.politica WHERE id = %s", (id_politica,))
            politica = cur.fetchone()

            if not politica:
                print("Política não encontrada")
                return {"error": "Política não encontrada"}, 404

            sas_parent_folder_uri_cluster = politica['sas_test_parent_uri']
            url = f"{url_sid}/referenceData/domains?parentFolderUri={sas_parent_folder_uri_cluster}"

            payload = {
                "name": name,
                "description": descricao,
                "domainType": "lookup"
            }

            authorization = f'Bearer {token}'
            headers = {
                "Content-Type": "application/vnd.sas.data.reference.domain+json",
                "Authorization": authorization,
                "Accept": "application/vnd.sas.data.reference.domain+json, application/vnd.sas.data.reference.value.list+json, application/json, application/vnd.sas.error+json"
            }

            # Criar o domínio SAS
            response = requests.post(url, headers=headers, json=payload, verify=False)
            response.raise_for_status()  # Lança uma exceção se o status da resposta não for 2xx

            domain_info = response.json()

            # Atualizar o parâmetro com o ID do domínio SAS criado e status_code
            cur.execute(
                f"""
                UPDATE {schema_db}.parametro 
                SET sas_domain_id = %s, status_code = %s 
                WHERE id = %s
                """,
                (domain_info["id"], status_code, parametro_id)
            )
            conn.commit()

                            # Registrar evento de criação de parâmetro
            cur.execute(
                    f"""
                    INSERT INTO {schema_db}.evento (status_code, sas_user_id, parametro_id)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (status_code, sas_user_id, parametro_id)
            )
            conn.commit()

            print("Registro de Parâmetro atualizado com sucesso!")

            # Buscar os dados associados ao parâmetro no banco de dados
            cur.execute(f"SELECT sas_key, sas_value FROM {schema_db}.dado WHERE parametro_id = %s ", (parametro_id,))
            valores_dados = cur.fetchall()

            if valores_dados:
                # Preparar as entradas para o domínio
                payload_entries = []
                for sas_key, sas_value in valores_dados:
                    payload_entries.append({
                        "key": sas_key,
                        "value": sas_value
                    })

                # Enviar entradas para o domínio SAS
                url_entries = f"{url_sid}/referenceData/domains/{domain_info['id']}/contents"

                payload = {
                    "label": name,
                    "status": "developing",
                    "entries": payload_entries
                }

                headers = {
                    "Content-Type": "application/vnd.sas.data.reference.domain.content.full+json",
                    "Authorization": authorization,
                    "Accept": "application/vnd.sas.data.reference.domain.content.full+json, application/vnd.sas.data.reference.value.list.content.full+json, application/json, application/vnd.sas.error+json"
                }

                response_entries = requests.post(url_entries, headers=headers, json=payload, verify=False)
                response_entries.raise_for_status()  # Lança uma exceção se o status da resposta não for 2xx

                entries_info = response_entries.json()

                # Atualizar o parâmetro com o ID da entrada criada e status_code
                cur.execute(
                    f"""
                    UPDATE {schema_db}.parametro 
                    SET sas_content_id = %s, status_code = %s
                    WHERE id = %s
                    """,
                    (entries_info["id"], status_code, parametro_id)
                )
                conn.commit()


                
                print("Registro de Parâmetro atualizado com sucesso!")
                print({
                    "domain_created": domain_info,
                    "entries_created": entries_info
                })

            else:
                print("Sem entries fornecidas")
                print({"domain_created": domain_info})

        except Exception as e:
            conn.rollback()
            print(str(e))
            return {"error": str(e)}, 500

        finally:
            cur.close()
            conn.close()

    else:
        print('Parâmetro já existe')


def type_variable(type): #string, decimal,integer,date,datetime,boolean
    match type:
        case 'TEXTO' :
            return 'string'
        case 'LISTA' :
            return 'string'
        case 'DECIMAL' :
            return 'decimal'
        case 'NUMERICO':
            return 'integer'

def create_variavel_global(token, url_sid, nome, id_politica, parametro_id):
    sas_user_id = 'lucas'
    sas_domain_id = check_exites_domains(parametro_id)
    if sas_domain_id is None :
        conn = get_db_connection()  
        cur = conn.cursor()
        try:
                # Verificar se o parâmetro já possui um domínio SAS atribuído
                cur.execute(f"SELECT * FROM  {schema_db}.parametro WHERE id = %s", (parametro_id,))
                parametro = cur.fetchone()

                if not parametro:
                    print("Parâmetro não encontrado")
                    return {"error": "Parâmetro não encontrado"}, 404

                if parametro['sas_domain_id']:
                    print("O parâmetro já possui um domínio SAS atribuído:", parametro['sas_domain_id'])
                    return

                # Verificar se já existe um domínio SAS com o mesmo nome na política associada
                cur.execute(f"SELECT * FROM  {schema_db}.politica WHERE id = %s", (id_politica,))
                politica = cur.fetchone()

                if not politica:
                    print("Política não encontrada")
                    print({"error": "Política não encontrada"}, 400)
                    return

            
                cur.execute(f"SELECT sas_value, sas_type FROM  {schema_db}.dado WHERE parametro_id = %s",(parametro_id,))
                value =  cur.fetchall()

                defaultValue = value[0]['sas_value']
                dataType = type_variable(value[0]['sas_type'])

                url = f"{url_sid}/referenceData/globalVariables"
                
                payload = {
                    "name": nome,
                    "dataType": dataType,
                    "defaultValue": defaultValue,
                }

                headers = {
                    "Content-Type": "application/vnd.sas.data.reference.global.variable+json",
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.sas.data.reference.global.variable+json, application/json, application/vnd.sas.error+json"
                }

                response = requests.post(url, json=payload, headers=headers, verify=False)

                domain_info = response.json()

                relevant_info = {
                    "name": domain_info["name"],
                    "id": domain_info["id"],
                }
                status_code = '004'
            
                cur.execute(
                f"""
                    UPDATE {schema_db}.parametro 
                    SET sas_domain_id = %s, status_code = %s
                    WHERE id = %s
                    """,
                    (relevant_info["id"], status_code, parametro_id)
                )
                conn.commit()

                cur.execute(
                    f"""
                        INSERT INTO {schema_db}.evento (status_code, sas_user_id, parametro_id)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, 
                    (status_code, sas_user_id, parametro_id))

                conn.commit()
                print("Registro de Parâmetro atualizado com sucesso!",relevant_info["id"])

        except Exception as e:
                conn.rollback()
                print(str(e))
                print({"error": str(e)}, 500)

        finally:
                cur.close()
                conn.close()
    print('Varaivel Global ja existe') 



def verificar_e_criar(token, url_sid, parametros_005):
    if parametros_005:
        for parametro in parametros_005:
            politica = parametro['politica']
            cluster = politica['cluster']
            segmento = cluster['segmento']
            dado = parametro['dado']

            try:
                # Cria o segmento se ainda não existir
                create_segmento_sid(token, url_sid, segmento['id'], segmento['nome'], segmento['descricao'], segmento['sas_test_folder_id'])

                # Cria o cluster se ainda não existir
                criar_cluster_sid(token, url_sid, cluster['nome'], cluster['descricao'], cluster['segmento']['id'], cluster['id'], cluster['sas_test_folder_id'])

                # Cria a política se ainda não existir
                criar_politica_sid(token, url_sid, politica['nome'], politica['descricao'], politica['cluster']['id'], politica['id'], politica['sas_test_folder_id'])

                # Cria o parâmetro se ainda não existir
                if parametro['modo'] == 'CHAVE':
                    create_domains_and_entries_sid(token, url_sid, parametro['nome'], parametro['descricao'], politica['id'], parametro['id'], dado)

                if parametro['modo'] == 'GLOBAL':
                    create_variavel_global(token, url_sid, parametro['nome'],  politica['id'], parametro['id'])
            except Exception as e:
                print(f"Erro ao criar parâmetro: {e}")
                # Você pode optar por lançar novamente a exceção ou lidar com ela aqui

    else:
        print("Nenhum parâmetro com status 005 encontrado.")


# Função para executar a verificação a cada 5 minutos
def verificar_periodicamente():
    while True:
        try:
            # Obter os parâmetros com status 005
            parametros = get_all_parametro()
            parametros_005 = [parametro for parametro in parametros if parametro['status_code'] == '005']

            if parametros_005:
                url_sid = url_path_sid_analytics
            else:
                url_sid = url_path_sid
            # Obter o token SAS
            token = login(url_sid,user_name_sid_analitico,password_sid_analitico)


            # Verificar e criar os parâmetros
            verificar_e_criar(token, url_sid, parametros_005)
        except Exception as e:
            print(f"Erro ao executar verificação: {e}")
        
        time.sleep(300)  # Aguarda 5 minutos


