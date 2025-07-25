from flask import Flask, jsonify, request
from gateway_logica import GatewayCore

app = Flask(__name__)
gw = GatewayCore()

@app.route('/atuadores', methods=['GET'])
def listar_atuadores():
    # Lista de atuadores já registrados
    atuadores = gw.listar_atuadores()
    return jsonify(atuadores)

@app.route('/sensores', methods=['GET'])
def listar_sensores():
    print("Listando sensores...")
    # Lista de sensores (mesmo dispositivos, filtrados)
    sensores = gw.listar_sensores()
    return jsonify(sensores)

@app.route('/atuadores/<id>/estado', methods=['GET'])
def consultar_estado(id):
    # Retorna estado e configurações do atuador
    try:
        estado = gw.estado_atuador(id)
        return jsonify({
            'id': id,
            'estado': estado.estado,
            'configuracoes': dict(estado.configuracoes)
        })
    except KeyError:
        return jsonify({'erro': f'Atuador {id} não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/atuadores/<id>/comando', methods=['POST'])
def enviar_comando(id):
    data = request.get_json() or {}
    comando = data.get('comando')
    if comando not in ('ligar', 'desligar'):
        return jsonify({'erro': 'Comando inválido'}), 400

    try:
        if comando == 'ligar':
            resp = gw.ligar_atuador(id)
        else:  # desligar
            resp = gw.desligar_atuador(id)

        return jsonify({
            'id': id,
            'mensagem': resp.mensagem,
            'sucesso': resp.sucesso
        })
    except KeyError:
        return jsonify({'erro': f'Atuador {id} não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/atuadores/<id>/configurar', methods=['POST'])
def configurar(id):
    data = request.get_json() or {}
    parametro = data.get('parametro')
    valor = data.get('valor')

    if not parametro or not valor:
        return jsonify({'erro': 'parametro e valor são obrigatórios'}), 400

    try:
        resp = gw.configurar_atuador(id, parametro, valor)
        return jsonify({
            'id': id,
            'mensagem': resp.mensagem,
            'sucesso': resp.sucesso
        })
    except KeyError:
        return jsonify({'erro': f'Atuador {id} não encontrado'}), 404
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/sensores/<fila>/leituras', methods=['GET'])
def consultar_sensores(fila):
    # Retorna leituras de uma fila de sensor específica
    leituras = gw.get_leituras_sensor(fila)
    return jsonify({
        'fila': fila,
        'leituras': leituras
    })

if __name__ == '__main__':
    app.run(port=5000, debug=True)
