import grpc
from concurrent import futures
import time

import gateway_atuadores_pb2 as pb2
import gateway_atuadores_pb2_grpc as pb2_grpc
import json

class LampadaServicer(pb2_grpc.AtuadorServiceServicer):
    def __init__(self):
        self.estado = "desligado"

    def Ligar(self, request, context):
        self.estado = "ligado"
        print("[Lâmpada] Comando: Ligar")
        return pb2.Resposta(mensagem="Lâmpada ligada", sucesso=True)

    def Desligar(self, request, context):
        self.estado = "desligado"
        print("[Lâmpada] Comando: Desligar")
        return pb2.Resposta(mensagem="Lâmpada desligada", sucesso=True)

    def AlterarConfiguracao(self, request, context):
        # Este atuador não possui configurações dinâmicas
        return pb2.Resposta(mensagem="Este atuador não suporta configurações", sucesso=False)

    def ConsultarEstado(self, request, context):
        print(f"[Lâmpada] Estado atual: {self.estado}")
        return pb2.EstadoResponse(estado=self.estado, configuracoes={})
import socket
import json

def responder_ao_gateway(nome, id):
    MCAST_GRP = '239.255.0.1'
    MCAST_PORT = 5007

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.bind(('', MCAST_PORT))

    mreq = socket.inet_aton(MCAST_GRP) + socket.inet_aton('0.0.0.0')
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print("[Lâmpada] Aguardando mensagem multicast...")

    while True:
        data, addr = sock.recvfrom(1024)
        data = json.loads(data.decode())
        addr = addr[0]
        print(f"[Lâmpada] Mensagem recebida: {data} de {addr}")
        if data['codigo'] == "DISCOVERY_GW":
            info = {
                "id": id,
                "tipo": 'atuador',
                "ip": socket.gethostbyname(socket.gethostname()),
                "porta_grpc": 5051
            }
            resposta = json.dumps(info).encode()
            sock_resposta = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock_resposta.sendto(resposta, (addr, data['porta']))
            print(f"[{nome.upper()}] Resposta enviada ao Gateway: {info}")
            break  # responde uma vez e sai (ou pode continuar respondendo)

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    pb2_grpc.add_AtuadorServiceServicer_to_server(LampadaServicer(), server)
    server.add_insecure_port('[::]:5051')
    server.start()
    print("[Lâmpada] Servidor gRPC rodando na porta 5051...")
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == '__main__':
    responder_ao_gateway(nome='lampada sala',id='lampadada-01')
    serve()
