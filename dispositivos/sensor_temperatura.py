from utils import multicast
import socket
import struct
import time
import random
import threading
from protos import gateway_atuadores_pb2 as pb

# CONFIGURAÇÕES DO SENSOR
ID = "sensor_temp_001"
TIPO = "SensorTemperatura"
ESTADO_INICIAL = "OK"
PORTA_UDP_SENSOR = 5007
UNIDADE = "Celsius"

# Função para participar da descoberta multicast e responder ao gateway
def escutar_multicast():
    sock = multicast.criar_socket_multicast_receptor()
    print("[MULTICAST] Aguardando mensagens de descoberta...")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = pb.DescobertaMulticast()
        msg.ParseFromString(data)

        if msg.tipo_mensagem == pb.DescobertaMulticast.REQUISICAO_DESCOBERTA:
            print(f"[MULTICAST] Recebido do gateway: {addr}")

            resposta = pb.DescobertaMulticast()
            resposta.tipo_mensagem = pb.DescobertaMulticast.RESPOSTA_DESCOBERTA
            resposta.ip_gateway = addr[0]
            resposta.porta_gateway_tcp = msg.porta_gateway_tcp

            info = resposta.informacao_dispositivo
            info.id = ID
            info.tipo = TIPO
            info.ip = socket.gethostbyname(socket.gethostname())
            info.porta = PORTA_UDP_SENSOR
            info.estado = ESTADO_INICIAL

            sock.sendto(resposta.SerializeToString(), addr)
            print(f"[MULTICAST] Resposta enviada ao gateway.")
            break
    
# Função que envia temperatura periódica ao gateway
def enviar_temperatura():
    endereco_gateway = ('127.0.0.1', 12347)  # definir IP e porta reais do gateway UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        temperatura = round(random.uniform(20.0, 30.0), 2)
        msg = pb.AtualizacaoEstadoDispositivo()
        msg.id_dispositivo = ID
        msg.estado_atual = "OK"
        msg.valor_leitura = temperatura
        msg.unidade = UNIDADE

        sock.sendto(msg.SerializeToString(), endereco_gateway)
        print(f"[SENSOR] Temperatura enviada: {temperatura}°C")
        time.sleep(15)

# Início do sensor
if __name__ == "__main__":
    t1 = threading.Thread(target=escutar_multicast)
    t2 = threading.Thread(target=enviar_temperatura)

    t1.start()
    t2.start()
    t1.join()
    t2.join()
