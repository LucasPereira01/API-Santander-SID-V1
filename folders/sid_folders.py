from flask import Flask, make_response, jsonify, request
import requests


def create_folder(token):
    body = request.json
    name = body.get("nome")
    description = body.get("descricao")

    url = "https://server.demo.sas.com/folders/folders"

    payload = {
        "name": name,
        "description": description,
        "type": "folder"
        }
      
    autorization = f'Bearer {token}'
    querystring = {"parentFolderUri":"/folders/folders"}
    headers = {
        "Content-Type": "application/json",
        "Authorization":  autorization ,
        "Accept": "application/vnd.sas.content.folder+json, application/json"
    }

    response = requests.post(url, json=payload, headers=headers, verify = False)
    print(response.json())
    if response.status_code ==201:
        r = response.json()
        return r
    else:
        return response.json()