# AGV 操作手册（整理版）

> 整理自项目原始操作笔记，全部终端命令原样保留。原稿另存于 [operation-manual-raw.md](operation-manual-raw.md)。
>
> 约定：工作区位于 `~/agv_ws`；底盘串口为 `/dev/ttyACM0`（USB 转 RS485 → DDSM115 电机），雷达串口为 `/dev/ttyACM1`（N10P 适配板）。每个终端都要先 `source ~/agv_ws/install/setup.bash`。

## 目录

1. [建图](#一建图cartographer)
2. [SLAM 导航](#二slam-导航nav2)
3. [最终版（一键多进程 + Web 远程）](#三最终版)
4. [常见问题](#四常见问题)

---

## 一、建图（Cartographer）

### 终端 1（底盘驱动）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
sudo chmod 777 /dev/ttyACM0
```

```bash
ros2 run agv_base_control base_node
```

### 终端 2（雷达驱动）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
sudo chmod 777 /dev/ttyACM1
```

```bash
ros2 launch lslidar_driver lsn10p_launch.py
```

### 终端 3（雷达 TF）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
ros2 run tf2_ros static_transform_publisher 0 0 0.2 0 0 0 base_link laser
```

### 终端 4（Cartographer 建图）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
ros2 launch agv_slam cartographer.launch.py
```

### 终端 5（键盘遥控）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### 终端 6（启动普通 RViz2）

```bash
rviz2
```

### 终端 7（保存地图）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
cd ~/agv_ws/src/agv_slam/config
```

（假设保存的地图名为 "my_room_map_v3"）

```bash
ros2 run nav2_map_server map_saver_cli -f my_room_map_v3 --fmt png
```

---

## 二、SLAM 导航（Nav2）

### 终端 1（底盘驱动）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
sudo chmod 777 /dev/ttyACM0
```

```bash
ros2 run agv_base_control base_node
```

### 终端 2（雷达驱动）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
sudo chmod 777 /dev/ttyACM1
```

```bash
ros2 launch lslidar_driver lsn10p_launch.py
```

### 终端 3（雷达 TF）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
ros2 run tf2_ros static_transform_publisher 0 0 0.2 0 0 0 base_link laser
```

### 终端 4（脚印 TF 补丁）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 base_link base_footprint
```

### 终端 5（加载地图启动 Nav2）

```bash
source ~/agv_ws/install/setup.bash
```

（假设使用的地图名为 "my_room_map_v2"）

```bash
source ~/agv_ws/install/setup.bash
ros2 launch nav2_bringup bringup_launch.py use_sim_time:=False map:=~/agv_ws/src/agv_slam/config/my_room_map_v2.yaml
```

### 终端 6（启动导航专用 RViz2）

```bash
source ~/agv_ws/install/setup.bash
```

```bash
ros2 run rviz2 rviz2 -d $(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/rviz/nav2_default_view.rviz
```

---

## 三、最终版

三条聚合命令，按顺序执行（多进程后台并行）：

### 1. 底盘 + TF + rosbridge（Web 前端指令通道）

```bash
source ~/agv_ws/install/setup.bash
ros2 run agv_base_control base_node & ros2 run tf2_ros static_transform_publisher 0 0 0.2 0 0 0 base_link laser & ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 base_link base_footprint & ros2 launch rosbridge_server rosbridge_websocket_launch.xml
```

### 2. 雷达 + Nav2（加载最新地图 v4）

```bash
source ~/agv_ws/install/setup.bash
ros2 launch lslidar_driver lsn10p_launch.py & ros2 launch nav2_bringup bringup_launch.py use_sim_time:=False map:=~/agv_ws/src/agv_slam/config/my_room_map_v4.yaml
```

### 3. 导航 RViz2 + VNC + noVNC（Web 前端可视化通道）

```bash
source ~/agv_ws/install/setup.bash
ros2 run rviz2 rviz2 -d $(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/rviz/nav2_default_view.rviz

x11vnc -display :1 -auth ~/.Xauthority -nopw -forever -shared -bg

/usr/share/novnc/utils/launch.sh --vnc localhost:5901 --listen 6080
```

之后浏览器打开 `frontend/index.html`，将页面内 IP 配置为本机地址即可使用 Web HMI（遥控 ws://NX_IP:9090，监控 http://NX_IP:6080/vnc.html）。

---

## 四、常见问题

- **串口权限**：`sudo chmod 777 /dev/ttyACM0 /dev/ttyACM1` 重启后失效，需重新执行（或将用户加入 `dialout` 组）。
- **地图版本**：`web_backend.py` 中 `load_map` 硬编码的是 `my_room_map_v2`；「最终版」命令加载的是 `my_room_map_v4`。按实际使用的地图改 `map:=` 路径。
- **地图图像格式**：v1/v2 为 `.pgm`，v3/v4 保存时用了 `--fmt png` 为 `.png`，yaml 中 `image:` 字段与之对应。
- **TF 树**：需要 `base_link → laser`（雷达高 0.2m）与 `base_link → base_footprint` 两条静态 TF，缺一 Nav2 会报 TF 错误。
