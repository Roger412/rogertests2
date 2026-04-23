#include <chrono>
#include <cstdlib>
#include <memory>
#include <iostream>

#include "rclcpp/rclcpp.hpp"
#include "interfaces/srv/add_three_ints.hpp"

using namespace std::chrono_literals;

class AddThreeIntsClient : public rclcpp::Node
{
public:
  AddThreeIntsClient()
  : Node("cpp_add_three_ints_client")
  {
    client_ = this->create_client<interfaces::srv::AddThreeInts>("add_three_ints");
  }

  void send_request(int64_t a, int64_t b, int64_t c)
  {
    while (!client_->wait_for_service(1s)) {
      if (!rclcpp::ok()) {
        RCLCPP_ERROR(this->get_logger(), "Interrupted while waiting for the service.");
        return;
      }
      RCLCPP_INFO(this->get_logger(), "Service not available, waiting again...");
    }

    auto request = std::make_shared<interfaces::srv::AddThreeInts::Request>();
    request->a = a;
    request->b = b;
    request->c = c;

    auto future = client_->async_send_request(request);

    auto result = rclcpp::spin_until_future_complete(
      this->get_node_base_interface(),
      future
    );

    if (result == rclcpp::FutureReturnCode::SUCCESS) {
      RCLCPP_INFO(
        this->get_logger(),
        "Result: %ld + %ld + %ld = %ld",
        a, b, c, future.get()->sum
      );
    } else {
      RCLCPP_ERROR(this->get_logger(), "Failed to call service add_three_ints");
    }
  }

private:
  rclcpp::Client<interfaces::srv::AddThreeInts>::SharedPtr client_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);

  if (argc != 4) {
    std::cerr << "Usage: ros2 run cpp_add_three_ints cpp_client <a> <b> <c>" << std::endl;
    return 1;
  }

  auto node = std::make_shared<AddThreeIntsClient>();

  int64_t a = std::atoll(argv[1]);
  int64_t b = std::atoll(argv[2]);
  int64_t c = std::atoll(argv[3]);

  node->send_request(a, b, c);

  rclcpp::shutdown();
  return 0;
}
