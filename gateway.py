import socket
import threading
import time
import struct
import cliente_gateway_pb2      
import gateway_atuadores_pb2 


IP_GATEWAY = '127.0.0.1' 
PORTA_TCP_CLIENTE = 50000 
PORTA_UDP_MULTICAST = 12346 
GRUPO_MULTICAST = '224.1.1.1' 
PORTA_UDP_DISPOSITIVOS = 12347 

dispositivos_conectados = {}

dispositivos_lock = threading.Lock()


def iniciar_descoberta_multicast():

    multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2) 
    
    print(f"[Descoberta Multicast] Iniciando processo de descoberta multicast na porta {PORTA_UDP_MULTICAST}...")

    
    discovery_request = gateway_atuadores_pb2.DescobertaMulticast()
    discovery_request.tipo_mensagem = gateway_atuadores_pb2.DescobertaMulticast.REQUISICAO_DESCOBERTA
    discovery_request.ip_gateway = IP_GATEWAY
    discovery_request.porta_gateway_tcp = PORTA_TCP_CLIENTE 

    mensagem_serializada = discovery_request.SerializeToString()

    try:
        
        multicast_socket.sendto(mensagem_serializada, (GRUPO_MULTICAST, PORTA_UDP_MULTICAST))
        print(f"[Descoberta Multicast] Requisição multicast enviada para {GRUPO_MULTICAST}:{PORTA_UDP_MULTICAST}")
    except Exception as e:
        print(f"[Descoberta Multicast] Erro ao enviar requisição multicast: {e}")
    finally:
        multicast_socket.close()

def escutar_respostas_multicast():
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('', PORTA_UDP_MULTICAST)) 

    mreq = struct.pack("4sl", socket.inet_aton(GRUPO_MULTICAST), socket.INADDR_ANY)
    listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    print(f"[Descoberta Multicast] Escutando respostas multicast em {GRUPO_MULTICAST}:{PORTA_UDP_MULTICAST}...")

    while True:
        try:
            data, address = listen_socket.recvfrom(1024) 
            discovery_response = gateway_atuadores_pb2.DescobertaMulticast()
            discovery_response.ParseFromString(data)

            if discovery_response.tipo_mensagem == gateway_atuadores_pb2.DescobertaMulticast.RESPOSTA_DESCOBERTA:
                info_dispositivo = discovery_response.informacao_dispositivo 
                with dispositivos_lock:
                    if info_dispositivo.id not in dispositivos_conectados:
                        dispositivos_conectados[info_dispositivo.id] = {
                            "tipo": info_dispositivo.tipo, 
                            "ip": info_dispositivo.ip,
                            "porta": info_dispositivo.porta, 
                            "estado": info_dispositivo.estado 
                        }
                        print(f"[Descoberta Multicast] Dispositivo descoberto: ID={info_dispositivo.id}, Tipo={info_dispositivo.tipo}, IP={info_dispositivo.ip}, Porta={info_dispositivo.porta}, Estado={info_dispositivo.estado}")
                    else:
                        
                        dispositivos_conectados[info_dispositivo.id]["estado"] = info_dispositivo.estado
                        
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[Descoberta Multicast] Erro ao processar resposta multicast: {e}")


