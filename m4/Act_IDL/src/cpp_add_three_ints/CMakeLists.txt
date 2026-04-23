cmake_minimum_required(VERSION 3.8)
project(cpp_add_three_ints)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(interfaces REQUIRED)

add_executable(cpp_server src/add_three_ints_server.cpp)
ament_target_dependencies(cpp_server rclcpp interfaces)

add_executable(cpp_client src/add_three_ints_client.cpp)
ament_target_dependencies(cpp_client rclcpp interfaces)

install(TARGETS
  cpp_server
  cpp_client
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()