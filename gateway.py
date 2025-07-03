import socket
import threading
import time
import struct
from Protos import cliente_gateway_pb2
from Protos import gateway_atuadores_pb2

# Configurações
IP_GATEWAY = '0.0.0.0'
PORTA_TCP_CLIENTE = 50000
PORTA_UDP_MULTICAST = 12346
GRUPO_MULTICAST = '224.1.1.1'
PORTA_UDP_DISPOSITIVOS = 12347

class Gateway:
    def __init__(self):
        self.dispositivos_conectados = {}
        self.dispositivos_lock = threading.Lock()
        
        # Sockets
        self.socket_tcp = None
        self.socket_multicast = None
        self.socket_udp = None

    def iniciar_servidor_tcp(self):
        """Inicia o servidor TCP para comunicação com clientes"""
        self.socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_tcp.bind((IP_GATEWAY, PORTA_TCP_CLIENTE))
        self.socket_tcp.listen(5)
        print(f"[Gateway] Servidor TCP iniciado em {IP_GATEWAY}:{PORTA_TCP_CLIENTE}")

    def iniciar_multicast(self):
        """Configura o socket multicast para descoberta de dispositivos"""
        self.socket_multicast = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_multicast.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Junta-se ao grupo multicast sem bind
        mreq = struct.pack("4sl", socket.inet_aton(GRUPO_MULTICAST), socket.INADDR_ANY)
        self.socket_multicast.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        print(f"[Gateway] Escutando multicast no grupo {GRUPO_MULTICAST}")

    def iniciar_udp_dispositivos(self):
        """Inicia socket UDP para comunicação com dispositivos"""
        self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket_udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_udp.bind((IP_GATEWAY, PORTA_UDP_DISPOSITIVOS))
        print(f"[Gateway] Escutando dispositivos em UDP {IP_GATEWAY}:{PORTA_UDP_DISPOSITIVOS}")

    def enviar_requisicao_descoberta(self):
        """Envia requisição de descoberta para dispositivos"""
        req = gateway_atuadores_pb2.DescobertaMulticast()
        req.tipo_mensagem = gateway_atuadores_pb2.DescobertaMulticast.REQUISICAO_DESCOBERTA
        req.ip_gateway = IP_GATEWAY
        req.porta_gateway_tcp = PORTA_TCP_CLIENTE
        
        self.socket_multicast.sendto(req.SerializeToString(), (GRUPO_MULTICAST, PORTA_UDP_MULTICAST))
        print("[Gateway] Requisição de descoberta enviada")

    def tratar_resposta_multicast(self):
        """Processa respostas de descoberta de dispositivos"""
        while True:
            try:
                data, addr = self.socket_multicast.recvfrom(1024)
                resposta = gateway_atuadores_pb2.DescobertaMulticast()
                resposta.ParseFromString(data)

                if resposta.tipo_mensagem == gateway_atuadores_pb2.DescobertaMulticast.RESPOSTA_DESCOBERTA:
                    dispositivo = resposta.informacao_dispositivo
                    
                    with self.dispositivos_lock:
                        if dispositivo.id not in self.dispositivos_conectados:
                            self.dispositivos_conectados[dispositivo.id] = {
                                'tipo': dispositivo.tipo,
                                'ip': dispositivo.ip,
                                'porta': dispositivo.porta,
                                'estado': dispositivo.estado
                            }
                            print(f"[Gateway] Novo dispositivo registrado: {dispositivo.id}")
                        else:
                            # Atualiza estado se dispositivo já existir
                            self.dispositivos_conectados[dispositivo.id]['estado'] = dispositivo.estado

            except Exception as e:
                print(f"[Gateway] Erro no multicast: {e}")

    def tratar_cliente(self, conexao, endereco):
        """Gerencia conexão com um cliente"""
        print(f"[Gateway] Cliente conectado: {endereco}")
        
        try:
            while True:
                # Recebe tamanho da mensagem
                tamanho_bytes = conexao.recv(4)
                if not tamanho_bytes:
                    break
                tamanho = int.from_bytes(tamanho_bytes, 'big')

                # Recebe mensagem completa
                dados = b''
                while len(dados) < tamanho:
                    parte = conexao.recv(tamanho - len(dados))
                    if not parte:
                        break
                    dados += parte

                requisicao = cliente_gateway_pb2.ClienteRequisicao()
                requisicao.ParseFromString(dados)

                resposta = cliente_gateway_pb2.RespostaGateway()
                
                if requisicao.request_type == cliente_gateway_pb2.ClienteRequisicao.LISTAR_DISPOSITIVOS:
                    resposta = self.processar_listagem()
                
                elif requisicao.request_type == cliente_gateway_pb2.ClienteRequisicao.ENVIAR_COMANDO:
                    resposta = self.processar_comando(requisicao.comando_cliente)
                
                # Envia resposta
                serializado = resposta.SerializeToString()
                conexao.sendall(len(serializado).to_bytes(4, 'big') + serializado)

        except Exception as e:
            print(f"[Gateway] Erro com cliente {endereco}: {e}")
        finally:
            conexao.close()
            print(f"[Gateway] Cliente desconectado: {endereco}")

    def processar_listagem(self):
        """Prepara resposta com lista de dispositivos"""
        resposta = cliente_gateway_pb2.RespostaGateway()
        resposta.response_type = cliente_gateway_pb2.RespostaGateway.LISTAR_DISPOSITIVOS
        
        with self.dispositivos_lock:
            for dev_id, info in self.dispositivos_conectados.items():
                dispositivo = resposta.devices.add()
                dispositivo.id = dev_id
                dispositivo.tipo = info['tipo']
                dispositivo.ip = info['ip']
                dispositivo.porta = info['porta']
                dispositivo.estado = info['estado']
        
        return resposta

    def processar_comando(self, comando_cliente):
        """Processa comando do cliente e envia para o dispositivo"""
        resposta = cliente_gateway_pb2.RespostaGateway()
        resposta.response_type = cliente_gateway_pb2.RespostaGateway.ENVIAR_COMANDO
        
        with self.dispositivos_lock:
            if comando_cliente.id_dispositivo not in self.dispositivos_conectados:
                resposta.sucesso = False
                resposta.message = f"Dispositivo {comando_cliente.id_dispositivo} não encontrado"
                return resposta

            dispositivo = self.dispositivos_conectados[comando_cliente.id_dispositivo]
            
            try:
                # Converte comando do cliente para comando do dispositivo
                comando = gateway_atuadores_pb2.ComandoAtuador()
                comando.id_dispositivo = comando_cliente.id_dispositivo
                
                # Mapeamento de tipos de comando
                if comando_cliente.tipo_comando == cliente_gateway_pb2.ComandoCliente.LIGAR_DESLIGAR:
                    comando.tipo_comando = gateway_atuadores_pb2.ComandoAtuador.LIGAR_DESLIGAR
                elif comando_cliente.tipo_comando == cliente_gateway_pb2.ComandoCliente.DEFINIR_TEMPERATURA:
                    comando.tipo_comando = gateway_atuadores_pb2.ComandoAtuador.DEFINIR_TEMPERATURA
                    comando.valor = comando_cliente.valor
                
                # Envia comando via UDP para o dispositivo
                self.socket_udp.sendto(
                    comando.SerializeToString(),
                    (dispositivo['ip'], dispositivo['porta'])
                )
                
                resposta.sucesso = True
                resposta.message = f"Comando enviado para {comando_cliente.id_dispositivo}"
                
                # Atualiza estado local
                if comando.tipo_comando == gateway_atuadores_pb2.ComandoAtuador.LIGAR_DESLIGAR:
                    dispositivo['estado'] = "ligado" if dispositivo['estado'] == "desligado" else "desligado"
                
            except Exception as e:
                resposta.sucesso = False
                resposta.message = f"Erro ao enviar comando: {str(e)}"
        
        return resposta

    def monitorar_dispositivos_udp(self):
        """Recebe atualizações de estado dos dispositivos"""
        while True:
            try:
                data, addr = self.socket_udp.recvfrom(1024)
                atualizacao = gateway_atuadores_pb2.AtualizacaoEstadoDispositivo()
                atualizacao.ParseFromString(data)
                
                with self.dispositivos_lock:
                    if atualizacao.id_dispositivo in self.dispositivos_conectados:
                        self.dispositivos_conectados[atualizacao.id_dispositivo]['estado'] = atualizacao.estado_atual
                        print(f"[Gateway] Estado atualizado: {atualizacao.id_dispositivo} = {atualizacao.estado_atual}")
                    
            except Exception as e:
                print(f"[Gateway] Erro ao receber atualização UDP: {e}")

    def loop_descoberta(self):
        """Envia requisições de descoberta periodicamente"""
        while True:
            self.enviar_requisicao_descoberta()
            time.sleep(10)

    def executar(self):
        """Inicia todos os serviços do gateway"""
        try:
            self.iniciar_servidor_tcp()
            self.iniciar_multicast()
            self.iniciar_udp_dispositivos()

            # Threads
            threading.Thread(target=self.tratar_resposta_multicast, daemon=True).start()
            threading.Thread(target=self.monitorar_dispositivos_udp, daemon=True).start()
            threading.Thread(target=self.loop_descoberta, daemon=True).start()

            # Loop principal para aceitar clientes
            while True:
                conexao, endereco = self.socket_tcp.accept()
                threading.Thread(target=self.tratar_cliente, args=(conexao, endereco), daemon=True).start()

        except KeyboardInterrupt:
            print("\n[Gateway] Desligando...")
        finally:
            if self.socket_tcp: self.socket_tcp.close()
            if self.socket_multicast: self.socket_multicast.close()
            if self.socket_udp: self.socket_udp.close()

if __name__ == "__main__":
    gateway = Gateway()
    gateway.executar()