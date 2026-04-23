#!/usr/bin/env python3

import sys

import rclpy
from rclpy.node import Node

from interfaces.srv import AddThreeInts


class AddThreeIntsClient(Node):
    def __init__(self):
        super().__init__('add_three_ints_client')

        self.client = self.create_client(AddThreeInts, 'add_three_ints')

        while not self.client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Service not available, waiting again...')

    def send_request(self, a: int, b: int, c: int):
        request = AddThreeInts.Request()
        request.a = a
        request.b = b
        request.c = c

        future = self.client.call_async(request)
        return future


def main(args=None):
    rclpy.init(args=args)

    if len(sys.argv) != 4:
        print('Usage: ros2 run py_add_three_ints client <a> <b> <c>')
        return

    a = int(sys.argv[1])
    b = int(sys.argv[2])
    c = int(sys.argv[3])

    node = AddThreeIntsClient()
    future = node.send_request(a, b, c)

    rclpy.spin_until_future_complete(node, future)

    if future.result() is not None:
        response = future.result()
        node.get_logger().info(
            f'Result: {a} + {b} + {c} = {response.sum}'
        )
    else:
        node.get_logger().error(
            f'Service call failed: {future.exception()}'
        )

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()