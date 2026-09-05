# AGV 操作笔记（原始版）

## 建图

### 终端1（底盘驱动）

```
source ~/agv_ws/install/setup.bash
```

```
sudo chmod 777 /dev/ttyACM0
```

```
ros2 run agv_base_control base_node
```

### 终端2（雷达驱动）

```
source ~/agv_ws/install/setup.bash
```

```
sudo chmod 777 /dev/ttyACM1
```

```
ros2 launch lslidar_driver lsn10p_launch.py
```

### 终端3（雷达TF）

```
source ~/agv_ws/install/setup.bash
```

```
ros2 run tf2_ros static_transform_publisher 0 0 0.2 0 0 0 base_link laser
```

### 终端4	(Cartographer 建图)

```
source ~/agv_ws/install/setup.bash
```

```
ros2 launch agv_slam cartographer.launch.py
```

### 终端5	(键盘遥控)

```
source ~/agv_ws/install/setup.bash
```

```
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

### 终端6	(启动普通 RViz2)

```
rviz2
```

### 终端7	(保存地图)

```
source ~/agv_ws/install/setup.bash
```

```
cd ~/agv_ws/src/agv_slam/config
```

（假设保存的地图名为“my_room_map_v3”）

```
ros2 run nav2_map_server map_saver_cli -f my_room_map_v3 --fmt png
```

## SLAM导航

### 终端1	（底盘驱动）

```
source ~/agv_ws/install/setup.bash
```

```
sudo chmod 777 /dev/ttyACM0
```

```
ros2 run agv_base_control base_node
```

### 终端2	（雷达驱动）

```
source ~/agv_ws/install/setup.bash
```

```
sudo chmod 777 /dev/ttyACM1
```

```
ros2 launch lslidar_driver lsn10p_launch.py
```

### 终端3	（雷达TF）

```
source ~/agv_ws/install/setup.bash
```

```
ros2 run tf2_ros static_transform_publisher 0 0 0.2 0 0 0 base_link laser
```

### 终端4	（脚印 TF 补丁）

```
source ~/agv_ws/install/setup.bash
```

```
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 base_link base_footprint
```

### 终端5	（加载地图启动 Nav2）

```
source ~/agv_ws/install/setup.bash
```

（假设使用的地图名为“my_room_map_v2”）

```
source ~/agv_ws/install/setup.bash
ros2 launch nav2_bringup bringup_launch.py use_sim_time:=False map:=~/agv_ws/src/agv_slam/config/my_room_map_v2.yaml
```

### 终端6	（启动导航专用 RViz2）

```
source ~/agv_ws/install/setup.bash
```

```
ros2 run rviz2 rviz2 -d $(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/rviz/nav2_default_view.rviz
```

## 最终版

```
source ~/agv_ws/install/setup.bash
ros2 run agv_base_control base_node & ros2 run tf2_ros static_transform_publisher 0 0 0.2 0 0 0 base_link laser & ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 base_link base_footprint & ros2 launch rosbridge_server rosbridge_websocket_launch.xml

source ~/agv_ws/install/setup.bash
ros2 launch lslidar_driver lsn10p_launch.py & ros2 launch nav2_bringup bringup_launch.py use_sim_time:=False map:=~/agv_ws/src/agv_slam/config/my_room_map_v4.yaml

source ~/agv_ws/install/setup.bash
ros2 run rviz2 rviz2 -d $(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/rviz/nav2_default_view.rviz

x11vnc -display :1 -auth ~/.Xauthority -nopw -forever -shared -bg

/usr/share/novnc/utils/launch.sh --vnc localhost:5901 --listen 6080
```

