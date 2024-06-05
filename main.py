
from flask import Flask, make_response, jsonify
import schedule
import threading
import time
from flask_cors import CORS

from lookups.buscasas import conf_sas, read_file, get_token_and_write, get_domains, get_content, get_current_contents, create_domains, create_domains_entries, update_entries,create_domains_and_entries
from folders.segments import create_segmento,edit_segmento,list_segmentos,verify_folder_root_or_create
from folders.clusters import criar_cluster,busca_all_cluster,edit_cluster
from folders.politcs import criar_politica,edit_politica,busca_all_politica

global_uri = None

# Programamos a atualização do token a cada 55 minutos
schedule.every(55).minutes.do(get_token_and_write)


# Função para executar o agendamento em uma thread separada
def schedule_thread():
    while True:
        schedule.run_pending()
        time.sleep(1)


# Iniciamos a thread para execução do agendamento
schedule_thread = threading.Thread(target=schedule_thread)
schedule_thread.start()


# Verifica se existe um token armazenado
token = read_file()
if not token:
    get_token_and_write()  # Se não existir, obtém um novo token e armazena


def get_root(token):
    global global_uri
    if global_uri is not None:
        print("Existing global Uri: "+ global_uri)
        return global_uri
    
    else:
        global_uri = verify_folder_root_or_create(token)
    return global_uri 
get_root(token)


# Iniciamos o aplicativo Flask
app = Flask(__name__,template_folder="./templates")
app.config['DEBUG'] = True
CORS(app)


# Definimos as rotas da API
@app.route('/api/v1/', methods=['GET'])
def get_buscasas():
    return conf_sas(token)


@app.route('/api/v1/domains', methods=['GET'])
def get_domains_route():
    return get_domains(token)


@app.route('/api/v1/contents', methods=['GET'])
def get_contents():
    return get_content(token)


@app.route('/api/v1/current_contents', methods=['GET'])
def get_current_contents_route():
    return get_current_contents(token)


@app.route('/api/v1/create_domains', methods=['POST'])
def create_domains_route():
    return create_domains(token)


""" @app.route('/api/v1/create_domains_entries', methods=['POST'])
def create_domains_entries_route():
    return create_domains_entries(token) """


@app.route('/api/v1/create_domains_entries', methods=['POST'])
def create_domains_entries_route():
    return create_domains_and_entries(token)


@app.route('/api/v1/update_entries', methods=['PATCH'])
def update_entries_route():
    return update_entries(token)


### Folders
@app.route('/api/v1/front/segmentos', methods=['POST'])
def create_segments():
    return create_segmento(token, global_uri)


@app.route('/api/v1/front/segmentos', methods=['PUT'])
def edit_segmentos():
    return edit_segmento()


@app.route('/api/v1/front/segmentos', methods=['GET'])
def list_all_segmentos():
    return list_segmentos()


# Clusters
@app.route('/api/v1/front/clusters', methods=['POST'])
def create_cluster():
    return criar_cluster(token)


@app.route('/api/v1/front/clusters', methods=['GET'])
def get_all_cluster():
    return busca_all_cluster()


@app.route('/api/v1/front/clusters', methods=['PUT'])
def alter_cluster():
    return edit_cluster()


# Politicas
@app.route('/api/v1/front/politicas', methods=['POST'])
def create_politica():
    return criar_politica(token)


@app.route('/api/v1/front/politicas', methods=['PUT'])
def alter_politica():
    return edit_politica()


@app.route('/api/v1/front/politicas', methods=['GET'])
def get_all_politica():
    return busca_all_politica()


# Teste Api
@app.route('/', methods=['GET'])
def get_index():
    return make_response(jsonify({"sucesso":"Bem vindo"}))


if __name__ == "__main__":
    #app.run(debug=True, ssl_context='adhoc')
    app.run(app.run(port=8080), debug=True, ssl_context='adhoc')