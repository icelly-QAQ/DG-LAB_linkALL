# DGLabController API 文档

## 概述

`DGLabController` 是一个用于控制 DG-Lab 设备的核心控制器类，融合了原始版本和 VR 版本的功能实现。它负责处理设备连接、强度控制、波形模式设置以及与游戏（如 ToN）的联动等功能。

## 类定义

```python
class DGLabController:
    def __init__(self, client, ui_callback=None):
        # 初始化方法
```

### `__init__(self, client, ui_callback=None)`

初始化 DGLabController 实例。

**参数:**
- `client`: DGLabWSServer 的客户端实例
- `ui_callback`: 用于更新UI的回调函数（可选）

**功能:**
- 初始化控制器的各种参数和状态
- 设置默认的强度控制参数
- 初始化命令队列和冷却时间管理
- 初始化波形相关参数

**初始化的属性包括:**
- `last_strength`: 记录上次的强度值
- `app_status_online`: App 端在线情况
- `pulse_mode_a/b`: 通道 A/B 的波形模式
- `current_select_channel`: 当前选择的通道
- `fire_mode_strength_step`: 一键开火默认强度
- `adjust_strength_step`: 强度调节步进值
- `command_queue`: 命令优先级队列
- `source_cooldowns`: 各来源的冷却时间
- `enable_*_commands`: 各类命令的启用状态
- `enable_interaction_mode_*`: 各通道交互模式开关
- `pulse_frequency`: 波形更新频率
- `pulse_amplitude_factor`: 波形振幅因子

## 异步组件初始化

### `initialize_async_components(self)`

初始化控制器的异步组件。这个方法应该在事件循环运行后调用。

**功能:**
- 启动命令处理任务
- 初始化其他需要异步环境的组件

## 命令处理相关方法

### `process_commands(self)`

处理命令队列中的命令。

**功能:**
- 从优先级队列中获取命令
- 检查命令来源的冷却时间
- 根据命令类型和启用状态执行相应操作
- 处理各种类型的命令（GUI、面板、交互、ToN等）

**处理逻辑:**
1. 从队列获取命令
2. 检查命令来源的冷却时间
3. 根据命令类型执行相应操作
4. 标记任务完成

### `execute_command(self, command)`

执行命令。

**参数:**
- `command`: 要执行的命令对象

**功能:**
- 根据命令的操作类型调用相应的处理方法
- 支持的操作类型包括：
  - SET_TO: 设置强度值
  - INCREASE: 增加强度值
  - DECREASE: 减少强度值
  - SET_PULSE_MODE: 设置波形模式

### `add_command(self, command_type, channel, operation, value, source_id=None)`

添加命令到队列，带冷却检查。

**参数:**
- `command_type`: 命令类型（CommandType枚举）
- `channel`: 目标通道（Channel枚举）
- `operation`: 操作类型（StrengthOperationType枚举）
- `value`: 操作值
- `source_id`: 来源标识（可选）

**功能:**
- 检查命令冷却时间
- 将命令添加到优先级队列中
- 记录命令来源和时间

## 强度控制相关方法

### `set_strength(self, channel, value)`

设置指定通道的强度值。

**参数:**
- `channel`: 目标通道（Channel枚举）
- `value`: 要设置的强度值

**功能:**
- 使用 `client.set_strength` 方法设置指定通道的强度
- 记录操作日志

### `adjust_strength(self, channel, delta)`

调整指定通道的强度值。

**参数:**
- `channel`: 目标通道（Channel枚举）
- `delta`: 强度变化值（可正可负）

**功能:**
- 根据当前强度和限制范围计算新强度值
- 更新指定通道的强度
- 确保强度值在有效范围内（0 到 通道限制值之间）

### `strength_fire_mode(self, value, channel, fire_strength, last_strength)`

一键开火模式。

**参数:**
- `value`: 触发状态（布尔值）
- `channel`: 目标通道
- `fire_strength`: 开火强度值
- `last_strength`: 原始强度数据

**功能:**
- 启动时记录原始强度值
- 设置开火强度
- 2秒后自动恢复原始强度
- 使用锁机制确保并发安全

### `set_channel(self, value)`

选定当前调节对应的通道。

**参数:**
- `value`: 通道选择值（整数）
  - 0 或 1: 选择通道 A
  - 其他值: 选择通道 B

**功能:**
- 更新当前选择的通道
- 更新UI显示

### `set_panel_control(self, value)`

面板控制开关。

