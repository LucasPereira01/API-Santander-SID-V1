from flask import Flask, make_response, request, jsonify
import uuid
from datetime import datetime
from db import get_db_connection
import requests
import certifi



app = Flask(__name__)



def get_global_variables(token):
   
    try:
        url = "https://server.demo.sas.com/referenceData/globalVariables"

        headers = {
        "Accept": "application/vnd.sas.collection+json, application/json",
        "Accept-Item": "application/vnd.sas.data.reference.global.variable+json",
        "Authorization": f"Bearer {token}",
        }

        response = requests.get(url, headers=headers, verify=False)
        if response.status_code == 200:
         etag = response.headers.get('ETag')
         r = response.json()
        return {"resposta":r, "etag": etag}
    except (Exception) as error:
        print(f"Erro ao buscar variavel global: {error}")
        return jsonify({"error": "Failed to retrieve variables"}), 500


def create_global_variables(token):
    url = "https://server.demo.sas.com/referenceData/globalVariables"

    payload = {
        "name": "Global0100849",
        "dataType": "string",
        "defaultValue": "Value0100849",
    }

    headers = {
        "Content-Type": "application/vnd.sas.data.reference.global.variable+json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.sas.data.reference.global.variable+json, application/json, application/vnd.sas.error+json"
    }

    response = requests.post(url, json=payload, headers=headers, verify=False)
    
    try:
        response_json = response.json()
    except ValueError:
        response_json = None

    if response.status_code == 201:
        return response_json if response_json is not None else {
            "error": "Response not in JSON format",
            "content": response.content.decode('utf-8')
        }
    else:
        return {
            "error": f"Request failed with status code: {response.status_code}",
            "content": response.content.decode('utf-8')
        }


def get_global_variables_globalVariableId(token):
    try:
        #global_variables = get_global_variables(token)    
        variableId = 'a3880f25-8a7c-4e1b-b045-bfffc097d45c'

       
        url = f"https://server.demo.sas.com/referenceData/globalVariables/{variableId}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.sas.data.reference.global.variable+json, application/json, application/vnd.sas.summary+json, application/vnd.sas.error+json"
        }

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code == 200:
            etag = response.headers.get('ETag')
            r = response.json()
        return {"resposta":r, "etag": etag}
    except (Exception) as error:
        print(f"Erro ao buscar variavel global: {error}")
        return jsonify({"error": "Failed to retrieve variables"}), 500


def put_global_variables(token):
       
    try:
        global_variables = get_global_variables_globalVariableId(token)
        globalVariableId = global_variables["resposta"]["id"]
        print(globalVariableId)
        etag = global_variables["etag"]
    
        url = f"https://server.demo.sas.com/referenceData/globalVariables/{globalVariableId}"

        payload = {
            "name": "Globalz1158",  # nao pode mudar o nome da variavel global
            "dataType": "string",
            "defaultValue": "Value1521",
        }

        headers = {
            "If-Match": etag,
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.sas.data.reference.global.variable+json, application/json, application/vnd.sas.error+json"
        }

        response = requests.put(url, json=payload, headers=headers, verify=False)
        
        try:
            response_json = response.json()
        except ValueError:
            response_json = None

        if response.status_code == 200:
            print(response)
            return response_json if response_json is not None else {
                "error": "Response not in JSON format",
                "content": response.content.decode('utf-8')
            }
        else:
            return {
                "error": f"Request failed with status code: {response.status_code}",
                "content": response.content.decode('utf-8')
            }

    except requests.exceptions.RequestException as e:
        # Handle any request exceptions
        return {"error": str(e)}
    

def delete_global_variables_globalVariableId(token):

    url = f"https://server.demo.sas.com/referenceData/globalVariables/a3880f25-8a7c-4e1b-b045-bfffc097d45c"

    headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    response = requests.delete(url, headers=headers, verify=False)

    if response.status_code == 204:
            response_data = {
                "message": "Variavel global deletada com sucesso",
                "status_code": response.status_code
            }
    else:
            try:
                response_data = response.json()
            except requests.exceptions.JSONDecodeError:
                response_data = {
                    "error": "JSON response invalid",
                    "status_code": response.status_code,
                    "content": response.text
                }
    return response_data