def tratar_cliente(conexao, endereco_cliente):

    print(f"[Cliente] Conexão estabelecida com o cliente {endereco_cliente}")
    while True:
        try:
            
            tamanho_bytes = conexao.recv(4)
            if not tamanho_bytes: 
                break
            tamanho_mensagem = int.from_bytes(tamanho_bytes, 'big')

            
            dados_recebidos = b''
            while len(dados_recebidos) < tamanho_mensagem:
                pacote = conexao.recv(tamanho_mensagem - len(dados_recebidos))
                if not pacote: 
                    break
                dados_recebidos += pacote
            
            if not dados_recebidos:
                break 

            requisicao = cliente_gateway_pb2.ClienteRequisicao() 
            requisicao.ParseFromString(dados_recebidos)

            resposta = cliente_gateway_pb2.RespostaGateway() 
            resposta.sucesso = True 

            if requisicao.tipo_requisicao == cliente_gateway_pb2.ClienteRequisicao.LISTAR_DISPOSITIVOS: 
                print(f"[Cliente {endereco_cliente}] Requisição: LISTAR_DISPOSITIVOS")
                resposta.tipo_resposta = cliente_gateway_pb2.RespostaGateway.LISTA_DISPOSITIVOS 
                with dispositivos_lock:
                    for dev_id, info in dispositivos_conectados.items():
                        device_proto = resposta.dispositivos.add() 
                        device_proto.id = dev_id
                        device_proto.tipo = info['tipo']
                        device_proto.ip = info['ip']
                        device_proto.porta = info['porta']
                        device_proto.estado = info['estado']
            
            elif requisicao.tipo_requisicao == cliente_gateway_pb2.ClienteRequisicao.ENVIAR_COMANDO: 
                print(f"[Cliente {endereco_cliente}] Requisição: ENVIAR_COMANDO para {requisicao.comando_cliente.id_dispositivo}")
                resposta.tipo_resposta = cliente_gateway_pb2.RespostaGateway.STATUS_COMANDO 
                
                id_dispositivo = requisicao.comando_cliente.id_dispositivo 
                tipo_comando_cliente = requisicao.comando_cliente.tipo_comando 
                valor_comando = requisicao.comando_cliente.valor

                with dispositivos_lock:
                    if id_dispositivo in dispositivos_conectados:
                        info_atuador = dispositivos_conectados[id_dispositivo]
                        
                        
                        try:
                            
                            comando_atuador_pb = gateway_atuadores_pb2.ComandoAtuador()
                            comando_atuador_pb.id_dispositivo = id_dispositivo
                            
                            
                            if tipo_comando_cliente == cliente_gateway_pb2.ComandoCliente.LIGAR_DESLIGAR:
                                comando_atuador_pb.tipo_comando = gateway_atuadores_pb2.ComandoAtuador.LIGAR_DESLIGAR
                                comando_atuador_pb.valor = "" 
                            elif tipo_comando_cliente == cliente_gateway_pb2.ComandoCliente.DEFINIR_TEMPERATURA:
                                comando_atuador_pb.tipo_comando = gateway_atuadores_pb2.ComandoAtuador.DEFINIR_TEMPERATURA
                                comando_atuador_pb.valor = valor_comando
                            

                            
                            if comando_atuador_pb.tipo_comando != gateway_atuadores_pb2.ComandoAtuador.COMANDO_ATUADOR_DESCONHECIDO:
                                atuador_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                
                                atuador_socket.connect((info_atuador['ip'], info_atuador['porta']))
                                
                                serializado_comando_atuador = comando_atuador_pb.SerializeToString()
                                atuador_socket.sendall(len(serializado_comando_atuador).to_bytes(4, 'big') + serializado_comando_atuador)
                                
                                
                                
                                

                                atuador_socket.close()
                                print(f"[Gateway->Atuador] Comando '{gateway_atuadores_pb2.ComandoAtuador.TipoComandoAtuador.Name(comando_atuador_pb.tipo_comando)}' enviado para {id_dispositivo} via TCP.")
                                resposta.mensagem = f"Comando enviado com sucesso para {id_dispositivo}."
                                
                                
                                if comando_atuador_pb.tipo_comando == gateway_atuadores_pb2.ComandoAtuador.LIGAR_DESLIGAR:
                                    current_state = info_atuador['estado']
                                    new_state = "Desligado" if current_state == "Ligado" else "Ligado"
                                    info_atuador['estado'] = new_state
                                elif comando_atuador_pb.tipo_comando == gateway_atuadores_pb2.ComandoAtuador.DEFINIR_TEMPERATURA:
                                    info_atuador['estado'] = f"Temperatura: {valor_comando}C"

                            else:
                                resposta.sucesso = False
                                resposta.mensagem = f"Tipo de comando de cliente desconhecido ou não mapeado para {id_dispositivo}."
                                print(f"[Comando] Tipo de comando de cliente desconhecido: {tipo_comando_cliente}")

                        except Exception as atu_e:
                            resposta.sucesso = False
                            resposta.mensagem = f"Falha ao comunicar com o atuador {id_dispositivo} via TCP: {atu_e}"
                            print(f"[Gateway->Atuador] Erro ao enviar comando TCP para {id_dispositivo}: {atu_e}")
                    else:
                        resposta.sucesso = False
                        resposta.mensagem = f"Dispositivo {id_dispositivo} não encontrado."
                        print(f"[Comando] Dispositivo {id_dispositivo} não encontrado.")
            
            else: 
                resposta.tipo_resposta = cliente_gateway_pb2.RespostaGateway.ERRO
                resposta.sucesso = False
                resposta.mensagem = "Requisição desconhecida."
                print(f"[Erro] Requisição desconhecida: {requisicao.tipo_requisicao}")

            
            serializado = resposta.SerializeToString()
            conexao.sendall(len(serializado).to_bytes(4, 'big') + serializado)

        except Exception as e:
            print(f"[Cliente {endereco_cliente}] Erro ao tratar requisição: {e}")
            break 
    
    print(f"[Cliente {endereco_cliente}] Conexão encerrada.")
    conexao.close()



