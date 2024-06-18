from flask import Flask, make_response, jsonify
import schedule
import threading
import time
from flask_cors import CORS

from lookups.buscasas import *
from lookups.parametros.parametros import *
from folders.segments import *
from folders.clusters import *
from folders.politcs import *
from folders.create_lokup_sid import *

from users.users import *

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
app = Flask(__name__, template_folder="./templates")
CORS(app)


# Função para execução do loop de verificação em uma thread
def run_verification():
    while True:
        print("Executando verificação a cada 5 minutos...")
        verificar_periodicamente()
        time.sleep(300)  # Espera 5 minutos


# Iniciar as threads para execução do agendamento e da verificação
def run_threads():
    verification_thread = threading.Thread(target=run_verification)
    verification_thread.start()

run_threads()

# Definimos as rotas da API
@app.route('/api/v1/', methods=['GET'])
def get_buscasas():
    return conf_sas(token)

@app.route('/api/v1/front/login', methods=['POST'])
def get_login():
    return login()

## Parametros no banco
@app.route('/api/v1/front/parametros/datatable', methods=['POST'])
def lista_data_table():
    return lista_parametros_data_table()

@app.route('/api/v1/front/parametros', methods=['POST'])
def create_parametro_base():
    return create_parametro()

@app.route('/api/v1/front/parametros', methods=['GET'])
def busca_all_parametro_base():
    return get_all_parametro()

@app.route('/api/v1/front/parametros/<string:parametro_id>', methods=['GET'])
def busca_parametro_id_base(parametro_id):
    return get_parametro_by_id(parametro_id)

@app.route('/api/v1/front/parametros/<string:parametro_id>', methods=['PUT'])
def alter_parametro_id_base(parametro_id):
    return update_parametro(parametro_id)

@app.route('/api/v1/front/parametros/<string:parametro_id>', methods=['DELETE'])
def del_parametro_id_base(parametro_id):
    return delete_parametro(parametro_id)

@app.route('/api/v1/front/parametros/<string:parametro_id>/status', methods=['POST'])
def alter__status_parametro_base(parametro_id):
    return atualizar_status(parametro_id)


## Variavel no banco
@app.route('/api/v1/front/parametros/<string:id_parametros>/variaveis', methods=['POST'])
def create_variaveis_base(id_parametros):
    return create_variaveis(id_parametros)

@app.route('/api/v1/front/parametros/<string:id_parametros>/dados', methods=['POST'])
def create_dados_base(id_parametros):
    return create_dados(id_parametros)

####################### Folders ########################################################
""" @app.route('/api/v1/front/segmentos', methods=['POST'])
def create_segments():
    return create_segmento(token, global_uri) """

@app.route('/api/v1/front/segmentos', methods=['POST'])
def create_segments_data_base():
    return create_segmento_data_base()


@app.route('/api/v1/front/segmentos/<string:segmento_id>', methods=['PUT'])
def edit_segmentos(segmento_id):
    return edit_segmento(segmento_id)


@app.route('/api/v1/front/segmentos', methods=['GET'])
def list_all_segmentos():
    return list_segmentos()

@app.route('/api/v1/front/segmentos/<string:segmento_id>', methods=['GET'])
def list_id_segmentos(segmento_id):
    return list_segmentos_id(segmento_id)

@app.route('/api/v1/front/segmentos/<string:segmento_id>', methods=['DELETE'])
def del_id_segmentos(segmento_id):
    return delete_segmento(segmento_id)

# Clusters 
""" @app.route('/api/v1/front/clusters', methods=['POST'])
def create_cluster():
    return criar_cluster(token) """

@app.route('/api/v1/front/clusters', methods=['POST'])
def create_cluster_data_base():
    return criar_cluster_data_base()

@app.route('/api/v1/front/clusters', methods=['GET'])
def get_all_cluster():
    return busca_all_cluster()

@app.route('/api/v1/front/clusters/<string:cluster_id>', methods=['GET'])
def list_id_cluster(cluster_id):
    return buscar_cluster_id(cluster_id)
    
@app.route('/api/v1/front/clusters/<string:cluster_id>', methods=['PUT'])
def alter_cluster(cluster_id):
    return edit_cluster(cluster_id)
    
@app.route('/api/v1/front/clusters/<string:cluster_id>', methods=['DELETE'])
def del_cluster(cluster_id):
    return delete_cluster(cluster_id)
    
# Politicas
""" @app.route('/api/v1/front/politicas', methods=['POST'])
def create_politica():
    return criar_politica(token) """

@app.route('/api/v1/front/politicas', methods=['POST'])
def create_politica_data_base():
    return criar_politica_data_base()

@app.route('/api/v1/front/politicas/<string:politica_id>', methods=['GET'])
def lit_id_politica(politica_id):
    return list_politica_id(politica_id)

@app.route('/api/v1/front/politicas/<string:politica_id>', methods=['PUT'])
def alter_politica(politica_id):
    return edit_politica(politica_id)

@app.route('/api/v1/front/politicas/<string:politica_id>', methods=['DELETE'])
def del_politica(politica_id):
    return delete_politica(politica_id)


@app.route('/api/v1/front/politicas', methods=['GET'])
def get_all_politica():
    return busca_all_politica()


# Teste Api
@app.route('/', methods=['GET'])
def get_index():
    return make_response(jsonify({"sucesso":"Bem vindo"}))

if __name__ == "__main__":
    app.run(debug=False, ssl_context='adhoc',port=8080)

# Função para execução do loop de verificação em uma thread
def run_verification():
    while True:
        print("Executando verificação a cada 5 minutos...")
        # Coloque sua lógica de verificação aqui
        time.sleep(300)  # Espera 5 minutos

