import grpc
import greeting_pb2
import greeting_pb2_grpc


def run(name: str = "World"):
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = greeting_pb2_grpc.GreeterStub(channel)

        hello_response = stub.SayHello(greeting_pb2.HelloRequest(name=name))
        print(f"[Client] SayHello response: {hello_response.message}")

        goodbye_response = stub.SayGoodbye(greeting_pb2.GoodbyeRequest(name=name))
        print(f"[Client] SayGoodbye response: {goodbye_response.message}")


if __name__ == "__main__":
    run("Test User")
