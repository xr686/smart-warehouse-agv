#!/usr/bin/env bash
# ============================================================================
# navigation.sh —— 一键拉起 Nav2 导航（最终版前两条聚合命令 + VNC 可选）
# 对应 docs/operation-manual.md「三、最终版」。
# 用法：
#   ./navigation.sh                # 底盘+TF+rosbridge / 雷达+Nav2（默认地图 v4）
#   MAP=my_room_map_v2.yaml ./navigation.sh   # 指定地图文件名
#   WITH_VNC=1 ./navigation.sh     # 额外启动 x11vnc + noVNC（Web 可视化通道）
# ============================================================================
set -u

WS="${AGV_WS:-$HOME/agv_ws}"
MAP_FILE="${MAP:-my_room_map_v4.yaml}"
MAP_PATH="$WS/src/agv_slam/config/$MAP_FILE"
source "$WS/install/setup.bash"

[ -f "$MAP_PATH" ] || { echo "[nav] 地图不存在: $MAP_PATH"; exit 1; }

echo "[nav] 放开串口权限..."
sudo chmod 777 /dev/ttyACM0 /dev/ttyACM1

echo "[nav] 组1：底盘驱动 + 双静态TF + rosbridge(ws://0.0.0.0:9090)..."
ros2 run agv_base_control base_node &
ros2 run tf2_ros static_transform_publisher 0 0 0.2 0 0 0 base_link laser &
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 base_link base_footprint &
ros2 launch rosbridge_server rosbridge_websocket_launch.xml &

echo "[nav] 组2：雷达驱动 + Nav2（地图: $MAP_PATH）..."
ros2 launch lslidar_driver lsn10p_launch.py &
ros2 launch nav2_bringup bringup_launch.py use_sim_time:=False map:="$MAP_PATH" &

if [ "${WITH_VNC:-0}" = "1" ]; then
  echo "[nav] 组3：x11vnc + noVNC(http://<本机IP>:6080/vnc.html)..."
  x11vnc -display :1 -auth ~/.Xauthority -nopw -forever -shared -bg
  /usr/share/novnc/utils/launch.sh --vnc localhost:5901 --listen 6080 &
fi

echo "[nav] 导航 RViz2 与前端页面请按需手动启动（见操作手册）。"
trap 'echo "[nav] 停止全部子进程..."; kill $(jobs -p) 2>/dev/null' INT TERM EXIT
wait
