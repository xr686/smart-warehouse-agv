# Node-RED 流（reCamera 边缘视觉安防）

本目录 `flows.json` 为实机（Seeed reCamera）导出的 Node-RED 流，共 **22 个节点**，是边缘视觉安防链路的完整逻辑编排。

## 流内容

- **SenseCraft SSCMA 推理节点**（`node-red-contrib-sscma` 0.3.6，运行在 reCamera 端）：camera → model → sscma 推理 → capture，本地 NPU 跑行人（person）检测
- **person 检测触发抓拍**：检测到行人入侵即触发 capture 存盘，构成历史抓拍库
- **3 个 HTTP API**（http in / http response / file in / function / exec 节点组成）：
  | API | 路径 | 用途 |
  |---|---|---|
  | Image List | `/api/images` | 返回抓拍图片列表 |
  | Latest Photo | `/api/latest` | 返回最新一张抓拍 |
  | Single Image | `/api/image` | 按文件名返回单张图片 |

这三个 API 正好对应 `frontend/index.html` 中历史入侵抓拍库的调用（`fetchAPI(ip,'/api/images')`、`/api/image?file=`），也是前端 8090 端口 WebSocket 视频流之外的 RESTful 数据通道。

## 导入方式

1. 浏览器打开 reCamera 上的 Node-RED 编辑器（通常 `http://192.168.42.1:1880`；reCamera 经 USB RNDIS 直连 Jetson NX，见 `hardware/BOM.md`）
2. 右上角菜单 → **Import** → 粘贴 `flows.json` 全部内容（或选择本文件）→ Import
3. 点 Deploy 部署；确认 SSCMA 节点已加载 person 检测模型
