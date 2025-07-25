import grpc
from concurrent import futures
import gateway_atuadores_pb2 as atuador_pb2
import gateway_atuadores_pb2_grpc as atuador_pb2_grpc

class CameraServicer(atuador_pb2_grpc.AtuadorServiceServicer):
    def __init__(self):
        self.estado = "desligado"
        self.configuracoes = {"resolucao": "720p"}

    def Ligar(self, request, context):
        self.estado = "ligado"
        return atuador_pb2.Resposta(mensagem="Câmera ligada", sucesso=True)

    def Desligar(self, request, context):
        self.estado = "desligado"
        return atuador_pb2.Resposta(mensagem="Câmera desligada", sucesso=True)

    def AlterarConfiguracao(self, request, context):
        if request.parametro == "resolucao":
            self.configuracoes["resolucao"] = request.valor
            return atuador_pb2.Resposta(
                mensagem=f"Resolução atualizada para {request.valor}",
                sucesso=True
            )
        return atuador_pb2.Resposta(
            mensagem=f"Parâmetro '{request.parametro}' não suportado",
            sucesso=False
        )

    def ConsultarEstado(self, request, context):
        return atuador_pb2.EstadoResponse(
            estado=self.estado,
            configuracoes=self.configuracoes
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    atuador_pb2_grpc.add_AtuadorServiceServicer_to_server(CameraServicer(), server)
    server.add_insecure_port('[::]:50052')
    server.start()
    print("Câmera gRPC rodando em :50052")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
