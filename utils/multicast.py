import socket
import struct

# IP e porta padrão do grupo multicast
GRUPO_MULTICAST = '224.0.0.1'
PORTA_MULTICAST = 10000

def criar_socket_multicast_receptor(grupo=GRUPO_MULTICAST, porta=PORTA_MULTICAST):
    """
    Cria um socket configurado para escutar mensagens multicast UDP.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', porta))

    mreq = struct.pack("4sl", socket.inet_aton(grupo), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    return sock

def enviar_multicast(data, grupo=GRUPO_MULTICAST, porta=PORTA_MULTICAST, ttl=2):
    """
    Envia dados para o grupo multicast.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    sock.sendto(data, (grupo, porta))
    sock.close()
