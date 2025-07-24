import pika
import json
import random
import time
import socket

# Configurações do RabbitMQ
RABBITMQ_HOST = 'localhost'
RABBITMQ_PORT = 5672
QUEUE_NAME = 'sensor_temperatura'

# Função para simular leitura de temperatura
def ler_temperatura():
    return round(random.uniform(20.0, 35.0), 2)

# Descobrir IP local (útil para identificação)
def get_ip_local():
    return socket.gethostbyname(socket.gethostname())

def iniciar_sensor():
    # Conecta ao RabbitMQ
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
    )
    channel = connection.channel()

    # Garante que a fila existe
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    print("Sensor de temperatura iniciado. Enviando dados para fila:", QUEUE_NAME)

    while True:
        temperatura = ler_temperatura()
        mensagem = {
            'tipo': 'temperatura',
            'valor': temperatura,
            'unidade': 'C',
            'timestamp': time.time(),
            'ip_sensor': get_ip_local()
        }
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps(mensagem)
        )
        print(f"[Sensor] Enviado: {mensagem}")
        time.sleep(15)  # Envia a cada 15 segundos

if __name__ == '__main__':
    iniciar_sensor()
