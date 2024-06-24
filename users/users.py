from flask import Flask, make_response, jsonify, request
import requests
import os

app = Flask(__name__)

url_path_sid = os.getenv("URL_PATH_SID")

def login():
    url = url_path_sid + "/SASLogon/oauth/token"
    body = request.get_json()
    headers = { "Content-Type": "application/x-www-form-urlencoded" }
    data = {
        "grant_type": "password",
        "username": body.get("username"),
        "password": body.get("password")
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

        if response.status_code == 200:
            url2 = url_path_sid + "/identities/users/" + body.get("username")
            res = response.json()

            headers2 = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {res['access_token']}",
                "Accept": "application/json"
            }

            try:
                response2 = requests.get(
                    url=url2,
                    headers=headers2,
                    verify=False
                )

                if response2.status_code == 200:
                    res2 = response2.json()

                    try:
                        url3 = url_path_sid + "/identities/users/" + body.get("username") + "/memberships"
                        query3 = "santander" # "santander"
                        filter3 = f"?filter=and(eq(providerId,'local'),or(contains($primary,name,'{query3}'),contains($primary,id,'{query3}')))&start=0&limit=100&sortBy=name%3Aascending"
                        
                        response3 = requests.get(
                            url=url3 + filter3,
                            headers=headers2,
                            verify=False
                        )

                        if response3.status_code == 200:
                            items = response3.json()['items']
                            ids = []

                            for item in items:
                                ids.append(item['id'])
                            
                            emailAddresses = None
                            # if res2['emailAddresses'] and len(res2['emailAddresses']) > 0:
                            #     emailAddresses = res2['emailAddresses'][0]['value']
                                
                            return {
                                "user_id": res2['id'],
                                "user_email": emailAddresses,
                                "user_name": res2['name'],
                                "token": res['access_token'],
                                "expires_in": res['expires_in'],
                                "santander_memberships_ids": ids
                            }
                            
                        else:
                            return response3.json()
                        
                    except requests.exceptions.RequestException as e3:
                        return jsonify(e3)                    
                else:
                    return response2.json()
                
            except requests.exceptions.RequestException as e2:
                return jsonify(e2)
        else:
            return response.json()
        
    except requests.exceptions.RequestException as e:
        return jsonify(e)