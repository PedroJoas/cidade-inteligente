from utils import multicast
import socket
import struct
import time
import random
import threading
from Protos import gateway_atuadores_pb2 as proto

class SensorTemperatura:
    def __init__(self):
        # Configurações do dispositivo
        self.id_dispositivo = "sensor_temp_001"
        self.tipo_dispositivo = "SensorTemperatura"
        self.estado = "operacional"
        self.unidade_medida = "Celsius"
        
        # Configurações de rede
        self.grupo_multicast = '224.1.1.1'
        self.porta_multicast = 12346
        self.porta_udp = 5007
        self.ip_gateway = '127.0.0.1'
        self.porta_gateway_udp = 12347
        
        # Sockets
        self.socket_multicast = None
        self.socket_udp = None

    def participar_descoberta(self):
        """Participa do grupo multicast e responde às requisições do gateway"""
        self.socket_multicast = multicast.criar_socket_multicast_receptor()
        print("[SENSOR] Pronto para receber requisições de descoberta...")

        while True:
            try:
                dados, endereco = self.socket_multicast.recvfrom(1024)
                mensagem = proto.DescobertaMulticast()
                mensagem.ParseFromString(dados)

                if mensagem.tipo_mensagem == proto.DescobertaMulticast.REQUISICAO_DESCOBERTA:
                    print(f"[SENSOR] Recebida requisição do gateway {endereco}")

                    # Prepara resposta
                    resposta = proto.DescobertaMulticast()
                    resposta.tipo_mensagem = proto.DescobertaMulticast.RESPOSTA_DESCOBERTA
                    resposta.ip_gateway = endereco[0]
                    resposta.porta_gateway_tcp = mensagem.porta_gateway_tcp

                    # Informações do dispositivo
                    info = resposta.informacao_dispositivo
                    info.id = self.id_dispositivo
                    info.tipo = self.tipo_dispositivo
                    info.ip = socket.gethostbyname(socket.gethostname())
                    info.porta = self.porta_udp
                    info.estado = self.estado

                    self.socket_multicast.sendto(resposta.SerializeToString(), endereco)
                    print("[SENSOR] Resposta de descoberta enviada ao gateway")

            except Exception as erro:
                print(f"[SENSOR] Erro na descoberta multicast: {erro}")

    def enviar_leituras(self):
        """Envia leituras de temperatura periódicas para o gateway"""
        self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        while True:
            try:
                # Simula leitura de temperatura
                temperatura = round(random.uniform(20.0, 30.0), 2)
                
                # Prepara mensagem
                mensagem = proto.AtualizacaoEstadoDispositivo()
                mensagem.id_dispositivo = self.id_dispositivo
                mensagem.estado_atual = self.estado
                mensagem.valor_leitura = temperatura
                mensagem.unidade = self.unidade_medida

                # Envia para o gateway
                self.socket_udp.sendto(
                    mensagem.SerializeToString(),
                    (self.ip_gateway, self.porta_gateway_udp)
                )
                
                print(f"[SENSOR] Temperatura enviada: {temperatura}°C")
                time.sleep(15)  # Intervalo entre leituras

            except Exception as erro:
                print(f"[SENSOR] Erro ao enviar leitura: {erro}")
                time.sleep(5)

    def executar(self):
        """Inicia todas as funcionalidades do sensor"""
        try:
            # Thread para descoberta multicast
            thread_descoberta = threading.Thread(
                target=self.participar_descoberta,
                daemon=True
            )
            
            # Thread para envio de leituras
            thread_leituras = threading.Thread(
                target=self.enviar_leituras,
                daemon=True
            )

            thread_descoberta.start()
            thread_leituras.start()

            print("[SENSOR] Sensor de temperatura em operação")
            
            # Mantém as threads ativas
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n[SENSOR] Desligando sensor...")
        finally:
            if self.socket_multicast:
                self.socket_multicast.close()
            if self.socket_udp:
                self.socket_udp.close()

if __name__ == "__main__":
    sensor = SensorTemperatura()
    sensor.executar()