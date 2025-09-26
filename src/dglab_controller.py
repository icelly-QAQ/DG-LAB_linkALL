# dglab_controller.py
"""
DGLabController - 融合了原始版本和VR版本的控制器实现
"""
import asyncio
import math
import time
import uuid
from enum import Enum

from pydglab_ws import StrengthData, FeedbackButton, Channel, StrengthOperationType, RetCode, DGLabWSServer
from pulse_data import PULSE_DATA, PULSE_NAME

import logging

from command_types import CommandType

logger = logging.getLogger(__name__)


class ChannelCommand:
    def __init__(self, command_type, channel, operation, value, source_id=None, timestamp=None):
        self.command_type = command_type  # 命令类型，决定优先级
        self.channel = channel  # 目标通道
        self.operation = operation  # 操作类型
        self.value = value  # 操作值
        self.source_id = source_id or str(uuid.uuid4())  # 来源标识
        self.timestamp = timestamp or time.time()  # 时间戳
    
    def __lt__(self, other):
        # 优先级比较函数，用于队列排序
        if self.command_type.value != other.command_type.value:
            return self.command_type.value < other.command_type.value
        return self.timestamp < other.timestamp  # 同优先级按时间排序

class DGLabController:
    def __init__(self, client, ui_callback=None):
        """
        初始化 DGLabController 实例
        :param client: DGLabWSServer 的客户端实例
        :param ui_callback: 用于更新UI的回调函数
        """
        self.client = client
        self.main_window = ui_callback
        self.last_strength = None  # 记录上次的强度值, 从 app更新, 包含 a b a_limit b_limit
        self.app_status_online = False  # App 端在线情况
        # 功能控制参数
        self.pulse_mode_a = 0  # pulse mode for Channel A (双向 - 更新名称)
        self.pulse_mode_b = 0  # pulse mode for Channel B (双向 - 更新名称)
        self.current_select_channel = Channel.A  # 游戏内面板控制的通道选择, 默认为 A (双向)
        self.fire_mode_strength_step = 30    # 一键开火默认强度 (双向)
        self.adjust_strength_step = 5    # 按钮3和按钮4调节强度的步进值
        self.fire_mode_active = False  # 标记当前是否在进行开火操作
        self.fire_mode_lock = asyncio.Lock()  # 一键开火模式锁
        self.data_updated_event = asyncio.Event()  # 数据更新事件
        self.fire_mode_origin_strength_a = 0  # 进入一键开火模式前的强度值
        self.fire_mode_origin_strength_b = 0
        # 定时任务变量 - 初始化为None，在异步初始化中创建
        self.command_processing_task = None
        # 按键延迟触发计时
        self.mode_toggle_timer = None
        # 波形更新相关
        self.pulse_update_lock = asyncio.Lock()  # 添加波形更新锁
        self.pulse_last_update_time = {}  # 记录每个通道最后波形更新时间
        
        # 命令队列相关
        self.command_queue = asyncio.PriorityQueue()  # 优先级队列
        self.command_sources = {}  # 记录各来源的最后命令时间
        self.source_cooldowns = {  # 各来源的冷却时间（秒）
            CommandType.GUI_COMMAND: 0,  # GUI无冷却
            CommandType.PANEL_COMMAND: 0.1,  # 面板命令冷却
            CommandType.INTERACTION_COMMAND: 0.05,  # 交互命令冷却
            CommandType.TON_COMMAND: 0.2,  # 游戏联动冷却
        }
        
        # 命令类型控制
        self.enable_gui_commands = True  # 默认启用GUI命令
        self.enable_panel_commands = True  # 默认启用面板命令
        self.enable_interaction_commands = True  # 默认启用交互命令
        # 各通道交互模式控制
        self.enable_interaction_mode_a = False  # 通道A交互模式开关
        self.enable_interaction_mode_b = False  # 通道B交互模式开关
        
        # 波形参数
        self.pulse_frequency = 10  # 波形更新频率（Hz）
        self.pulse_amplitude_factor = 1.0  # 波形振幅因子，用于全局调整波形强度
        
        logger.info("DGLabController 初始化完成")

    async def initialize_async_components(self):
        """
        初始化控制器的异步组件
        这个方法应该在事件循环运行后调用
        """
        # 启动异步任务
        self.command_processing_task = asyncio.create_task(self.process_commands())
        logger.info("DGLabController 异步组件初始化完成")

    async def process_commands(self):
        """
        处理命令队列中的命令
        """
        while True:
            try:
                # 从队列获取命令
                command = await self.command_queue.get()
                
                # 检查命令来源的冷却时间
                current_time = time.time()
                last_command_time = self.command_sources.get(command.source_id, 0)
                cooldown = self.source_cooldowns.get(command.command_type, 0)
                
                if current_time - last_command_time < cooldown:
                    logger.debug(f"命令 {command.source_id} 冷却中，跳过处理")
                    self.command_queue.task_done()
                    continue
                
                # 更新最后命令时间
                self.command_sources[command.source_id] = current_time
                
                # 根据命令类型执行相应操作
                if command.command_type == CommandType.GUI_COMMAND and self.enable_gui_commands:
                    await self.execute_command(command)
                elif command.command_type == CommandType.PANEL_COMMAND and self.enable_panel_commands:
                    await self.execute_command(command)
                elif command.command_type == CommandType.INTERACTION_COMMAND and self.enable_interaction_commands:
                    # 对于交互命令，还需要检查对应通道是否启用交互模式
                    if (command.channel == Channel.A and self.enable_interaction_mode_a) or \
                       (command.channel == Channel.B and self.enable_interaction_mode_b):
                        await self.execute_command(command)
                elif command.command_type == CommandType.TON_COMMAND:
                    await self.execute_command(command)
                
                # 标记任务完成
                self.command_queue.task_done()
                
            except Exception as e:
                logger.error(f"处理命令队列时出错: {e}", exc_info=True)
                await asyncio.sleep(0.1)  # 防止错误时无限循环

    async def execute_command(self, command):
        """
        执行命令
        """
        try:
            if command.operation == StrengthOperationType.SET_TO:
                await self.set_strength(command.channel, command.value)
            elif command.operation == StrengthOperationType.INCREASE:
                await self.adjust_strength(command.channel, command.value)
            elif command.operation == StrengthOperationType.DECREASE:
                await self.adjust_strength(command.channel, -command.value)
            elif command.operation == StrengthOperationType.SET_PULSE_MODE:
                await self.set_pulse_mode(command.channel, command.value)
        except Exception as e:
            logger.error(f"执行命令时出错: {e}", exc_info=True)

    async def set_strength(self, channel, value):
        """
        设置指定通道的强度值
        """
        try:
            # 使用正确的参数格式：channel, StrengthOperationType.SET_TO, value
            await self.client.set_strength(channel, StrengthOperationType.SET_TO, value)
            logger.info(f"设置通道 {channel.name} 强度为 {value} 成功")
        except Exception as e:
            logger.error(f"设置强度时出错: {e}", exc_info=True)

    async def adjust_strength(self, channel, delta):
        """
        调整指定通道的强度值
        """
        if self.last_strength:
            if channel == Channel.A:
                new_strength = max(0, min(self.last_strength.a_limit, self.last_strength.a + delta))
                await self.client.set_strength(Channel.A, StrengthOperationType.SET_TO, new_strength)
            elif channel == Channel.B:
                new_strength = max(0, min(self.last_strength.b_limit, self.last_strength.b + delta))
                await self.client.set_strength(Channel.B, StrengthOperationType.SET_TO, new_strength)

    async def set_pulse_mode(self, channel, mode):
        """
        设置指定通道的波形模式
        """
        if channel == Channel.A:
            self.pulse_mode_a = mode
            logger.info(f"设置通道 A 波形模式为 {PULSE_NAME[mode]}")
            # 更新UI
            if self.main_window and hasattr(self.main_window.controller_settings_tab, 'pulse_mode_a_combo'):
                self.main_window.controller_settings_tab.pulse_mode_a_combo.blockSignals(True)
                self.main_window.controller_settings_tab.pulse_mode_a_combo.setCurrentIndex(mode)
                self.main_window.controller_settings_tab.pulse_mode_a_combo.blockSignals(False)
        elif channel == Channel.B:
            self.pulse_mode_b = mode
            logger.info(f"设置通道 B 波形模式为 {PULSE_NAME[mode]}")
            # 更新UI
            if self.main_window and hasattr(self.main_window.controller_settings_tab, 'pulse_mode_b_combo'):
                self.main_window.controller_settings_tab.pulse_mode_b_combo.blockSignals(True)
                self.main_window.controller_settings_tab.pulse_mode_b_combo.setCurrentIndex(mode)
                self.main_window.controller_settings_tab.pulse_mode_b_combo.blockSignals(False)

    async def set_channel(self, value):
        """
        value: INT
        选定当前调节对应的通道, 目前 Page 1-2 为 Channel A， Page 3 为 Channel B
        """
        if value >= 0:
            self.current_select_channel = Channel.A if value <= 1 else Channel.B
            logger.info(f"set activate channel to: {self.current_select_channel}")
            if self.main_window.controller_settings_tab:
                channel_name = "A" if self.current_select_channel == Channel.A else "B"
                self.main_window.controller_settings_tab.update_current_channel_display(channel_name)

    async def set_panel_control(self, value):
        """
        面板控制开关
        """
        if value == 1:
            self.enable_panel_commands = True
            logger.info("启用面板控制")
        elif value == 0:
            self.enable_panel_commands = False
            logger.info("禁用面板控制")

    async def set_mode(self, value, channel):
        """
        设置模式
        """
        if value:
            # 开始长按计时
            if self.mode_toggle_timer:
                self.mode_toggle_timer.cancel()
            self.mode_toggle_timer = asyncio.create_task(self.set_mode_timer_handle(channel))
        else:
            # 松开按键，取消计时
            if self.mode_toggle_timer:
                self.mode_toggle_timer.cancel()
                self.mode_toggle_timer = None

    async def set_mode_timer_handle(self, channel):
        """
        长按按键切换 面板/交互 模式控制
        """
        await asyncio.sleep(1)

        if channel == Channel.A:
            self.enable_interaction_mode_a = not self.enable_interaction_mode_a
            mode_name = "可交互模式" if self.enable_interaction_mode_a else "面板设置模式"
            logger.info("通道 A 切换为" + mode_name)
            # 更新UI
            if self.main_window:
                self.main_window.controller_settings_tab.enable_interaction_commands_a_checkbox.blockSignals(True)
                self.main_window.controller_settings_tab.enable_interaction_commands_a_checkbox.setChecked(self.enable_interaction_mode_a)
                self.main_window.controller_settings_tab.enable_interaction_commands_a_checkbox.blockSignals(False)
        elif channel == Channel.B:
            self.enable_interaction_mode_b = not self.enable_interaction_mode_b
            mode_name = "可交互模式" if self.enable_interaction_mode_b else "面板设置模式"
            logger.info("通道 B 切换为" + mode_name)
            # 更新UI
            if self.main_window:
                self.main_window.controller_settings_tab.enable_interaction_commands_b_checkbox.blockSignals(True)
                self.main_window.controller_settings_tab.enable_interaction_commands_b_checkbox.setChecked(self.enable_interaction_mode_b)
                self.main_window.controller_settings_tab.enable_interaction_commands_b_checkbox.blockSignals(False)
                
        # 更新总体交互命令启用状态
        if self.main_window:
            self.enable_interaction_commands = self.enable_interaction_mode_a or self.enable_interaction_mode_b

    async def strength_fire_mode(self, value, channel, fire_strength, last_strength):
        """
        一键开火模式
        """
        async with self.fire_mode_lock:
            if value and not self.fire_mode_active:
                # 开始开火模式
                self.fire_mode_active = True
                # 记录原始强度值
                if last_strength:
                    self.fire_mode_origin_strength_a = last_strength.a
                    self.fire_mode_origin_strength_b = last_strength.b
                      
                # 设置开火强度
                await self.client.set_strength(channel, StrengthOperationType.SET_TO, fire_strength)
                
                logger.info(f"开火模式启动: 通道 {channel.name}, 强度 {fire_strength}")
                
                # 设置定时器，2秒后恢复原始强度
                await asyncio.sleep(2)
                
                # 恢复原始强度
                if last_strength:
                    if channel == Channel.A:
                        await self.client.set_strength(Channel.A, StrengthOperationType.SET_TO, self.fire_mode_origin_strength_a)
                    elif channel == Channel.B:
                        await self.client.set_strength(Channel.B, StrengthOperationType.SET_TO, self.fire_mode_origin_strength_b)
                
                self.fire_mode_active = False
                logger.info(f"开火模式结束: 通道 {channel.name}, 已恢复原始强度")

    async def toggle_chatbox(self, value):
        """
        切换聊天框状态 - OSC功能已删除，仅保留空实现以避免错误
        """
        pass

    async def set_pulse_data(self, value, channel, pulse_index):
        """
        设置波形数据
        """
        if value:
            if channel == Channel.A:
                await self.set_pulse_mode(Channel.A, pulse_index)
            elif channel == Channel.B:
                await self.set_pulse_mode(Channel.B, pulse_index)

    async def add_command(self, command_type, channel, operation, value, source_id=None):
        """
        添加命令到队列，带冷却检查
        """
        now = time.time()
        source_key = f"{command_type.name}_{source_id or 'default'}"
        
        # 检查冷却时间
        if source_key in self.command_sources:
            last_time = self.command_sources[source_key]
            cooldown = self.source_cooldowns[command_type]
            if now - last_time < cooldown:
                logger.debug(f"命令在冷却期内，已忽略: {command_type.name}, 来源: {source_id}")
                return  # 在冷却期内，忽略命令
        
        # 记录时间并加入队列
        self.command_sources[source_key] = now
        await self.command_queue.put(ChannelCommand(command_type, channel, operation, value, source_id, now))
        logger.debug(f"已添加命令: {command_type.name}, 通道: {channel}, 操作: {operation}, 值: {value}")

    def map_value(self, value, min_value, max_value):
        """
        将值映射到强度范围
        """
        return min_value + value * (max_value - min_value)

    async def update_strength(self, strength_data):
        """
        更新强度数据
        """
        self.last_strength = strength_data
        self.app_status_online = True
        self.data_updated_event.set()

    async def handle_button_feedback(self, button_data):
        """
        处理按钮反馈
        """
        logger.info(f"收到按钮反馈: {button_data}")
        # 这里可以根据需要实现按钮反馈的处理逻辑

    async def cleanup(self):
        """
        清理资源
        """
        if self.command_processing_task:
            self.command_processing_task.cancel()
            try:
                await self.command_processing_task
            except asyncio.CancelledError:
                pass
            
        logger.info("DGLabController 资源已清理")

    # 以下是与波形相关的方法
    async def periodic_send_pulse_data(self):
        """
        波形维护后台任务：当波形超过3秒未被更新时发送更新
        该任务直接作为系统维护任务运行，不通过命令队列
        """
        while True:
            try:
                if self.last_strength:  # 当收到设备状态后再发送波形
                    current_time = asyncio.get_event_loop().time()
                    
                    # 使用锁防止并发访问
                    async with self.pulse_update_lock:
                        # 检查通道A波形
                        if Channel.A in self.pulse_last_update_time:
                            if current_time - self.pulse_last_update_time[Channel.A] > 3:
                                await self.send_pulse_data(Channel.A)
                        
                        # 检查通道B波形
                        if Channel.B in self.pulse_last_update_time:
                            if current_time - self.pulse_last_update_time[Channel.B] > 3:
                                await self.send_pulse_data(Channel.B)
            except Exception as e:
                logger.error(f"periodic_send_pulse_data 任务中发生错误: {e}", exc_info=True)
            
            await asyncio.sleep(1)  # 每秒检查一次

    async def send_pulse_data(self, channel):
        """
        发送波形数据
        """
        try:
            if channel == Channel.A:
                pulse_mode = self.pulse_mode_a
                pulse_data = PULSE_DATA.get(pulse_mode, [])
            else:
                pulse_mode = self.pulse_mode_b
                pulse_data = PULSE_DATA.get(pulse_mode, [])
            
            if pulse_data:
                # 应用振幅因子
                scaled_pulse = [min(100, max(0, int(val * self.pulse_amplitude_factor))) for val in pulse_data]
                
                # 使用正确的API：set_pulse(channel, scaled_pulse) 而不是 set_pulse_a/set_pulse_b
                await self.client.set_pulse(channel, scaled_pulse)
                
                # 更新最后更新时间
                self.pulse_last_update_time[channel] = asyncio.get_event_loop().time()
                logger.debug(f"发送波形数据: 通道 {channel.name}, 模式 {PULSE_NAME[pulse_mode]}")
        except Exception as e:
            logger.error(f"发送波形数据时出错: {e}", exc_info=True)

    async def add_pulses(self, channel, *pulses):
        """
        向指定通道添加波形数据
        """
        try:
            await self.client.add_pulses(channel, *pulses)
        except Exception as e:
            logger.error(f"添加波形数据失败: {e}")
