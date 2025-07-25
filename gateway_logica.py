import grpc
import threading
import json
import pika
from gateway_atuadores_pb2_grpc import AtuadorServiceStub
from gateway_atuadores_pb2 import Empty, ConfiguracaoRequest

RABBITMQ_HOST = 'localhost'
SENSOR_FILAS = ['sensor_temperatura', 'sensor_umidade']


class GatewayCore:
    
    DEFAULT_ATUADORES = [
        {'id_atuador': 'semaforo', 'nome':'Semaforo Rua 1','host': 'localhost', 'port': 50051, 'tipo': 'atuador'},
        {'id_atuador': 'camera',  'nome':'Camera Portao 1', 'host': 'localhost', 'port': 50052, 'tipo': 'atuador'},
        {'id_atuador': 'poste', 'nome':'Poste Rua 1', 'host': 'localhost', 'port': 50053,  'tipo': 'atuador'},
    ]

    def __init__(self):
        self.dispositivos = {}  # Registros de sensores e atuadores
        self.atuadores = {}     # Stubs gRPC dos atuadores
        self.sensores = {}     # Leituras sensoriais

        self._iniciar_rabbitmq()
        self._iniciar_consumo_sensores()

        # Registrar todos os atuadores pré-definidos
        self._registrar_atuadores()

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
                    on_message_callback=lambda ch, method, props, body, f=fila: 
                        self._callback_sensor(ch, method, props, body, f),
                    auto_ack=True
                )
            print("[Gateway] Consumindo dados sensoriais...")
            self.rabbit_channel.start_consuming()

        threading.Thread(target=consumir, daemon=True).start()

    def _callback_sensor(self, ch, method, properties, body, fila):
        dados = json.loads(body)
        sensor_id = dados.get("id_sensor")

        if sensor_id:
            if sensor_id not in self.sensores:
                self.sensores[sensor_id] = {
                    "fila": fila,
                    "valores": [],  # Histórico de valores
                    "datahoras": [],  # Histórico de timestamps
                    "ip_sensor": dados.get("ip_sensor")
                }

            self.sensores[sensor_id]["valores"].append(dados.get("valor"))
            self.sensores[sensor_id]["datahoras"].append(dados.get("datahora"))

            print(f"[Sensor {sensor_id}] Valor registrado: {dados.get('valor')}")


    def get_leituras_sensor(self, fila):
        return self.sensores

    # ---------- REGISTRO DE ATUADORES ----------
    def _registrar_atuadores(self):
        for cfg in self.DEFAULT_ATUADORES:
            self.registrar_atuador(
                cfg['id_atuador'],
                cfg['nome'],
                cfg['host'],
                cfg['port'],
                cfg.get('tipo', 'atuador')
            )

    def registrar_atuador(self, id_atuador, nome, host, port, tipo='atuador'):
        canal = grpc.insecure_channel(f"{host}:{port}")
        stub = AtuadorServiceStub(canal)
        self.atuadores[id_atuador] = stub
        self.dispositivos[id_atuador] = {
            "id": id_atuador,
            "nome":nome,
            "tipo": tipo,
            "ip": host,
            "porta_grpc": port
        }
        print(f"[gRPC] Atuador '{id_atuador}' registrado em {host}:{port}")

    # ---------- CONTROLE DE ATUADORES via gRPC ----------
    def ligar_atuador(self, id_atuador):
        return self.atuadores[id_atuador].Ligar(Empty())

    def desligar_atuador(self, id_atuador):
        return self.atuadores[id_atuador].Desligar(Empty())

    def configurar_atuador(self, id_atuador, parametro, valor):
        req = ConfiguracaoRequest(parametro=parametro, valor=valor)
        return self.atuadores[id_atuador].AlterarConfiguracao(req)

    def estado_atuador(self, id_atuador):
        return self.atuadores[id_atuador].ConsultarEstado(Empty())

    # ---------- LISTAGENS ----------
    def listar_atuadores(self):
        return {
            id: info
            for id, info in self.dispositivos.items()
            if info.get('tipo') == 'atuador'
        }

    def listar_sensores(self):
        sensores_listados = {}

        for sensor_id, dados in self.sensores.items():
            sensores_listados[sensor_id] = {
                "fila": dados.get("fila"),
                "ip_sensor": dados.get("ip_sensor"),
                "quantidade_leituras": len(dados.get("valores", [])),
                "ultima_leitura": dados["valores"][-1] if dados.get("valores") else None,
                "datahora_ultima": dados["datahoras"][-1] if dados.get("datahoras") else None,
                "todos_valores": dados.get("valores", []),
                "todos_horarios": dados.get("datahoras", [])
            }

        return sensores_listados


