from utils import multicast
import socket
import struct
import threading
from protos import gateway_atuadores_pb2 as pb

# CONFIGURAÇÕES DO SEMÁFORO
ID = "semaforo_001"
TIPO = "Semaforo"
PORTA_TCP = 5008
ESTADO_ATUAL = "VERDE"

# Multicast: participa da descoberta inicial
def escutar_multicast():
    sock = multicast.criar_socket_multicast_receptor()
    print("[MULTICAST] Aguardando descoberta...")

    while True:
        data, addr = sock.recvfrom(1024)
        msg = pb.DescobertaMulticast()
        msg.ParseFromString(data)

        if msg.tipo_mensagem == pb.DescobertaMulticast.REQUISICAO_DESCOBERTA:
            print(f"[MULTICAST] Gateway encontrado em {addr}")

            resposta = pb.DescobertaMulticast()
            resposta.tipo_mensagem = pb.DescobertaMulticast.RESPOSTA_DESCOBERTA
            resposta.ip_gateway = addr[0]
            resposta.porta_gateway_tcp = msg.porta_gateway_tcp

            info = resposta.informacao_dispositivo
            info.id = ID
            info.tipo = TIPO
            info.ip = socket.gethostbyname(socket.gethostname())
            info.porta = PORTA_TCP
            info.estado = ESTADO_ATUAL

            sock.sendto(resposta.SerializeToString(), addr)
            print(f"[MULTICAST] Enviado resposta ao gateway.")
            break
        
# TCP: escuta comandos do gateway
def escutar_comando_tcp():
    global ESTADO_ATUAL

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('0.0.0.0', PORTA_TCP))
    sock.listen(1)

    print(f"[TCP] Aguardando comandos na porta {PORTA_TCP}...")

    while True:
        conn, addr = sock.accept()
        print(f"[TCP] Conectado ao gateway {addr}")
        try:

            tamanho_bytes = conn.recv(4)
            if not tamanho_bytes:
                continue

            tamanho_msg = int.from_bytes(tamanho_bytes, 'big')
            data = conn.recv(tamanho_msg)
            
            comando = pb.ComandoAtuador()
            comando.ParseFromString(data)

            if comando.id_dispositivo == ID:
                tipo = comando.tipo_comando

                if tipo == pb.ComandoAtuador.LIGAR_DESLIGAR:
                    novo_estado = "VERMELHO" if ESTADO_ATUAL == "VERDE" else "VERDE"
                    print(f"[SEMAFORO] Alterando estado: {ESTADO_ATUAL} -> {novo_estado}")
                    ESTADO_ATUAL = novo_estado
            else:
                print(f"[SEMAFORO] Comando desconhecido para semáforo")
        except Exception as e:
            print(f"[SEMAFORO] Erro ao processar comando: {e}")
        finally:
            conn.close()
        

# Início do semáforo
if __name__ == "__main__":
    t1 = threading.Thread(target=escutar_multicast)
    t2 = threading.Thread(target=escutar_comando_tcp)

    t1.start()
    t2.start()
    t1.join()
    t2.join()
