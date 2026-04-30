import grpc
sys.path.insert(1, './protos')
import rpc_demo_pb2
import rpc_demo_pb2_grpc

def run(num1, num2):
    with grpc.insecure_channel('localhost:7042') as channel:
        stub = rpc_demo_pb2_grpc.RPCDemoStub(channel)
        response = stub.GetImageResult()
    print(f"Result: {response.result}")

if __name__ == '__main__':
    # Get user Input 
    #num1 = int(input("Please input num1: "))
    #num2 = int(input("Please input num2: "))
    run(0, 0)