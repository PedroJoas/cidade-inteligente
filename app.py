from flask import Flask, render_template, request, redirect, url_for
import requests

app = Flask(__name__)
GATEWAY_URL = 'http://localhost:5000'  # URL do seu servidor Flask do Gateway

DISPOSITIVOS = ['poste-01', 'camera-01', 'semaforo-01']  # Mock inicial

@app.route('/')
def index():
    estados = []
    for d in DISPOSITIVOS:
        try:
            resp = requests.get(f'{GATEWAY_URL}/dispositivos/estado/{d}')
            estados.append({'id': d, 'estado': resp.json()['estado']})
        except:
            estados.append({'id': d, 'estado': 'indisponível'})
    return render_template('index.html', dispositivos=estados)

@app.route('/comando', methods=['POST'])
def comando():
    id = request.form['id']
    acao = request.form['acao']  # ligar/desligar
    requests.post(f'{GATEWAY_URL}/dispositivos/comando/{id}', json={'comando': acao})
    return redirect(url_for('index'))

@app.route('/sensores/<tipo>')
def sensores(tipo):
    resp = requests.get(f'{GATEWAY_URL}/sensores/{tipo}')
    dados = resp.json()['leituras']
    return render_template('index.html', dispositivos=[], sensores=dados, tipo=tipo)

if __name__ == '__main__':
    app.run(port=5500, debug=True)
