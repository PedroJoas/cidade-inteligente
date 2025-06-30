import socket
import sys
import cliente_gateway_pb2 

IP_GATEWAY = '127.0.0.1'  
PORTA_TCP_GATEWAY = 50000 

class Cliente:
    def __init__(self, ip_gateway, porta_gateway):
        self.ip_gateway = ip_gateway
        self.porta_gateway = porta_gateway
        self.socket_cliente = None

    def conectar_ao_gateway(self):
        
        try:
            self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_cliente.connect((self.ip_gateway, self.porta_gateway))
            print(f"Conectado ao Gateway em {self.ip_gateway}:{self.porta_gateway}")
        except socket.error as e:
            print(f"Erro ao conectar ao Gateway: {e}")
            sys.exit(1)

    def enviar_mensagem(self, mensagem):
        
        try:
            mensagem_serializada = mensagem.SerializeToString()
            
            self.socket_cliente.sendall(len(mensagem_serializada).to_bytes(4, 'big') + mensagem_serializada)
        except socket.error as e:
            print(f"Erro ao enviar mensagem: {e}")
            self.desconectar()

    def receber_mensagem(self):
        
        try:
            
            tamanho_bytes = self.socket_cliente.recv(4)
            if not tamanho_bytes:
                return None
            tamanho_mensagem = int.from_bytes(tamanho_bytes, 'big')

            
            dados_recebidos = b''
            while len(dados_recebidos) < tamanho_mensagem:
                pacote = self.socket_cliente.recv(tamanho_mensagem - len(dados_recebidos))
                if not pacote:
                    return None
                dados_recebidos += pacote

            
            resposta = cliente_gateway_pb2.RespostaGateway() 
            resposta.ParseFromString(dados_recebidos)
            return resposta
        except socket.error as e:
            print(f"Erro ao receber mensagem: {e}")
            self.desconectar()
            return None

    def desconectar(self):
        
        if self.socket_cliente:
            print("Desconectando do Gateway.")
            self.socket_cliente.close()
            self.socket_cliente = None

    def listar_dispositivos(self):
        
        requisicao = cliente_gateway_pb2.ClienteRequisicao() 
        requisicao.request_type = cliente_gateway_pb2.ClienteRequisicao.LISTAR_DISPOSITIVOS 
        print("Solicitando lista de dispositivos...")
        self.enviar_mensagem(requisicao)
        resposta = self.receber_mensagem()
        if resposta and resposta.response_type == cliente_gateway_pb2.RespostaGateway.LISTAR_DISPOSITIVOS: 
            print("\n--- Dispositivos Conectados ---")
            if resposta.devices:
                for dev in resposta.devices:
                    
                    print(f"  ID: {dev.id}, Tipo: {dev.tipo}, IP: {dev.ip}, Porta: {dev.porta}, Estado: {dev.estado}")
            else:
                print("  Nenhum dispositivo conectado.")
            print("------------------------------")
        elif resposta:
            print(f"Tipo de resposta inesperado recebido: {cliente_gateway_pb2.RespostaGateway.TipoRequisicao.Name(resposta.response_type)}")
        else:
            print("Falha ao obter a lista de dispositivos.")

    def enviar_comando(self, id_dispositivo, tipo_comando, valor=None):
        
        requisicao = cliente_gateway_pb2.ClienteRequisicao() 
        requisicao.request_type = cliente_gateway_pb2.ClienteRequisicao.ENVIAR_COMANDO 
        
        
        requisicao.comando.id_dispositivo = id_dispositivo 
        requisicao.comando.Comando_type = tipo_comando    
        if valor is not None:
            requisicao.comando.value = valor

        print(f"Enviando comando para o dispositivo {id_dispositivo}: {cliente_gateway_pb2.Comando.TipoComando.Name(tipo_comando)} com valor {valor if valor is not None else 'N/A'}")
        self.enviar_mensagem(requisicao)
        resposta = self.receber_mensagem()
        if resposta and resposta.response_type == cliente_gateway_pb2.RespostaGateway.ENVIAR_COMANDO: 
            print(f"Status do comando para o dispositivo {id_dispositivo}: {'Sucesso' if resposta.sucesso else 'Falha'} - {resposta.message}") 
        elif resposta:
            print(f"Tipo de resposta inesperado recebido: {cliente_gateway_pb2.RespostaGateway.TipoRequisicao.Name(resposta.response_type)} - {resposta.message}")
        else:
            print("Falha ao obter o status do comando.")

    def executar(self):
        
        self.conectar_ao_gateway()
        print("\nO Gateway é responsável pela descoberta de dispositivos usando multicast UDP ao ser iniciado.")
        print("Dispositivos respondem a essa descoberta para se 'parearem' com o Gateway.")
        print("O cliente interage com os dispositivos já conhecidos pelo Gateway.")
        while True:
            print("\nMenu do Cliente:")
            print("1. Listar Dispositivos")
            print("2. Enviar Comando para Dispositivo")
            print("3. Sair")
            escolha = input("Digite sua escolha: ")

            if escolha == '1':
                self.listar_dispositivos()
            elif escolha == '2':
                id_dispositivo = input("Digite o ID do dispositivo: ")
                print("Tipos de Comando:")
                
                print(f"  {cliente_gateway_pb2.Comando.ALTERNA_ENERGIA.value}: Ligar/Desligar")
                print(f"  {cliente_gateway_pb2.Comando.SETAR_TEMPERATURA.value}: Ajustar Temperatura")
                
                tipo_comando_str = input("Digite o tipo de comando (número): ")
                try:
                    tipo_comando = int(tipo_comando_str)
                    valor = None
                    
                    if tipo_comando in [cliente_gateway_pb2.Comando.SETAR_TEMPERATURA]:
                        valor = input("Digite o valor do comando: ")
                    self.enviar_comando(id_dispositivo, tipo_comando, valor)
                except ValueError:
                    print("Tipo de comando inválido. Por favor, digite um número.")
            elif escolha == '3':
                self.desconectar()
                break
            else:
                print("Escolha inválida. Por favor, tente novamente.")

if __name__ == "__main__":
    cliente = Cliente(IP_GATEWAY, PORTA_TCP_GATEWAY)
    cliente.executar()