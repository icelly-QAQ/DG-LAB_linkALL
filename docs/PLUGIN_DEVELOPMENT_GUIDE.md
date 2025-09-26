# DG-LAB 插件系统开发指南

本文档详细介绍了DG-LAB项目的插件系统，帮助开发者创建和集成自定义插件。

## 1. 插件系统概述

插件系统采用了现代化的装饰器驱动架构，提供更简洁的API、完善的异步支持和更灵活的事件处理机制。该系统具有以下优势：

- 使用Python装饰器定义插件信息和功能，简化开发流程
- 完整的异步支持，允许插件执行非阻塞操作
- 统一的事件驱动架构，使插件能够响应各种系统事件
- 内置设置管理系统，简化插件配置
- 完善的类型提示，提升开发体验

## 2. 插件基本结构

每个插件应该遵循以下基本结构：

```
plugins/
├── 插件名称/
│   ├── __init__.py        # 插件初始化文件
│   └── 插件名称.py         # 插件主代码文件
```

## 3. 创建第一个插件

### 3.1 基本插件示例

下面是一个最简单的插件示例：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示例插件"""
import asyncio
from src.plugin_system.decorators import plugin
from src.plugin_system.plugin import Plugin
from src.dglab_controller import DGLabController
from src.command_types import Channel
import logging

logger = logging.getLogger(__name__)

@plugin(
    name="示例插件",
    description="示例插件描述：一个让a通道每隔5秒电你5秒",
    version="1.0.0",
    author="icelly_QAQ",
    is_game_plugin=True
)
class ArkForDGLAB(Plugin):
    """示例插件"""
    def initialize(self):
        """初始化插件资源
        
        参数:
            controller: Controller实例，用于与设备交互
        """
        self.controller = DGLabController
        self.task = None  # 定时任务
        logger.info(f"插件 {self.name} 已初始化")
        return True
    
    def shutdown(self):
        """关闭插件，清理资源"""
        # 停止定时任务
        if self.task and not self.task.done():
            self.task.cancel()
        logger.info(f"插件 {self.name} 已关闭")
    
    def on_enable(self):
        """插件启用时调用"""
        # 启动定时任务
        if self.controller:
            self.task = asyncio.create_task(self.strength_cycle())
        logger.info(f"插件 {self.name} 已启用")
    
    def on_disable(self):
        """插件禁用时调用"""
        # 停止定时任务
        if self.task and not self.task.done():
            self.task.cancel()
        logger.info(f"插件 {self.name} 已禁用")
    
    async def strength_cycle(self):
        """强度循环任务：每5秒将A通道强度设置为30，5秒后设置为5"""
        try:
            while True:
                # 设置A通道强度为30
                if self.controller and hasattr(self.controller, 'set_strength'):
                    await self.set_strength(Channel.A, 30)
                    logger.info("设置A通道强度为30")
                
                # 等待5秒
                await asyncio.sleep(5)
                
                # 设置A通道强度为5
                if self.controller and hasattr(self.controller, 'set_strength'):
                    await self.set_strength(Channel.A, 5)
                    logger.info("设置A通道强度为5")
                
                # 等待5秒
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            logger.info("强度循环任务已取消")
        except Exception as e:
            logger.error(f"强度循环任务出错: {e}")
    
    def get_config_widget(self):
        """获取插件配置界面组件
        
        返回:
            QWidget或None: 插件配置界面组件，如果没有配置项则返回None
        """
        return None
```

### 3.2 插件初始化文件

在插件目录中创建`__init__.py`文件：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件初始化文件"""
from .插件名称 import PluginExample

# 必须提供一个名为plugin_class的变量，指向插件主类
def get_plugin_class():
    return PluginExample
```

## 4. 插件装饰器

新插件系统使用装饰器来定义插件信息和功能：

### 4.1 @plugin 装饰器

`@plugin`装饰器用于定义插件的基本信息：

```python
@plugin(
    name="插件名称",           # 必需，插件显示名称
    description="插件描述",    # 必需，插件功能描述
    version="1.0.0",           # 必需，插件版本号
    author="开发者名称",        # 必需，插件作者
    is_game_plugin=False       # 可选，是否为玩法类插件，默认为False
)
class YourPlugin(Plugin):
    # 插件实现
