#!/usr/bin/env bash
# ============================================================================
# mapping.sh —— 一键拉起 Cartographer 建图（多进程后台并行）
# 对应 docs/operation-manual.md「一、建图」的 7 个终端，合并为一条脚本。
# RViz2 与键盘遥控建议另开终端手动运行（见手册终端 5/6）；保存地图见终端 7。
# ============================================================================
set -u

WS="${AGV_WS:-$HOME/agv_ws}"
source "$WS/install/setup.bash"

echo "[mapping] 放开串口权限..."
sudo chmod 777 /dev/ttyACM0 /dev/ttyACM1

echo "[mapping] 启动：底盘驱动 + 雷达驱动 + 雷达TF + Cartographer..."
ros2 run agv_base_control base_node &
ros2 run tf2_ros static_transform_publisher 0 0 0.2 0 0 0 base_link laser &
ros2 launch lslidar_driver lsn10p_launch.py &
ros2 launch agv_slam cartographer.launch.py &

trap 'echo "[mapping] 停止全部子进程..."; kill $(jobs -p) 2>/dev/null' INT TERM EXIT
wait
