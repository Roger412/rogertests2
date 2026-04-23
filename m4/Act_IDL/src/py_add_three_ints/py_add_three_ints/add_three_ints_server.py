#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from interfaces.srv import AddThreeInts


class AddThreeIntsServer(Node):
    def __init__(self):
        super().__init__('add_three_ints_server')

        self.service = self.create_service(
            AddThreeInts,
            'add_three_ints',
            self.handle_add_three_ints
        )

        self.get_logger().info('AddThreeInts server is ready.')

    def handle_add_three_ints(self, request, response):
        response.sum = request.a + request.b + request.c

        self.get_logger().info(
            f'Request received: a={request.a}, b={request.b}, c={request.c}'
        )
        self.get_logger().info(
            f'Response sent: sum={response.sum}'
        )

        return response


def main(args=None):
    rclpy.init(args=args)
    node = AddThreeIntsServer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()