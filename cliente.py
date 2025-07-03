import socket
import sys
from Protos import cliente_gateway_pb2 

class Cliente:
    def __init__(self, ip_gateway='127.0.0.1', porta_gateway=50000):
        self.ip_gateway = ip_gateway
        self.porta_gateway = porta_gateway
        self.socket_cliente = None

    def conectar_ao_gateway(self):
        """Estabelece conexão TCP com o gateway"""
        try:
            self.socket_cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_cliente.connect((self.ip_gateway, self.porta_gateway))
            print(f"Conectado ao Gateway em {self.ip_gateway}:{self.porta_gateway}")
            return True
        except (socket.error, ConnectionRefusedError) as e:
            print(f"Erro ao conectar ao Gateway: {e}")
            return False

    def enviar_mensagem(self, mensagem):
        """Envia mensagem serializada com prefixo de tamanho"""
        try:
            mensagem_serializada = mensagem.SerializeToString()
            tamanho = len(mensagem_serializada).to_bytes(4, 'big')
            self.socket_cliente.sendall(tamanho + mensagem_serializada)
            return True
        except (socket.error, AttributeError) as e:
            print(f"Erro ao enviar mensagem: {e}")
            self.desconectar()
            return False

    def receber_mensagem(self):
        """Recebe mensagem com prefixo de tamanho"""
        try:
            # Recebe os 4 bytes do tamanho
            tamanho_bytes = self.socket_cliente.recv(4)
            if not tamanho_bytes:
                return None
                
            tamanho_mensagem = int.from_bytes(tamanho_bytes, 'big')
            
            # Recebe a mensagem completa
            dados_recebidos = b''
            while len(dados_recebidos) < tamanho_mensagem:
                pacote = self.socket_cliente.recv(tamanho_mensagem - len(dados_recebidos))
                if not pacote:
                    return None
                dados_recebidos += pacote

            resposta = cliente_gateway_pb2.RespostaGateway()
            resposta.ParseFromString(dados_recebidos)
            return resposta
            
        except (socket.error, ConnectionResetError) as e:
            print(f"Erro ao receber mensagem: {e}")
            self.desconectar()
            return None

    def desconectar(self):
        """Fecha a conexão com o gateway"""
        if self.socket_cliente:
            try:
                self.socket_cliente.close()
                print("🔌 Desconectado do Gateway.")
            except:
                pass
            finally:
                self.socket_cliente = None

    def listar_dispositivos(self):
        """Solicita e exibe a lista de dispositivos conectados"""
        try:
            requisicao = cliente_gateway_pb2.ClienteRequisicao()
            requisicao.request_type = cliente_gateway_pb2.ClienteRequisicao.LISTAR_DISPOSITIVOS
            
            if not self.enviar_mensagem(requisicao):
                return
                
            resposta = self.receber_mensagem()
            
            if not resposta:
                print("Não foi possível obter resposta do Gateway")
                return
                
            if resposta.response_type == cliente_gateway_pb2.RespostaGateway.LISTAR_DISPOSITIVOS:
                print("\n=== DISPOSITIVOS CONECTADOS ===")
                if resposta.devices:
                    for dev in resposta.devices:
                        print(f"   ID: {dev.id}")
                        print(f"   Tipo: {dev.tipo}")
                        print(f"   Endereço: {dev.ip}:{dev.porta}")
                        print(f"   Estado: {dev.estado}")
                        print("   --------------------")
                else:
                    print("Nenhum dispositivo encontrado.")
            else:
                print(f"Resposta inesperada: {resposta.response_type}")
                
        except Exception as e:
            print(f"Erro inesperado: {e}")

    def enviar_comando(self, id_dispositivo, tipo_comando, valor=None):
        """Envia comando para um dispositivo específico"""
        try:
            # Validação básica
            if not id_dispositivo or not isinstance(tipo_comando, int):
                print("Parâmetros inválidos")
                return

            requisicao = cliente_gateway_pb2.ClienteRequisicao()
            requisicao.request_type = cliente_gateway_pb2.ClienteRequisicao.ENVIAR_COMANDO
            
            # Configura o comando
            comando = requisicao.comando_cliente
            comando.id_dispositivo = id_dispositivo
            comando.tipo_comando = tipo_comando
            
            if valor is not None:
                comando.valor = str(valor)

            print(f"📤 Enviando comando: {cliente_gateway_pb2.ComandoCliente.TipoComando.Name(tipo_comando)}")
            
            if not self.enviar_mensagem(requisicao):
                return
                
            resposta = self.receber_mensagem()
            
            if resposta:
                if resposta.sucesso:
                    print(f"Sucesso: {resposta.message}")
                else:
                    print(f"Falha: {resposta.message}")
            else:
                print("Nenhuma resposta do Gateway")
                
        except Exception as e:
            print(f"Erro ao enviar comando: {e}")

    def mostrar_menu_comandos(self):
        """Exibe menu de tipos de comando disponíveis"""
        print("\nTipos de Comando Disponíveis:")
        print(f"  {cliente_gateway_pb2.ComandoCliente.LIGAR_DESLIGAR} - Ligar/Desligar")
        print(f"  {cliente_gateway_pb2.ComandoCliente.DEFINIR_TEMPERATURA} - Definir Temperatura")
        
        try:
            tipo_comando = int(input("Digite o número do comando: "))
            
            if tipo_comando not in [cliente_gateway_pb2.ComandoCliente.LIGAR_DESLIGAR, 
                                   cliente_gateway_pb2.ComandoCliente.DEFINIR_TEMPERATURA]:
                print("Tipo de comando inválido")
                return None
                
            valor = None
            if tipo_comando == cliente_gateway_pb2.ComandoCliente.DEFINIR_TEMPERATURA:
                valor = input("Digite o valor da temperatura: ")
                
            return tipo_comando, valor
            
        except ValueError:
            print("Por favor, digite um número válido")
            return None

    def executar(self):
        """Loop principal da aplicação cliente"""
        if not self.conectar_ao_gateway():
            return
            
        try:
            while True:
                print("\n=== MENU PRINCIPAL ===")
                print("1. Listar Dispositivos")
                print("2. Enviar Comando")
                print("3. Sair")
                
                escolha = input("Escolha: ").strip()
                
                if escolha == '1':
                    self.listar_dispositivos()
                elif escolha == '2':
                    id_dispositivo = input("Digite o ID do dispositivo: ").strip()
                    if not id_dispositivo:
                        print("ID inválido")
                        continue
                        
                    comando_info = self.mostrar_menu_comandos()
                    if comando_info:
                        tipo_comando, valor = comando_info
                        self.enviar_comando(id_dispositivo, tipo_comando, valor)
                elif escolha == '3':
                    break
                else:
                    print("Opção inválida")
                    
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário")
        finally:
            self.desconectar()

if __name__ == "__main__":
    cliente = Cliente()
    cliente.executar()