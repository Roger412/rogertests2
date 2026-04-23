import time
import grpc
import sys

sys.path.insert(1, './protos')

from google.protobuf.empty_pb2 import Empty
import rpc_demo_pb2
import rpc_demo_pb2_grpc


def main():
    server_address = "localhost:7042"

    channel = grpc.insecure_channel(server_address)
    stub = rpc_demo_pb2_grpc.RPCDemoStub(channel)

    print(f"Connected to gRPC server at {server_address}")

    try:
        while True:
            request = Empty()
            response = stub.GetMultCoords(request)

            values = list(response.values)

            if len(values) >= 3:
                x, y, z = values[0], values[1], values[2]
                print(f"Received -> x={x:.3f}, y={y:.3f}, z={z:.3f}")
            else:
                print(f"Received: {values}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nClient stopped.")
    except grpc.RpcError as e:
        print(f"gRPC error: {e}")


if __name__ == "__main__":
    main()
