
from flask import Flask, make_response, jsonify
import schedule
import threading
import time
from flask_cors import CORS

from lookups.buscasas import conf_sas, read_file, get_token_and_write, get_domains, get_content, get_current_contents, create_domains, create_domains_entries, update_entries,create_domains_and_entries
from folders.segments import create_segmento,edit_segmento,list_segmentos,list_segmentos_id
from folders.clusters import criar_cluster,busca_all_cluster,edit_cluster,buscar_cluster_id
from folders.politcs import criar_politica,edit_politica,busca_all_politica,list_politica_id

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


@app.route('/api/v1/domains/<string:id_politica>', methods=['POST'])
def create_domains_entries_route(id_politica):
    return create_domains_and_entries(token,id_politica)


@app.route('/api/v1/update_entries', methods=['PATCH'])
def update_entries_route():
    return update_entries(token)


### Folders
@app.route('/api/v1/front/segmentos', methods=['POST'])
def create_segments():
    return create_segmento(token, global_uri)


@app.route('/api/v1/front/segmentos/<string:segmento_id>', methods=['PUT'])
def edit_segmentos(segmento_id):
    return edit_segmento(segmento_id)


@app.route('/api/v1/front/segmentos', methods=['GET'])
def list_all_segmentos():
    return list_segmentos()

@app.route('/api/v1/front/segmentos/<string:segmento_id>', methods=['GET'])
def list_id_segmentos(segmento_id):
    return list_segmentos_id(segmento_id)


# Clusters
@app.route('/api/v1/front/clusters/<string:segmento_id>', methods=['POST'])
def create_cluster(segmento_id):
    return criar_cluster(token,segmento_id)


@app.route('/api/v1/front/clusters', methods=['GET'])
def get_all_cluster():
    return busca_all_cluster()

@app.route('/api/v1/front/clusters/<string:cluster_id>', methods=['GET'])
def list_id_cluster(cluster_id):
    return buscar_cluster_id(cluster_id)
    


@app.route('/api/v1/front/clusters/<string:cluster_id>', methods=['PUT'])
def alter_cluster(cluster_id):
    return edit_cluster(cluster_id)
    
# Politicas
@app.route('/api/v1/front/politicas/<string:cluster_id>', methods=['POST'])
def create_politica(cluster_id):
    return criar_politica(token,cluster_id)

@app.route('/api/v1/front/politicas/<string:politica_id>', methods=['GET'])
def lit_id_politica(politica_id):
    return list_politica_id(politica_id)

@app.route('/api/v1/front/politicas/<string:politica_id>', methods=['PUT'])
def alter_politica(politica_id):
    return edit_politica(politica_id)


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