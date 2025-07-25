import grpc
from concurrent import futures


import gateway_atuadores_pb2 as pb2
import gateway_atuadores_pb2_grpc as pb2_grpc


class PosteServicer(pb2_grpc.AtuadorServiceServicer):
    """Servicer gRPC para um atuador de lâmpada simples."""

    def __init__(self):
        self.estado = "desligado"

    def Ligar(self, request, context):
        self.estado = "ligado"
        return pb2.Resposta(mensagem="Lâmpada ligada", sucesso=True)

    def Desligar(self, request, context):
        self.estado = "desligado"
        return pb2.Resposta(mensagem="Lâmpada desligada", sucesso=True)

    def AlterarConfiguracao(self, request, context):
        # Lâmpada não tem configuração dinâmica
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Este atuador não suporta configurações")
        return pb2.Resposta(mensagem="Não suportado", sucesso=False)

    def ConsultarEstado(self, request, context):
        # Retornamos mapa vazio pois não há configurações dinâmicas
        return pb2.EstadoResponse(estado=self.estado, configuracoes={})


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))

    pb2_grpc.add_AtuadorServiceServicer_to_server(PosteServicer(), server)
    server.add_insecure_port("[::]:50053")
    server.start()

    try:
        # Bloqueia até receber SIGINT/SIGTERM
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
