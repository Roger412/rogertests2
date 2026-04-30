import signal
import threading
from concurrent import futures
import cv2
import base64
import numpy as np

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import grpc
import sys
sys.path.insert(1, './protos')
import rpc_demo_pb2
import rpc_demo_pb2_grpc

class RPCDemoImpl(rpc_demo_pb2_grpc.RPCDemoServicer):
    def __init__(self, node):
        self.node = node
        self.data = [0, 0, 0]
        self.img_compressed = None
        self.shape = None
        self.br = CvBridge()
        self.node.create_subscription(Float64MultiArray, '/object_position', self.update_data, 10)
        self.node.create_subscription(Image, '/image_result', self.update_image, 10)
        print("Initialized gRPC Server")

    def update_data(self, msg):
        self.data[0] = msg.data[0]
        self.data[1] = msg.data[1]
        self.data[2] = msg.data[2]
        #print(self.node.get_logger().info("Got data: " + str(self.data)))

    def update_image(self, msg):
        img_original = self.br.imgmsg_to_cv2(msg)
        self.shape = img_original.shape

        self.img_compressed = np.array(cv2.imencode('.jpg', img_original)[1]).tobytes()
        
        img_base64 = base64.b64encode(self.img_compressed)
        
        print("----")
        print("Memory size of original image in bytes:", img_original.size * img_original.itemsize)
        #file = open('original.bin', 'wb')
        #try:
        #    file.write(img_original)
        #finally:
        #    file.close()
            
        print("Memory size of compressed image in bytes:", len(self.img_compressed))
        #file = open('compressed.bin', 'wb')
        #try:
        #    file.write(self.img_compressed)
        #finally:
        #    file.close()

        print("Memory size of base64 image in bytes", len(img_base64))
        #file = open('base64.bin', 'wb')
        #try:
        #    file.write(img_base64)
        #finally:
        #    file.close()

        #print(self.img_compressed)
        #cv2.imshow('rec-img',self.img_compressed)
        #cv2.waitKey(1)
        #print(self.node.get_logger().info("Got data: " + str(self.data)))

    def GetMultCoords(self, request, context):
        print("    GetMultCoords Got call: " + context.peer())
        results = rpc_demo_pb2.MultCoords()
        results.values.append(self.data[0])
        results.values.append(self.data[1])
        results.values.append(self.data[2])
        return results

    def GetImageResult(self, request, context):
        print("    GetImageResult Got call: " + context.peer())
        results = rpc_demo_pb2.ImageResult()
        results.b64img = self.img_compressed
        results.width = self.shape[1]
        results.height = self.shape[0]
        return results

terminate = threading.Event()
def terminate_server(signum, frame):
    print("Got signal {}, {}".format(signum, frame))
    rclpy.shutdown()
    terminate.set()

def main(args=None):
    print("----ROS-gRPC-Wrapper----")
    signal.signal(signal.SIGINT, terminate_server)

    print("Starting ROS Node")
    rclpy.init(args=args)
    node = rclpy.create_node('object_position_wrapper')

    print("Starting gRPC Server")
    server_addr = "[::]:7042"
    service = RPCDemoImpl(node)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    rpc_demo_pb2_grpc.add_RPCDemoServicer_to_server(service, server)
    server.add_insecure_port(server_addr)
    server.start()
    print("gRPC Server listening on " + server_addr)

    print("Running ROS Node")
    executor = futures.ThreadPoolExecutor()
    executor.submit(lambda: rclpy.spin(node))
    
    terminate.wait()
    print("Stopping gRPC Server")
    server.stop(1).wait()
    print("Exited")
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()