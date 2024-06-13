from db import get_db_connection
import requests
from dotenv import load_dotenv
import os 
import time
import datetime
from lookups.parametros.parametros import get_all_parametro


# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Acesso à variável de ambiente
url_path_sid = os.getenv("URL_PATH_SID")
url_path_sid_analytics = os.getenv("URL_PATH_ANALYTICS_SID")

def create_segmento_sid(token, segmento_id, nome, descricao):
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
        url = f"{url_path_sid}/folders/folders"
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
            """
            UPDATE segmento 
            SET sas_parent_uri = %s, sas_folder_id = %s
            WHERE id = %s
            """,
            (sas_parent_uri, sas_folder_id,segmento_id)
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

def criar_cluster_sid(token,nome,descricao,segmento_id,cluster_id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM segmento WHERE id = %s",(segmento_id,))
    segmento = cur.fetchone()
    if not segmento:
        print("Segmento não encontrado")
        print({"error":"Segmento não encontrado"},400)
        return

    sas_parent_uri_seg = segmento[5]
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
        url = f"{url_path_sid}/folders/folders"

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
                    """
                    UPDATE clusters 
                    SET sas_parent_uri = %s, sas_folder_id = %s
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

def criar_politica_sid(token,nome,descricao,cluster_id,politica_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM clusters WHERE id = %s",(cluster_id,))
    cluster = cur.fetchone()
    if not cluster:
        print({"error":"Cluster não encontrado"})
        return
    sas_parent_uri_cluster = cluster[5]

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
        url = f"{url_path_sid}/folders/folders"

        path_cluster = {"parentFolderUri": sas_parent_uri_cluster}  # Define o path_cluster se a pasta raiz foi encontrada

        # TODO verificar se ja exite a politica no sid
        
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
        """
        UPDATE politica 
        SET sas_parent_uri = %s, sas_folder_id = %s
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

def create_domains_and_entries_sid(token, name, descricao, id_politica, parametro_id, entries=None):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT * FROM politica WHERE id = %s", (id_politica,))
        politica = cur.fetchone()
        if not politica:
            print("Política não encontrada")
            print(({"error": "Política não encontrada"}), 400)
            return

        sas_parent_folder_uri_cluster = politica[5]

        url = f"{url_path_sid}/referenceData/domains?parentFolderUri={sas_parent_folder_uri_cluster}"

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
        # TODO  Verificar se ja exite a lookup no sid
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

            # Verifica se 'entries' está presente em parametro e define entries
            if entries:
                url_entries = f"https://server.demo.sas.com/referenceData/domains/{domain_info['id']}/contents"

                payload = {
                    "label": name,
                    "status": "developing",
                    "entries": entries
                }

                headers = {
                    "Content-Type": "application/vnd.sas.data.reference.domain.content.full+json",
                    "Authorization": authorization,
                    "Accept": "application/vnd.sas.data.reference.domain.content.full+json, application/vnd.sas.data.reference.value.list.content.full+json, application/json, application/vnd.sas.error+json"
                }

                response_entries = requests.post(url_entries, headers=headers, json=payload, verify=False)
                if response_entries.status_code == 201:
                    entries_info = response_entries.json()

                    cur.execute(
                        """
                        UPDATE parametro 
                        SET sas_domain_id = %s
                        WHERE id = %s
                        """,
                        (relevant_info["id"], parametro_id)
                    )
                    # Commit the transaction
                    conn.commit()
                    print("Registro de cluster atualizado com sucesso!")
                    print({
                        "domain_created": relevant_info,
                        "entries_created": entries_info
                    }, 201)

                else:
                    print({"error": response_entries.text}, response_entries.status_code)

            else:
                print({"domain_created": relevant_info}, 201)

        else:
            print({"error": "Falha ao criar domínio", "json": response.json()}, response.status_code)

    except Exception as e:
        conn.rollback()
        print(str(e))
        print(({"error": str(e)}), 500)

    finally:
        cur.close()
        conn.close()


agora = datetime.datetime.now()
data_hora_atual = agora.strftime("%Y-%m-%d %H:%M:%S")


def verificar_e_criar(token):
    parametros = get_all_parametro()
    parametros_005 = [parametro for parametro in parametros if parametro['status_code'] == '005']
     
    total_sucesso = 0
    total_falha = 0
    
    if parametros:
        for parametro in parametros_005:
            print(parametro)
            segmento = parametro['politica']['cluster']['segmento']
            cluster = parametro['politica']['cluster']
            politica = parametro['politica']


            try:
                # Cria o segmento
                create_segmento_sid(token, segmento['id'], segmento['nome'], segmento['descricao'])
                print("Segmento: ",data_hora_atual)

                # Cria o cluster
                criar_cluster_sid(token, cluster['nome'], cluster['descricao'], cluster['segmento_id'], cluster['id'])
                print("Cluster: ",data_hora_atual)

                # Cria a política
                criar_politica_sid(token, politica['nome'], politica['descricao'], politica['cluster_id'], politica['id'])
                print("Politica: ",data_hora_atual)

                # Verifica se 'entries' está presente em parametro e define entries
                entries = parametro.get('entries')

                # Cria o parâmetro
                create_domains_and_entries_sid(token, parametro['nome'], parametro['descricao'], politica['id'], parametro['id'], entries)
                print("Parametros: ",data_hora_atual)

                total_sucesso += 1
            except Exception as e:
                total_falha += 1
                print(f"Erro ao criar parâmetro: {e}")
                print("Fim: ",data_hora_atual)

    print(f"Total de parâmetros criados com sucesso: {total_sucesso}")
    print(f"Total de parâmetros com falha: {total_falha}")

# Função para executar a verificação a cada 5 minutos
def verificar_periodicamente(token):
    while True:
        verificar_e_criar(token)
        time.sleep(300)  # Aguarda 5 minutos
