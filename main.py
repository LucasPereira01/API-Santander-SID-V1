from flask import Flask

from buscasas import conf_sas, read_file, armaze_token, get_token, get_domains,get_content,get_curren_contents,create_domains,create_domains_entries,update_entries

app = Flask(__name__)
app.config['DEBUG'] = True

#funcao get token 
armaze_token()
#servidor iniciou?
token = read_file()




@app.route('/api', methods=['GET'])
def get_buscasas():
    #busca = conf_sas(token)   
    #domain = get_domains(token)   
    #contents = get_content(token)   
    #currentContent = get_curren_contents(token)   
    #createDomien = create_domains(token)   
    #createDomiensEntrie = create_domains_entries(token)   
    upDateEntrie = update_entries(token)   
    return upDateEntrie
    #quando expirar vai trazer um erro de api expirada
    # trata o erro e chama essa funcao
    #armaza_token()
    #chamr de novo get_buscasas()





@app.route('/', methods=['GET'])
def get_index():
    return "index"

if __name__ == "__main__": 
    app.run(debug=True,ssl_context='adhoc')
