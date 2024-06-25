from flask import Flask, make_response, request, jsonify

def funcoes(sas_user_groups, permitted_groups):
    if not permitted_groups:
        return jsonify({'error': "Lista de permissões não encontrada no arquivo .env"}), 500

    # Verificar se o sas_user_groups está na lista de permitted_groups
    if sas_user_groups not in permitted_groups:
        return jsonify({'error': "Usuário não tem permissão para realizar esta operação"}), 403
    
    return None