from flask import Flask, render_template, request, redirect, url_for
import requests

app = Flask(__name__)


GATEWAY_URL = 'http://localhost:5000'

@app.route('/')
def index():
    return redirect(url_for('atuadores'))

@app.route('/atuadores', methods=['GET', 'POST'])
def atuadores():
    if request.method == 'POST':
        actuator_id = request.form.get('id')
        comando = request.form.get('comando')

        if comando == 'configurar':
            parametro = request.form.get('parametro')
            valor = request.form.get('valor')
            requests.post(f'{GATEWAY_URL}/atuadores/{actuator_id}/configurar',
                          json={'parametro': parametro, 'valor': valor})
        else:
            requests.post(f'{GATEWAY_URL}/atuadores/{actuator_id}/comando',
                          json={'comando': comando})

        return redirect(url_for('atuadores'))

    
    resp = requests.get(f'{GATEWAY_URL}/atuadores')
    atuadores = resp.json()

    
    for id, a in atuadores.items():
        estado_resp = requests.get(f'{GATEWAY_URL}/atuadores/{id}/estado')
        estado = estado_resp.json()
        a['status'] = estado.get('estado', 'Desconectado')

    return render_template('atuadores.html', atuadores=atuadores)



@app.route('/sensores')
def sensores():
    
    resp = requests.get(f'{GATEWAY_URL}/sensores')
    sensores = resp.json()
    return render_template('sensores.html', sensores=sensores)


if __name__ == '__main__':
    app.run(debug=True, port=8000)
