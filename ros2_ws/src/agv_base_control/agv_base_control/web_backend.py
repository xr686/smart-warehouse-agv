import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import subprocess
import signal
import os

class WebBackendNode(Node):
    def __init__(self):
        super().__init__('web_backend_node')
        # 监听来自网页的指令
        self.sub = self.create_subscription(String, '/web_cmd', self.cmd_callback, 10)
        self.current_process = None
        self.declare_parameter('map_file', '')
        self.get_logger().info("🌐 Web后端中枢节点已启动，等待网页指令...")

    def cmd_callback(self, msg):
        cmd = msg.data
        self.get_logger().info(f"收到前端指令: {cmd}")

        if cmd == 'create_map':
            self.stop_current()
            self.get_logger().info("正在启动建图程序...")
            self.current_process = subprocess.Popen(['ros2', 'launch', 'agv_slam', 'cartographer.launch.py'])
            
        elif cmd == 'load_map':
            self.stop_current()
            self.get_logger().info("正在启动Nav2自动导航...")
            # 地图文件名可用 ROS 参数 map_file 或环境变量 AGV_MAP 覆盖，
            # 默认与 scripts/navigation.sh 保持一致（v4）
            ws = os.environ.get('AGV_WS', os.path.expanduser('~/agv_ws'))
            map_file = self.get_parameter('map_file').value or os.environ.get('AGV_MAP', 'my_room_map_v4.yaml')
            map_path = os.path.join(ws, 'src', 'agv_slam', 'config', map_file)
            if not os.path.isfile(map_path):
                self.get_logger().error(f"地图不存在: {map_path}，已取消启动导航")
                return
            self.current_process = subprocess.Popen(['ros2', 'launch', 'nav2_bringup', 'bringup_launch.py', 'use_sim_time:=False', f'map:={map_path}'])
            
        elif cmd == 'stop_all':
            self.stop_current()
            self.get_logger().info("已终止所有后台导航/建图任务。")

    def stop_current(self):
        # 杀掉当前正在运行的后台终端进程
        if self.current_process:
            self.current_process.send_signal(signal.SIGINT)
            self.current_process.wait()
            self.current_process = None

def main(args=None):
    rclpy.init(args=args)
    node = WebBackendNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()