```

### 4.2 @setting 装饰器

`@setting`装饰器用于定义插件的配置项：

```python
@setting(
    name="设置项名称",          # 必需，设置项显示名称
    description="设置项描述",   # 必需，设置项详细描述
    default_value=默认值,         # 必需，设置项默认值
    min_value=最小值,             # 可选，数值类型的最小值
    max_value=最大值,             # 可选，数值类型的最大值
    options=选项列表,              # 可选，下拉列表选项
    type=类型                     # 可选，显式指定类型（如int, float, bool, str）
)
```

### 4.3 @event_handler 装饰器

`@event_handler`装饰器用于注册事件处理器：

```python
from src.plugin_system.event import EventPriority
from src.plugin_system.decorators import event_handler

@event_handler("事件名称", priority=EventPriority.NORMAL)
def on_event(self, event):
    # 事件处理逻辑
```

### 4.4 @command_handler 装饰器

`@command_handler`装饰器用于定义自定义命令处理器：

```python
from src.plugin_system.decorators import command_handler

@command_handler("命令名称")
def handle_command(self, params=None):
    # 命令处理逻辑
    return 结果
```

## 5. 插件生命周期

插件具有以下生命周期方法，开发者可以根据需要实现：

- **initialize()**: 插件初始化时调用，接收控制器实例
- **shutdown()**: 插件关闭时调用，用于清理资源
- **on_enable()**: 插件被启用时调用
- **on_disable()**: 插件被禁用时调用

```python
def initialize(self):
    """初始化插件资源"""
    self.controller = DGLabController
    logger.info(f"插件 {self.name} 已初始化")
    return True  # 必须返回True表示初始化成功

def shutdown(self):
    """关闭插件，清理资源"""
    logger.info(f"插件 {self.name} 已关闭")

def on_enable(self):
    """插件启用时调用"""
    logger.info(f"插件 {self.name} 已启用")

def on_disable(self):
    """插件禁用时调用"""
    logger.info(f"插件 {self.name} 已禁用")
```

## 6. 事件系统

新插件系统提供了丰富的事件机制，允许插件监听和响应各种系统事件。

### 6.1 常用事件列表

DG-LAB系统会触发以下常用事件：

- **strength_data_received**: 收到强度数据时触发
- **feedback_button_pressed**: 反馈按钮被按下时触发
- **connection_status_changed**: 设备连接状态变化时触发
- **device_connected**: 设备连接成功时触发
- **device_disconnected**: 设备断开连接时触发
- **intensity_changed**: 强度值变化时触发
- **step_changed**: 步长值变化时触发
- **command_executed**: 命令执行完成时触发

### 6.2 注册事件处理器

使用`@event_handler`装饰器注册事件处理器：

```python
from src.plugin_system.decorators import event_handler
from src.plugin_system.event import EventPriority

@event_handler("device_connected", priority=EventPriority.NORMAL)
def on_device_connected(self, event):
    """设备连接事件回调"""
    logger.info("设备已连接")

@event_handler("intensity_changed", priority=EventPriority.HIGH)
def on_intensity_changed(self, event):
    """强度变化事件回调
    
    参数:
        event: 事件对象，包含channel和intensity等数据
    """
    channel = event['channel']
    intensity = event['intensity']
    logger.info(f"通道 {channel} 强度已变更为: {intensity}")
```

### 6.3 异步事件处理

事件处理器也可以是异步的：

```python
from src.plugin_system.decorators import event_handler

@event_handler("strength_data_received")
async def on_strength_data(self, event):
    """异步处理强度数据"""
    # 异步处理数据，不会阻塞主线程
    result = await self.process_data_async(event.args)
    logger.info(f"数据处理结果: {result}")
```

## 7. 与控制器交互

在`initialize`方法中，插件会接收`controller`实例，可以使用它与DG-LAB设备交互：

### 7.1 发送命令

```python
# 发送振动命令
def send_vibration(self, channel, intensity):
    if self.controller:
        self.controller.send_command("vibration", {
            "channel": channel,
            "intensity": intensity
        })

