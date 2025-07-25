import pika
import json
import random
import time
import socket
from datetime import datetime

class SensorUmidade:
    def __init__(self, sensor_id, host='localhost', port=5672, queue_name='sensor_umidade', nome='Sensor de Umidade'):
        self.id = sensor_id
        self.nome = nome
        self.rabbitmq_host = host
        self.rabbitmq_port = port
        self.queue_name = queue_name
        self.channel = self._conectar_rabbitmq()

    def _conectar_rabbitmq(self):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=self.rabbitmq_host, port=self.rabbitmq_port)
        )
        channel = connection.channel()
        channel.queue_declare(queue=self.queue_name, durable=True)
        return channel

    def _ler_umidade(self):
        return round(random.uniform(35.0, 80.0), 2)  # Umidade em %

    def _get_ip_local(self):
        return socket.gethostbyname(socket.gethostname())

    def iniciar(self):
        print(f"Sensor {self.id} de umidade iniciado. Enviando dados para fila: {self.queue_name}")
        while True:
            umidade = self._ler_umidade()
            mensagem = {
                'id_sensor': self.id,
                'fila': self.queue_name,
                'nome_sensor': self.nome,
                'valor': umidade,
                'datahora': datetime.now().isoformat(),
                'ip_sensor': self._get_ip_local()
            }
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=json.dumps(mensagem)
            )
            print(f"[Sensor {self.id}] Enviado: {mensagem}")
            time.sleep(15)

if __name__ == '__main__':
    sensor = SensorUmidade(sensor_id='sensor_umidade_01', nome='Sensor de Umidade Sala')
    sensor.iniciar()