def escutar_dispositivos_udp():

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    udp_socket.bind((IP_GATEWAY, PORTA_UDP_DISPOSITIVOS))
    print(f"[Dispositivos UDP] Escutando dados/estado de dispositivos UDP em {IP_GATEWAY}:{PORTA_UDP_DISPOSITIVOS}...")

    while True:
        try:
            data, address = udp_socket.recvfrom(1024)
            
            atualizacao_estado = gateway_atuadores_pb2.AtualizacaoEstadoDispositivo()
            atualizacao_estado.ParseFromString(data)

            with dispositivos_lock:
                if atualizacao_estado.id_dispositivo in dispositivos_conectados:
                    
                    dispositivos_conectados[atualizacao_estado.id_dispositivo]["estado"] = atualizacao_estado.estado_atual
                    print(f"[Dispositivos UDP] Estado/Leitura atualizado para {atualizacao_estado.id_dispositivo}: {atualizacao_estado.estado_atual} (Valor: {atualizacao_estado.valor_leitura} {atualizacao_estado.unidade})")
                else:
                    print(f"[Dispositivos UDP] Recebido dado de dispositivo não descoberto: ID={atualizacao_estado.id_dispositivo} de {address}")
        except Exception as e:
            print(f"[Dispositivos UDP] Erro ao receber dados UDP de dispositivos: {e}")


if __name__ == '__main__':
    
    server_tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) 
    server_tcp_socket.bind((IP_GATEWAY, PORTA_TCP_CLIENTE))
    server_tcp_socket.listen(5) 
    print(f"[Gateway] Servidor TCP para clientes iniciado em {IP_GATEWAY}:{PORTA_TCP_CLIENTE}")

    
    threading.Thread(target=escutar_respostas_multicast, daemon=True).start()

    
    threading.Thread(target=escutar_dispositivos_udp, daemon=True).start()

    
    def loop_descoberta():
        while True:
            iniciar_descoberta_multicast()
            time.sleep(10) 
    threading.Thread(target=loop_descoberta, daemon=True).start()

    
    while True:
        try:
            conn, addr = server_tcp_socket.accept()
            
            threading.Thread(target=tratar_cliente, args=(conn, addr), daemon=True).start()
        except Exception as e:
            print(f"[Gateway] Erro ao aceitar nova conexão TCP: {e}")
            break

    server_tcp_socket.close()
    print("[Gateway] Servidor encerrado.")