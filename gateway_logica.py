import socket
import grpc
import threading
import json
import pika
from gateway_atuadores_pb2_grpc import AtuadorServiceStub
from gateway_atuadores_pb2 import Empty, ConfiguracaoRequest

MCAST_GRP = '239.255.0.1'
MCAST_PORT = 5007
OUVIR_PORTA = 6000
RABBITMQ_HOST = 'localhost'
SENSOR_FILAS = ['sensor_temperatura', 'sensor_umidade']

class GatewayCore:
    def __init__(self):
        self.dispositivos = {}
        self._iniciar_rabbitmq()
        self._iniciar_consumo_sensores()

    # ---------- RABBITMQ ----------
    def _iniciar_rabbitmq(self):
        self.rabbit_conn = pika.BlockingConnection(
            pika.ConnectionParameters(RABBITMQ_HOST)
        )
        self.rabbit_channel = self.rabbit_conn.channel()
        for fila in SENSOR_FILAS:
            self.rabbit_channel.queue_declare(queue=fila, durable=True)

    def _iniciar_consumo_sensores(self):
        def consumir():
            for fila in SENSOR_FILAS:
                self.rabbit_channel.basic_consume(
                    queue=fila,
                    on_message_callback=lambda ch, method, props, body, f=fila: self._callback_sensor(ch, method, props, body, f),
                    auto_ack=True
                )
            print("[Gateway] Consumindo dados sensoriais...")
            self.rabbit_channel.start_consuming()

        threading.Thread(target=consumir, daemon=True).start()

    def _callback_sensor(self, ch, method, properties, body, fila):
        dados = json.loads(body)
        self.sensores.setdefault(fila, []).append(dados)
        print(f"[Sensor {fila}] -> {dados}")

    def get_leituras_sensor(self, fila):
        return self.sensores.get(fila, [])

    # ---------- UDP MULTICAST ----------
    
    def enviar_multicast_discovery(self):
        mensagem = b'{"codigo": "DISCOVERY_GW", "porta": 6000}'
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.sendto(mensagem, (MCAST_GRP, MCAST_PORT))
        print(f"[Gateway] Multicast enviado: {mensagem.decode()}")

    def iniciar_descoberta_dispositivos(self):
            self.enviar_multicast_discovery()

            threading.Thread(target=self._escutar_respostas_udp, daemon=True).start()

    def _escutar_respostas_udp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        sock.bind(('', OUVIR_PORTA))  # Escuta na porta multicast
        print(f"[Gateway] Escutando respostas de dispositivos na porta {MCAST_PORT}")

        while True:
            print("[Gateway] Aguardando resposta de dispositivos...")
            try:
                data, addr = sock.recvfrom(1024)
                print(f"[UDP] Resposta de {addr}: {data.decode()}")
                self._processar_dispositivo_descoberto(data)
            except Exception as e:
                print(f"[Erro UDP]: {e}")

    def _processar_dispositivo_descoberto(self, mensagem_bytes):
        print('[Gateway] Processando dispositivo descoberto...')
        try:
            info = json.loads(mensagem_bytes.decode())
            id = info['id']
            self.dispositivos[id] = info  # Armazena dispositivo

            if info['tipo'] == 'atuador':
                self.registrar_atuador(id, info['ip'], info['porta_grpc'])


            print(f"[Dispositivo registrado] {id} → {info}")
        except Exception as e:
            print(f"[Erro ao processar resposta]: {e}")

    # ---------- gRPC ----------
    def registrar_atuador(self, id_atuador, host, port):
        canal = grpc.insecure_channel(f"{host}:{port}")
        stub = AtuadorServiceStub(canal)
        self.atuadores[id_atuador] = stub
        print(f"[gRPC] Atuador '{id_atuador}' registrado em {host}:{port}")

    def ligar_atuador(self, id_atuador):
        resposta = self.atuadores[id_atuador].Ligar(Empty())
        return resposta

    def desligar_atuador(self, id_atuador):
        resposta = self.atuadores[id_atuador].Desligar(Empty())
        return resposta

    def configurar_atuador(self, id_atuador, parametro, valor):
        req = ConfiguracaoRequest(parametro=parametro, valor=valor)
        resposta = self.atuadores[id_atuador].AlterarConfiguracao(req)
        return resposta

    def estado_atuador(self, id_atuador):
        return self.atuadores[id_atuador].ConsultarEstado(Empty())
    
    def listar_atuadores(self):
        return self.dispositivos

    def listar_sensores(self):
        return {
            id: dados
            for id, dados in self.dispositivos.items()
            if dados.get('tipo') == 'sensor'
        }