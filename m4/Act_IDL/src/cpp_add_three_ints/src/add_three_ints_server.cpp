#include "rclcpp/rclcpp.hpp"
#include "interfaces/srv/add_three_ints.hpp"

using std::placeholders::_1;
using std::placeholders::_2;

class AddThreeIntsServer : public rclcpp::Node
{
public:
  AddThreeIntsServer()
  : Node("cpp_add_three_ints_server")
  {
    service_ = this->create_service<interfaces::srv::AddThreeInts>(
      "add_three_ints",
      std::bind(&AddThreeIntsServer::handle_service, this, _1, _2)
    );

    RCLCPP_INFO(this->get_logger(), "C++ AddThreeInts server is ready.");
  }

private:
  void handle_service(
    const std::shared_ptr<interfaces::srv::AddThreeInts::Request> request,
    std::shared_ptr<interfaces::srv::AddThreeInts::Response> response)
  {
    response->sum = request->a + request->b + request->c;

    RCLCPP_INFO(
      this->get_logger(),
      "Request received: a=%ld, b=%ld, c=%ld",
      request->a, request->b, request->c
    );

    RCLCPP_INFO(
      this->get_logger(),
      "Response sent: sum=%ld",
      response->sum
    );
  }

  rclcpp::Service<interfaces::srv::AddThreeInts>::SharedPtr service_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<AddThreeIntsServer>());
  rclcpp::shutdown();
  return 0;
}