**参数:**
- `value`: 控制值
  - 1: 启用面板控制
  - 0: 禁用面板控制

**功能:**
- 启用或禁用面板控制命令
- 记录操作日志

### `set_mode(self, value, channel)`

设置模式（长按切换交互/面板模式）。

**参数:**
- `value`: 按键状态（布尔值）
- `channel`: 目标通道

**功能:**
- 按下时启动长按计时器
- 松开时取消计时器
- 长按1秒后切换对应通道的交互模式

### `set_mode_timer_handle(self, channel)`

长按按键切换面板/交互模式控制。

**参数:**
- `channel`: 目标通道

**功能:**
- 实现长按1秒后切换模式的逻辑
- 更新对应通道的交互模式开关
- 更新UI显示
- 更新总体交互命令启用状态

## 波形控制相关方法

### `set_pulse_mode(self, channel, mode)`

设置指定通道的波形模式。

**参数:**
- `channel`: 目标通道（Channel枚举）
- `mode`: 波形模式索引

**功能:**
- 更新指定通道的波形模式
- 更新UI显示
- 记录操作日志

### `set_pulse_data(self, value, channel, pulse_index)`

设置波形数据。

**参数:**
- `value`: 触发状态（布尔值）
- `channel`: 目标通道
- `pulse_index`: 波形索引

**功能:**
- 调用 `set_pulse_mode` 方法设置波形模式

### `periodic_send_pulse_data(self)`

波形维护后台任务：当波形超过3秒未被更新时发送更新。
该任务直接作为系统维护任务运行，不通过命令队列。

**功能:**
- 定期检查通道波形是否需要更新
- 当波形超过3秒未更新时发送新的波形数据
- 每秒检查一次

### `send_pulse_data(self, channel)`

发送波形数据。

**参数:**
- `channel`: 目标通道

**功能:**
- 根据通道的波形模式获取对应的波形数据
- 应用振幅因子调整波形强度
- 发送波形数据到设备
- 更新最后更新时间

### `add_pulses(self, channel, *pulses)`

向指定通道添加波形数据。

**参数:**
- `channel`: 目标通道
- `*pulses`: 波形数据（可变参数）

**功能:**
- 向指定通道添加一个或多个波形序列
- 通过客户端发送波形数据

## ToN 游戏联动相关方法

### `handle_ton_damage(self, damage_value, damage_multiplier=1.0)`

处理来自 ToN 游戏的伤害数据。

**参数:**
- `damage_value`: 伤害值
- `damage_multiplier`: 伤害倍数（默认为1.0）

**功能:**
- 根据伤害值计算增加的强度
- 对所有启用的交互通道应用伤害
- 如果没有启用任何通道，默认使用 A 通道
- 通过命令队列增加强度

### `handle_ton_death(self, penalty_strength, penalty_time)`

处理 ToN 游戏死亡惩罚。

**参数:**
- `penalty_strength`: 惩罚强度
- `penalty_time`: 惩罚时间（秒）

**功能:**
- 获取启用的交互通道
- 如果没有启用任何通道，默认使用 A 通道
- 设置惩罚强度并等待指定时间
- 时间结束后恢复原始强度
- 使用命令队列进行强度设置

## 其他辅助方法

### `map_value(self, value, min_value, max_value)`

将值映射到强度范围。

**参数:**
- `value`: 输入值
- `min_value`: 最小值
- `max_value`: 最大值

**功能:**
- 线性映射输入值到指定范围
- 公式: `min_value + value * (max_value - min_value)`

### `update_strength(self, strength_data)`

更新强度数据。

**参数:**
- `strength_data`: 强度数据

**功能:**
- 更新最后强度值
- 设置设备在线状态
- 触发数据更新事件

### `handle_button_feedback(self, button_data)`

处理按钮反馈。

**参数:**
- `button_data`: 按钮数据

**功能:**
- 记录按钮反馈日志
- 可扩展实现按钮反馈处理逻辑

### `toggle_chatbox(self, value)`

切换聊天框状态。

**参数:**
- `value`: 状态值

**功能:**
- OSC功能已删除，仅保留空实现以避免错误

### `cleanup(self)`

清理资源。

**功能:**
- 取消命令处理任务
- 清理其他需要释放的资源
- 记录清理日志

## 总结

本文档详细描述了 `DGLabController` 类的所有公共方法和主要功能。该控制器提供了完整的 DG-Lab 设备控制功能，包括强度控制、波形设置、命令队列管理以及与 ToN 游戏的联动等特性。