import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('agv_slam')
    
    return LaunchDescription([
        # 启动 Cartographer 核心节点
        Node(
            package='cartographer_ros',
            executable='cartographer_node',
            name='cartographer_node',
            output='screen',
            arguments=[
                '-configuration_directory', os.path.join(pkg_share, 'config'),
                '-configuration_basename', 'cartographer_2d.lua'
            ],
        ),
        # 启动占据栅格地图发布节点 (注意这里的 executable 名字已修改)
        Node(
            package='cartographer_ros',
            executable='occupancy_grid_node', 
            name='occupancy_grid_node',
            output='screen',
            arguments=['-resolution', '0.05', '-publish_period_sec', '1.0']
        )
    ])