# 异步发送命令并等待响应
async def send_command_and_wait(self, command_name, params):
    if self.controller:
        response = await self.controller.send_command_async(command_name, params)
        return response
    return None
```

### 7.2 获取设备状态

```python
# 获取连接状态
def is_device_connected(self):
    if self.controller:
        return self.controller.is_connected()
    return False

# 获取当前强度值
def get_current_intensity(self, channel):
    if self.controller:
        return self.controller.get_setting(f"intensity_channel_{channel}")
    return 0
```

### 7.3 触发自定义事件

插件可以触发自定义事件，供其他插件或系统监听：

```python
def trigger_custom_event(self, event_data):
    if self.controller:
        self.controller.trigger_event("my_plugin_custom_event", event_data)
```

## 8. 创建配置界面

插件可以通过实现`get_config_widget()`方法提供自定义配置界面：

### 8.1 基本配置界面

```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSlider, QLabel
from PySide6.QtCore import Qt

def get_config_widget(self):
    """创建插件配置界面"""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    
    # 添加一个滑块作为配置项
    label = QLabel("配置参数:")
    slider = QSlider(Qt.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(50)
    
    # 连接信号槽
    slider.valueChanged.connect(self.on_config_changed)
    
    layout.addWidget(label)
    layout.addWidget(slider)
    
    return widget

def on_config_changed(self, value):
    """配置参数变化处理"""
    logger.info(f"插件 {self.name} 配置已更改为: {value}")
```

### 8.2 使用设置装饰器

结合`@setting`装饰器可以更方便地创建配置项：

```python
from src.plugin_system.decorators import setting

@setting(
    name="通道强度",
    description="设置通道的输出强度",
    default_value=50,
    min_value=0,
    max_value=100
)
def channel_strength(self, value):
    """当设置值变更时的回调函数"""
    logger.info(f"通道强度已更新为: {value}")
    return value
```

### 8.3 读取和更新设置值

在插件中读取和更新设置值：

```python
# 读取设置值
current_value = self.get_setting("channel_strength")

# 更新设置值
self.set_setting("channel_strength", new_value)
```

## 9. 添加自定义UI元素

插件可以向主界面添加自定义UI元素：

```python
def initialize(self):
    """初始化插件并添加自定义UI"""
    # 获取主窗口实例
    main_window = self.controller.get_main_window()
    
    if main_window:
        # 添加自定义工具栏按钮
        from PySide6.QtWidgets import QAction
        from PySide6.QtGui import QIcon
        
        action = QAction("插件操作", main_window)
        action.triggered.connect(self.on_custom_action)
        
        # 添加到工具栏
        if hasattr(main_window, 'toolBar'):
            main_window.toolBar.addAction(action)
        
        logger.info(f"插件 {self.name} 已添加自定义UI元素")
    return True

def on_custom_action(self):
    """自定义操作处理"""
    from PySide6.QtWidgets import QMessageBox
    main_window = self.controller.get_main_window()
    if main_window:
        QMessageBox.information(main_window, "插件操作", "插件自定义操作被触发")
```

## 10. 插件系统API参考

### 10.1 插件类方法

- **get_setting(name)**: 获取指定名称的设置值
- **set_setting(name, value)**: 设置指定名称的设置值
- **trigger_event(event_name, data)**: 触发自定义事件
- **execute_command(command_name, params=None)**: 执行自定义命令
- **get_config_widget()**: 获取插件配置界面组件

### 10.2 控制器API

- **send_command(command_name, params=None)**: 发送命令到设备，不等待响应
- **send_command_async(command_name, params=None)**: 异步发送命令到设备并等待响应
- **is_connected()**: 检查设备是否已连接
- **trigger_event(event_name, event_data)**: 触发系统事件
- **get_main_window()**: 获取主窗口实例
- **get_setting(name)**: 获取系统设置值
- **set_setting(name, value)**: 设置系统设置值

## 11. 异步支持

插件系统完全支持异步操作，可以定义异步事件处理器和命令处理器：

```python
from src.plugin_system.decorators import event_handler, command_handler

@event_handler("strength_data_received")
async def on_strength_data(self, event):
    # 异步处理强度数据
    await self.process_data_async(event.args)

@command_handler("async_command")
async def handle_async_command(self, params=None):
    # 异步处理命令
    result = await self.do_async_work(params)
    return result
```

## 12. 调试插件

### 12.1 日志记录

DG-LAB 使用 Python 的内置 `logging` 模块进行日志记录。插件可以使用以下方式记录不同级别的日志：

```python
import logging

logger = logging.getLogger(__name__)

# 记录不同级别的日志
logger.debug("调试信息")  # 详细调试信息
logger.info("信息")     # 一般信息
logger.warning("警告")   # 警告信息
logger.error("错误")     # 错误信息
logger.critical("严重错误") # 严重错误信息
```

### 12.2 调试技巧

1. **使用打印语句**
   - 在关键位置添加 `print()` 语句输出变量值
   - 记录方法调用和返回值

2. **使用IDE调试器**
   - 使用PyCharm或VS Code设置断点进行调试
   - 检查变量状态和执行流程

3. **测试插件加载**
   - 确认插件目录结构正确
   - 检查 `__init__.py` 文件是否正确提供 `get_plugin_class()` 函数

4. **常见问题排查**
   - **插件无法加载**: 检查插件类是否正确继承 `Plugin`，是否使用了 `@plugin` 装饰器
   - **异步方法不工作**: 确保使用了 `async` 关键字，调用时使用 `await`
   - **事件处理器不响应**: 检查事件名称是否正确，插件是否已启用

## 13. 插件开发最佳实践

### 13.1 设计原则

- **单一职责**: 每个插件应专注于完成一个特定的功能
- **可配置性**: 提供合理的配置选项，让用户可以自定义插件行为
- **资源管理**: 确保在插件禁用或关闭时正确清理资源
- **错误处理**: 合理处理可能出现的异常情况
- **异步优先**: 尽量使用异步方法处理耗时操作

### 13.2 代码规范

- 遵循 Python 的 PEP 8 代码风格指南
- 提供清晰的文档字符串（docstrings）
- 使用有意义的变量和函数名
- 避免硬编码的常量
- 充分利用类型提示

### 13.3 资源管理

- 确保在 `shutdown()` 方法中释放所有资源
- 避免在插件中创建过多的长时间运行的线程
- 使用异步方法处理需要等待的操作

## 14. 插件部署

### 14.1 部署步骤

1. 将插件代码打包为正确的目录结构
2. 将整个插件目录复制到 DG-LAB 的 `plugins` 目录下
3. 重新启动 DG-LAB 或使用插件管理界面加载新插件

### 14.2 版本兼容性

DG-LAB 插件系统架构已更新，请确保：
- 新开发的插件使用新的插件系统 API
- 在发布插件时注明兼容的 DG-LAB 版本

## 15. 插件发布

当你的插件开发完成后，可以按照以下步骤发布：

1. 确保插件代码完整且文档齐全
2. 测试插件在不同环境下的兼容性
3. 打包插件目录为ZIP文件
4. 分享给其他用户或提交到插件仓库（未建立）

## 16. 示例插件参考

项目中包含了一个完整的示例插件，位于`plugins/Example_plugin`目录下，开发者可以参考该示例了解插件的具体实现方式：

- 展示了装饰器的使用方法
- 演示了如何定义设置项
- 展示了事件处理器和命令处理器的实现
- 提供了异步方法的使用示例

## 17. 常见问题解答

### Q: 插件放在哪个目录？
A: 插件应该放在项目根目录下的`plugins`文件夹中。

### Q: 如何检查插件是否被加载？
A: 启动应用程序后，可以在插件管理界面查看所有已加载的插件。

### Q: 插件之间可以相互通信吗？
A: 目前不直接支持插件间通信，可以考虑通过主控制器作为中介进行间接通信。

### Q: 插件可以保存配置吗？
A: 插件可以实现自己的配置保存逻辑，例如使用JSON或SQLite等方式。