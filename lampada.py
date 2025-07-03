import socket
import struct
import threading
from datetime import datetime
from Protos import gateway_atuadores_pb2 as proto
import time

class AtuadorLampada:
    def __init__(self, device_id, device_type="lampada", porta_udp=None):
        self.device_id = device_id
        self.device_type = device_type
        self.estado = "desligado"
        
        # Configurações de rede
        self.MULTICAST_GROUP = '224.1.1.1'
        self.MULTICAST_PORT = 12346
        self.UDP_PORT = porta_udp if porta_udp else 12347
        
        # Configuração do socket multicast
        self.multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # IMPORTANTE: Bind no endereço específico
        self.multicast_socket.bind(('0.0.0.0', self.MULTICAST_PORT))
        
        # Grupo multicast
        mreq = struct.pack("4sl", socket.inet_aton(self.MULTICAST_GROUP), socket.INADDR_ANY)
        self.multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # Socket UDP comum
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind(('0.0.0.0', self.UDP_PORT))
        
        self._log(f"Iniciada na porta UDP {self.UDP_PORT}")

    def _log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _handle_multicast(self):
        while True:
            try:
                data, addr = self.multicast_socket.recvfrom(1024)
                req = proto.DescobertaMulticast()
                req.ParseFromString(data)
                
                if req.tipo_mensagem == proto.DescobertaMulticast.REQUISICAO_DESCOBERTA:
                    self._log(f"Recebida requisição de {addr[0]}")
                    
                    # Prepara resposta
                    resp = proto.DescobertaMulticast()
                    resp.tipo_mensagem = proto.DescobertaMulticast.RESPOSTA_DESCOBERTA
                    resp.ip_gateway = addr[0]
                    resp.porta_gateway_tcp = req.porta_gateway_tcp
                    
                    # Preenche informações
                    info = resp.informacao_dispositivo
                    info.id = self.device_id
                    info.tipo = self.device_type
                    info.ip = socket.gethostbyname(socket.gethostname())
                    info.porta = self.UDP_PORT
                    info.estado = self.estado
                    
                    # Envia resposta via UDP comum
                    self.udp_socket.sendto(resp.SerializeToString(), addr)
                    self._log(f"Resposta enviada para {addr[0]}:{req.porta_gateway_tcp}")
                    
            except Exception as e:
                self._log(f"Erro: {str(e)}")

    def run(self):
        threading.Thread(target=self._handle_multicast, daemon=True).start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self._log("Encerrando...")

if __name__ == "__main__":
    lampada = AtuadorLampada(device_id="lampada_sala_1", porta_udp=12348)
    lampada.run()