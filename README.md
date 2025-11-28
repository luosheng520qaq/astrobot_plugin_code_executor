# AstrBot代码执行器插件 (Super Code Executor) - 全能小狐狸汐林

![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg) ![Python Version](https://img.shields.io/badge/python-3.10%2B-orange.svg) ![Plugin Version](https://img.shields.io/badge/version-2.5.0-brightgreen) ![Framework](https://img.shields.io/badge/framework-AstrBot-D72C4D)

⚠️⚠️⚠️ **安全警告** ⚠️⚠️⚠️

```diff
+=======================================================+
|  ██████╗ █████╗ ███████╗███████╗██████╗ ██╗███████╗   |
| ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██║██╔════╝   |
| ██║     ███████║█████╗  █████╗  ██████╔╝██║███████╗   |
| ██║     ██╔══██║██╔══╝  ██╔══╝  ██╔══██╗██║╚════██║   |
| ╚██████╗██║  ██║██║     ███████╗██║  ██║██║███████║   |
|  ╚═════╝╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝╚═╝╚══════╝   |
+=======================================================+
```

## 🔐 安全架构与风险

**作为开发者我已经完成的安全措施**
1. 代码执行验证管理员权限
2. 代码每次执行存档

**必须满足以下至少一项安全措施：**
1. **会话隔离**：启用AstrBot的会话隔离功能，确保不同会话间的执行环境完全独立
2. **群员识别**：启用AstrBot的群员识别系统，严格区分管理员/普通用户权限

**强烈建议同时采取以下防护措施：**
- 在虚拟机或容器环境中运行AstrBot
- 使用专用低权限系统账户
- 定期备份关键数据

‼️ **此插件权限极大，有一定安全风险。**
- 没有沙盒，代码拥有与运行用户相同的系统权限。
- 一个错误或恶意指令可能导致严重破坏（如删除系统文件、覆盖关键数据等）。
- 请仅在完全私有、可信环境中运行本插件，不要暴露在公共网络或不受信任用户面前。

```diff
- 高危操作示例（绝对禁止）：
  • rm -rf / 或等效Python代码
  • 覆盖系统关键文件
  • 下载执行未知脚本
  • 修改系统环境变量
  • 创建计划任务/开机自启
+ 安全建议：
  • 定期检查插件生成的代码
  • 设置文件操作白名单
  • 启用操作日志审计
  • 使用--restrict标志运行
```

---

# ✨ 插件功能总览

- **无限制代码执行**：执行任意Python代码（限制管理员可用）。
- **完全文件系统访问**：可在所有盘符自由创建、读取、修改、删除文件和目录。
- **智能文件发送**：自动检测并发送新生成文件，或指定任意路径文件发送。
- **🖼️ 图片处理功能**：自动提取消息中的图片URL，支持图片下载、处理、分析等操作。
- **丰富预装库**：内置40+常用库，涵盖数据科学、机器学习、图像处理、数据库、可视化、NLP等。
- **自动化图表生成**：matplotlib绘图后自动保存并发送图片。
- **执行历史记录系统**：每次代码执行自动记录到SQLite数据库，含详细信息、性能统计、文件追踪。
- **美观WebUI界面**：现代化响应式设计，支持统计、搜索、分页、详情查看。
- **强大搜索与筛选**：支持关键词、用户、状态、组合筛选。
- **分页浏览**：智能分页与页码导航。

---


# 建议辅助安装的插件：
- [AstrBot文本转图片插件](https://github.com/luosheng520qaq/astrbot_plugin_nobrowser_markdown_to_pic)
- [AstrBot消息合并插件](https://github.com/FreeDivers/astrbot_plugin_combine-messages) *（为代码执行器添加文件事件支持）*

# 🚀 安装与启动

1. 下载 `code_executor_plugin.py` 文件（或重命名后的插件文件）。
2. 放入 AstrBot 插件目录（通常为 `<AstrBot根目录>/data/plugins/`）。
3. 安装依赖包：

```bash
pip install fastapi uvicorn[standard] jinja2 aiosqlite
```

4. 重启 AstrBot。
5. 插件加载时自动初始化数据库并启动WebUI（默认端口22334）。
6. 通过浏览器访问 http://localhost:22334 查看历史记录界面。

---

# ⚙️ 配置说明

插件关键行为通过 `config.json` 配置，首次运行后在插件数据目录生成。

**主要配置项：**

```json
{
  "timeout_seconds": 90,
  "max_output_length": 3000,
  "enable_plots": true,
  "output_directory": "D:/ai_outputs",
  "enable_webui": false,
  "webui_port": 22334,
  "enable_lagrange_adapter": false,
  "lagrange_api_port": 8083,
  "enable_local_route_sending": false,
  "lagrange_host": "127.0.0.1",
  "local_route_host": "localhost"
}
```

- `timeout_seconds`：代码执行超时时间（秒）
- `max_output_length`：输出结果最大长度
- `enable_plots`：是否启用图表生成
- `output_directory`：默认工作目录（留空则使用插件内置路径，Docker用户可尝试填写 /Astrbot/data 或 /data）
- `enable_webui`：是否启用WebUI服务（默认关闭，避免端口冲突）
- `webui_port`：WebUI服务端口（可自定义，避免端口冲突）
- `enable_lagrange_adapter`：启用Lagrange适配器（默认关闭）
- `lagrange_api_port`：Lagrange API服务端口（默认8083）
- `enable_local_route_sending`：启用本地路由发送（默认关闭，适用于AstrBot和发送框架不在同一网络的情况）
- `lagrange_host`：Lagrange服务器IP地址（默认127.0.0.1，如果AstrBot和Lagrange不在同一主机请填写Lagrange的IP地址）
- `local_route_host`：本地路由发送主机IP地址（默认localhost，如需支持Docker或跨网络访问，请填写局域网IP地址）

**部分行为可通过源码 `__init__` 方法调整。**

## Lagrange适配器配置

当使用Lagrange作为机器人框架时，可启用Lagrange适配器来优化文件上传功能：

1. 设置 `enable_lagrange_adapter` 为 `true`
2. 确保Lagrange API服务运行在指定端口（默认8083）
3. 插件将自动根据聊天类型选择合适的上传接口：
   - **私聊**：调用 `/upload_private_file` 接口
   - **群聊**：调用 `/upload_group_file` 接口

**注意**：Lagrange适配器仅在启用时生效，默认情况下使用AstrBot原生文件发送方式。

---

# 📖 使用方法

## 1. 生成新文件（默认方式）

当任务需创建新文件（如报告、数据表、图表），AI会将文件保存在 `SAVE_DIR` 目录，插件自动检测并发送。

```python
import pandas as pd
import os

data = {'产品': ['A', 'B', 'C'], '销量': [100, 150, 80]}
df = pd.DataFrame(data)
save_path = os.path.join(SAVE_DIR, 'sales_report.xlsx')
df.to_excel(save_path, index=False)
print(f"销售报告已生成: {save_path}")
```

## 2. 发送本地已有文件（高级方式）

让AI将文件完整路径添加到 `FILES_TO_SEND` 列表即可发送任意位置文件。

```python
import os
file_path = "D:/marketing/quarterly_review.pptx"
if os.path.exists(file_path):
    FILES_TO_SEND.append(file_path)
    print(f"已准备发送文件: {file_path}")
else:
    print(f"错误: 文件未找到 at {file_path}")
```

## 3. 🖼️ 图片处理功能（新增）

插件会自动提取用户消息中的图片URL，并将其注入到 `img_url` 变量中供代码使用。

```python
# img_url 变量已自动注入，包含当前消息中的所有图片URL
if img_url:
    import requests
    from PIL import Image
    import io
    
    # 下载第一张图片
    response = requests.get(img_url[0])
    image = Image.open(io.BytesIO(response.content))
    
    # 获取图片信息
    print(f"图片尺寸: {image.size}")
    print(f"图片格式: {image.format}")
    print(f"图片模式: {image.mode}")
    
    # 处理图片（例如：调整大小并添加滤镜）
    resized_image = image.resize((800, 600))
    
    # 保存处理后的图片
    output_path = os.path.join(SAVE_DIR, 'processed_image.jpg')
    resized_image.save(output_path, quality=95)
    print(f"图片处理完成，已保存到: {output_path}")
else:
    print("当前消息中没有图片")
```

**图片处理功能特点**：
- 自动检测并提取消息中的图片URL
- 支持多张图片同时处理
- 可进行格式转换、尺寸调整、滤镜处理等操作
- 处理后的图片自动保存并发送

---

# 🗄️ 执行历史与WebUI

- 所有执行历史自动记录于 `execution_history.db`（SQLite）。
- WebUI支持统计面板、搜索筛选、分页浏览、详情查看。
- 支持通过配置文件自定义端口。

## 数据库表结构

```sql
CREATE TABLE execution_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id TEXT NOT NULL,
    sender_name TEXT NOT NULL,
    code TEXT NOT NULL,
    description TEXT,
    success BOOLEAN NOT NULL,
    output TEXT,
    error_msg TEXT,
    file_paths TEXT,
    execution_time REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

# 📦 依赖包

- fastapi
- uvicorn[standard]
- jinja2
- aiosqlite

---

# 🔧 技术实现

- **ExecutionHistoryDB** (`database.py`)：异步数据库操作，分页与统计。
- **CodeExecutorWebUI** (`webui.py`)：FastAPI+Jinja2，RESTful API与HTML界面。
- **CodeExecutorPlugin** (`main.py`)：主插件类，集成数据库与WebUI。
- 所有数据库操作异步，不阻塞主线程。
- WebUI后台运行，不影响主功能。
- 完善异常捕获与日志。

---

# 🛡️ 安全与故障排查

- WebUI服务绑定 `0.0.0.0`，支持局域网访问。
- 建议生产环境配置防火墙。
- 数据库文件受系统权限保护。
- 所有用户输入均HTML转义。

## 常见问题

1. **WebUI无法访问**：检查端口占用、插件日志、或防火墙。
2. **数据库错误**：检查写入权限、文件损坏、重启插件。
3. **记录缺失**：检查数据库连接、日志、执行权限。

## 日志查看
- 详见AstroBot日志系统，包括数据库、WebUI、错误异常。

---

# 🎯 使用建议

- 定期清理过期记录，避免数据库过大。
- 如端口被占用请修改配置。
- 外网访问请加强安全措施。
- 可通过WebUI监控性能与成功率。

---

# 📞 技术支持

如遇问题请：
1. 查看插件日志
2. 检查配置文件
3. 确认依赖包已安装
4. 联系作者QQ：723926109

---

**版本**: 2.5.0  
**作者**: Xican  
**更新日期**: 2025年10月26日

## 更新日志

### v2.5.0 - 修复图表中文显示问题
- 解决图表中中文显示乱码问题
- 修复文件空发送问题

### v2.4.0 - 代码执行错误处理增强
- 新增错误分析与修复建议功能
- 支持根据错误信息自动生成修复代码
- 新增配置项：`enable_error_analysis` 用于开启/关闭错误分析功能


### v2.3.0 - 图片处理功能增强 (2025-08-03)
- 🖼️ **新增图片处理功能**：自动提取消息中的图片URL并注入到执行环境
- **新增方法**：`get_image_urls_from_message` 用于从消息链中提取图片URL
- **变量注入**：在代码执行环境中自动提供 `img_url` 变量（图片URL列表）
- **增强提示词**：为AI提供详细的图片处理使用说明和示例
- **向后兼容**：不影响现有功能，纯增强性更新
- **适用场景**：图片下载、格式转换、尺寸调整、滤镜处理、信息提取等

### v2.2.1--fix (2025-07-31)
- 修复napcat和astrbot不在同一环境的文件发送问题

### v2.2.0--webui (2025-07-22)
- 新增Lagrange适配器支持
- 支持通过Lagrange API上传私聊和群聊文件
- 新增配置项：`enable_lagrange_adapter` 和 `lagrange_api_port`
- 优化文件上传逻辑，支持多种机器人框架