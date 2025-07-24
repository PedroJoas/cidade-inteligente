from flask import Flask, jsonify, request
from gateway_logica import GatewayCore  # Sua classe central

app = Flask(__name__)
gw = GatewayCore()
gw.iniciar_descoberta_dispositivos()  

@app.route('/dispositivos/estado/<id>', methods=['GET'])
def consultar_estado(id):
    try:
        estado = gw.estado_atuador(id)
        return jsonify({
            'estado': estado.estado,
            'configuracoes': dict(estado.configuracoes)
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 404

@app.route('/dispositivos/comando/<id>', methods=['POST'])
def enviar_comando(id):
    comando = request.json.get('comando')
    try:
        if comando == 'ligar':
            resposta = gw.ligar_atuador(id)
        elif comando == 'desligar':
            resposta = gw.desligar_atuador(id)
        else:
            return jsonify({'erro': 'Comando inválido'}), 400
        return jsonify({
            'mensagem': resposta.mensagem,
            'sucesso': resposta.sucesso
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 404

@app.route('/dispositivos/configurar/<id>', methods=['POST'])
def configurar(id):
    parametro = request.json.get('parametro')
    valor = request.json.get('valor')
    try:
        resposta = gw.configurar_atuador(id, parametro, valor)
        return jsonify({
            'mensagem': resposta.mensagem,
            'sucesso': resposta.sucesso
        })
    except Exception as e:
        return jsonify({'erro': str(e)}), 404

@app.route('/sensores/<tipo>', methods=['GET'])
def consultar_sensores(tipo):
    dados = gw.get_leituras_sensor(tipo)
    return jsonify({'leituras': dados})

@app.route('/atuadores')
def listar_atuadores():
    return gw.dispositivos

@app.route('/sensores')
def listar_sensores():
    return jsonify(gw.listar_sensores())

if __name__ == '__main__':
    app.run(port=5000, debug=True)
