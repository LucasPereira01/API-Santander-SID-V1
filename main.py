from flask import Flask, make_response, jsonify
import schedule
import threading
import time
from buscasas import conf_sas, read_file, get_token_and_write, get_domains, get_content, get_curren_contents, create_domains, create_domains_entries, update_entries

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

# Iniciamos o aplicativo Flask
app = Flask(__name__)
app.config['DEBUG'] = True

# Verifica se existe um token armazenado
token = read_file()
if not token:
    get_token_and_write()  # Se não existir, obtém um novo token e armazena

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
    return get_curren_contents(token)

@app.route('/api/v1/create_domains', methods=['POST'])
def create_domains_route():
    return create_domains(token)

@app.route('/api/v1/create_domains_entries', methods=['POST'])
def create_domains_entries_route():
    return create_domains_entries(token)

@app.route('/api/v1/update_entries', methods=['POST'])
def update_entries_route():
    return update_entries(token)

@app.route('/', methods=['GET'])
def get_index():
    return make_response(jsonify({"sucesso":"Bem vindo"}))

# Executamos o aplicativo Flask
if __name__ == "__main__":
    app.run(debug=True, ssl_context='adhoc')
    #app.run(app.run(port=8080), debug=True, ssl_context='adhoc')