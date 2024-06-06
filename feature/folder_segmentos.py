# Main
""" def get_root(token):
    global global_uri
    if global_uri is not None:
        print("Existing global Uri: "+ global_uri)
        return global_uri
    
    else:
        global_uri = verify_folder_root_or_create(token)
    return global_uri 
get_root(token) """

# segments.py

""" def verify_folder_root_or_create(token):
    print('Dentro do verify_folder_root')
    url = "https://server.demo.sas.com/folders/rootFolders"
    folder_name = "segmentos"  # Mantendo o nome correto da pasta conforme fornecido <----- Pasta raiz do segmento

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.sas.collection+json, application/vnd.sas.summary+json, application/json"
    }

    print('Antes do request')
    try:
        response = requests.get(url, headers=headers, verify=False)
        print('Depois do request')
        if response.status_code == 200:
            print('Status code 200')
            folders = response.json()["items"]
            for folder in folders:
                if folder["name"] == folder_name:
                    name = folder["name"]
                    uri = folder['links'][0]['uri']
                    print("URI:", uri)
                    return {"name": name, "uri": uri}
            print("Pasta não encontrada, criando...")

            create_folder_url = "https://server.demo.sas.com/folders/folders"
            create_folder_payload = {
                "name": folder_name,
                "type": "folder"
            }
            create_folder_headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            create_folder_response = requests.post(create_folder_url, json=create_folder_payload, headers=create_folder_headers, verify=False)
            if create_folder_response.status_code == 201:
                folder_data = create_folder_response.json()
                uri = folder_data['links'][0]['uri']
                print("Pasta criada com sucesso. URI:", uri)
                return {"name": folder_name, "uri": uri}
            else:
                print("Falha ao criar a pasta.")
                print("Status code:", create_folder_response.status_code)
                print("Texto da resposta:", create_folder_response.text)
                raise Exception("Falha ao  criar o Folder.")
        else:
            print("Falha ao recuperar as pastas.")
            print("Status code:", response.status_code)
            print("Texto da resposta:", response.text)
            raise Exception("Failed to retrieve folders.")
    except Exception as e:
        print("Erro durante a solicitação:", e)
        raise Exception("Falha ao tentar criar o Folders") """
