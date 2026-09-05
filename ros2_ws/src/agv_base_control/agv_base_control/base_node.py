import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
import serial
import crcmod.predefined
import math
import time
from tf2_ros import TransformBroadcaster

class AGVBaseNode(Node):
    def __init__(self):
        super().__init__('agv_base_node')

        # 1. 机器人真实物理参数（DDSM115 轮毂电机直径 115mm → 半径 0.0575m）
        self.declare_parameter('wheel_radius', 0.0575)
        self.declare_parameter('wheel_base', 0.287)
        self.wheel_radius = self.get_parameter('wheel_radius').value
        self.wheel_base = self.get_parameter('wheel_base').value

        # 2. 串口配置（可用 ROS 参数或环境变量覆盖，不再硬编码）
        self.declare_parameter('serial_port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 115200)
        # cmd_vel 超时保护：超过该秒数未收到新指令自动刹停（0 表示禁用）
        self.declare_parameter('cmd_vel_timeout', 0.5)
        self.port = self.get_parameter('serial_port').value
        self.baudrate = self.get_parameter('baudrate').value
        self.cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value
        self.serial = None
        self._connect_serial()

        self.crc8_func = crcmod.predefined.mkCrcFun('crc-8-maxim')
        
        # 3. 变量初始化
        self.target_left_rpm = 0
        self.target_right_rpm = 0
        
        # 里程计位姿累加值
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_th = 0.0
        self.last_time = self.get_clock().now()
        self.last_cmd_time = None
        
        # 4. ROS2 话题与 TF 广播器声明
        self.subscription = self.create_subscription(Twist, 'cmd_vel', self.cmd_vel_callback, 10)
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)
        
        # 5. 核心控制与读取循环 (20Hz)
        self.timer = self.create_timer(0.05, self.control_loop)

    def _connect_serial(self):
        """尝试打开串口；失败不退出，control_loop 里会周期重连"""
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.02)
            self.get_logger().info(f"成功连接到串口: {self.port}")
        except Exception as e:
            self.serial = None
            self.get_logger().error(f"串口连接失败: {e}（将每 2 秒自动重试）")

    def cmd_vel_callback(self, msg):
        """将 ROS2 的 Twist 速度指令转化为目标 RPM"""
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        self.last_cmd_time = time.time()
        
        v_left = linear_x - (angular_z * self.wheel_base / 2.0)
        v_right = linear_x + (angular_z * self.wheel_base / 2.0)
        
        self.target_left_rpm = int((v_left / (2 * math.pi * self.wheel_radius)) * 60)
        self.target_right_rpm = int((v_right / (2 * math.pi * self.wheel_radius)) * 60)

    def control_loop(self):
        """主循环：发命令 -> 读反馈 -> 算里程 -> 发布"""
        current_time = self.get_clock().now()

        # 串口掉线自动重连（拔插 USB 后无需重启节点）
        if self.serial is None:
            self._connect_serial()
            if self.serial is None:
                return

        # cmd_vel 超时保护：失联即刹停，防止前端断连后小车失控狂奔
        if (self.cmd_vel_timeout > 0 and self.last_cmd_time is not None
                and time.time() - self.last_cmd_time > self.cmd_vel_timeout
                and (self.target_left_rpm or self.target_right_rpm)):
            self.get_logger().warning("cmd_vel 超时，自动刹停")
            self.target_left_rpm = 0
            self.target_right_rpm = 0
        
        # 1. 同步轮询电机 1 (左轮)
        self.send_speed_command(1, self.target_left_rpm)
        actual_left_rpm = self.read_feedback(1)
        
        # 2. 同步轮询电机 2 (右轮)
        self.send_speed_command(2, -self.target_right_rpm) # 右轮电机反装
        actual_right_rpm = self.read_feedback(2)
        
        # 只有两个电机都成功读到数据，才更新里程计
        if actual_left_rpm is not None and actual_right_rpm is not None:
            # 右轮的真实RPM需要再反转回来用于计算
            actual_right_rpm = -actual_right_rpm
            
            # --- 正向运动学计算 ---
            # RPM 转 m/s
            v_left_actual = (actual_left_rpm / 60.0) * (2 * math.pi * self.wheel_radius)
            v_right_actual = (actual_right_rpm / 60.0) * (2 * math.pi * self.wheel_radius)
            
            # 底盘中心线速度与角速度
            vx = (v_right_actual + v_left_actual) / 2.0
            vth = (v_right_actual - v_left_actual) / self.wheel_base
            
            # 积分计算位姿 (dt: 两次循环的实际时间差)
            dt = (current_time - self.last_time).nanoseconds / 1e9
            
            delta_x = vx * math.cos(self.odom_th) * dt
            delta_y = vx * math.sin(self.odom_th) * dt
            delta_th = vth * dt
            
            self.odom_x += delta_x
            self.odom_y += delta_y
            self.odom_th += delta_th
            
            # 发布 Odom 和 TF
            self.publish_odometry(current_time, vx, vth)
            
        self.last_time = current_time

    def send_speed_command(self, motor_id, rpm):
        """发送十六进制速度指令"""
        if self.serial is None:
            return
        rpm = max(-330, min(330, rpm))
        if rpm < 0:
            rpm = (1 << 16) + rpm
            
        high_byte = (rpm >> 8) & 0xFF
        low_byte = rpm & 0xFF
        data = [motor_id, 0x64, high_byte, low_byte, 0x00, 0x00, 0x00, 0x00, 0x00]
        data.append(self.crc8_func(bytes(data)))
        
        # 清空接收缓冲区，防止读到上次残留的数据
        self.serial.reset_input_buffer() 
        self.serial.write(bytes(data))

    def read_feedback(self, expected_id):
        """读取10字节返回帧并解析速度(带异常保护)"""
        if self.serial is None:
            return None
        start_time = time.time()
        buffer = []
        while time.time() - start_time < 0.02:
            try:
                if self.serial.in_waiting:
                    b = self.serial.read(1)[0]
                    if not buffer and b != expected_id:
                        continue 
                    buffer.append(b)
                    if len(buffer) == 10:
                        crc = self.crc8_func(bytes(buffer[:9]))
                        if crc == buffer[9]:
                            rpm = (buffer[4] << 8) | buffer[5]
                            if rpm > 32767:
                                rpm -= 65536
                            return rpm
                        else:
                            return None
            except Exception as e:
                # 就算串口被拔掉或空转报错，也只打印警告，绝不崩溃！
                self.get_logger().warning(f"串口读取异常: {e}")
                try:
                    self.serial.close()
                except Exception:
                    pass
                self.serial = None  # 下个周期 control_loop 自动重连
                return None
        return None

    def publish_odometry(self, current_time, vx, vth):
        """组装并发布 TF 树与 Odometry 话题"""
        # 欧拉角转四元数 (航向角)
        qz = math.sin(self.odom_th / 2.0)
        qw = math.cos(self.odom_th / 2.0)
        
        # 1. 广播 TF: odom -> base_link
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.odom_x
        t.transform.translation.y = self.odom_y
        t.transform.translation.z = 0.0
        t.transform.rotation.x = 0.0
        t.transform.rotation.y = 0.0
        t.transform.rotation.z = qz
        t.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(t)
        
        # 2. 发布 Odometry 数据
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.odom_x
        odom.pose.pose.position.y = self.odom_y
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = vx
        odom.twist.twist.angular.z = vth
        self.odom_pub.publish(odom)

def main(args=None):
    rclpy.init(args=args)
    node = AGVBaseNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
