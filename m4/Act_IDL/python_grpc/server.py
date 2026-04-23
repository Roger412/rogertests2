import grpc
from concurrent import futures
import greeting_pb2
import greeting_pb2_grpc


class GreeterServicer(greeting_pb2_grpc.GreeterServicer):

    def SayHello(self, request, context):
        print(f"[Server] SayHello called with name='{request.name}'")
        return greeting_pb2.HelloReply(message=f"Hello, {request.name}!")

    def SayGoodbye(self, request, context):
        print(f"[Server] SayGoodbye called with name='{request.name}'")
        return greeting_pb2.GoodbyeReply(message=f"Goodbye, {request.name}!")


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    greeting_pb2_grpc.add_GreeterServicer_to_server(GreeterServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("[Server] Listening on port 50051...")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
