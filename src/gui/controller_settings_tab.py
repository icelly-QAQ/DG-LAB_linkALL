#!/usr/bin/env python3
# -*- coding: utf-8 -*-"控制器设置标签页模块
"""此模块实现了DG-Lab控制器的设置界面，包括通道强度控制、参数设置
和设备连接二维码显示功能。"""
from PySide6.QtWidgets import (QWidget, QGroupBox, QFormLayout, QLabel, QSlider,
                               QCheckBox, QComboBox, QSpinBox, QHBoxLayout, QToolTip, QPushButton, QVBoxLayout)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal, Slot
import asyncio
import logging

# 导入所需的类
from src.dglab_controller import Channel, CommandType, PULSE_DATA
from pydglab_ws import StrengthOperationType

logger = logging.getLogger(__name__)


class ControllerSettingsTab(QWidget):
    """控制器设置标签页类，提供DG-Lab控制器的参数设置和通道控制界面。
    
    属性:
        main_window: 主窗口引用
        dg_controller: DGLab控制器引用
        main_layout: 主布局
        left_panel: 左侧控制面板
        right_panel: 右侧二维码显示面板
        a_channel_slider: A通道强度滑动条
        b_channel_slider: B通道强度滑动条
        allow_a_channel_update: 是否允许A通道外部更新
        allow_b_channel_update: 是否允许B通道外部更新
    """
    
    # 添加信号用于在主线程中更新UI
    strength_data_updated = Signal(object)  # 接收StrengthData对象
    
    def __init__(self, main_window):
        """初始化控制器设置标签页实例。
        
        参数:
            main_window: 主窗口引用，用于访问控制器实例
        """
        super().__init__()
        self.main_window = main_window
        self.dg_controller = None

        # 创建主布局
        self.main_layout = QHBoxLayout(self)
        self.setLayout(self.main_layout)

        # 连接信号到槽函数
        self.strength_data_updated.connect(self.update_channel_strength_labels)

        # 左侧控制面板
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)

        # 控制器参数设置
        self.controller_group = QGroupBox("控制器设置")
        self.controller_group.setEnabled(False)  # 默认禁用
        self.controller_form = QFormLayout()

        # 添加 A 通道滑动条和标签
        self.a_channel_label = QLabel("A通道强度: 0 / 100")  # 默认显示
        self.a_channel_slider = QSlider(Qt.Horizontal)
        self.a_channel_slider.setRange(0, 100)  # 默认范围
        self.a_channel_slider.valueChanged.connect(self.set_a_channel_strength)
        self.a_channel_slider.sliderPressed.connect(self.disable_a_channel_updates)  # 用户开始拖动时禁用外部更新
        self.a_channel_slider.sliderReleased.connect(self.enable_a_channel_updates)  # 用户释放时重新启用外部更新
        self.controller_form.addRow(self.a_channel_label)
        self.controller_form.addRow(self.a_channel_slider)

        # 添加 B 通道滑动条和标签
        self.b_channel_label = QLabel("B通道强度: 0 / 100")  # 默认显示
        self.b_channel_slider = QSlider(Qt.Horizontal)
        self.b_channel_slider.setRange(0, 100)  # 默认范围
        self.b_channel_slider.valueChanged.connect(self.set_b_channel_strength)
        self.b_channel_slider.sliderPressed.connect(self.disable_b_channel_updates)  # 用户开始拖动时禁用外部更新
        self.b_channel_slider.sliderReleased.connect(self.enable_b_channel_updates)  # 用户释放时重新启用外部更新
        self.controller_form.addRow(self.b_channel_label)
        self.controller_form.addRow(self.b_channel_slider)

        # 控制滑动条外部更新的状态标志
        self.allow_a_channel_update = True
        self.allow_b_channel_update = True

        # 强度步长
        self.strength_step_spinbox = QSpinBox()
        self.strength_step_spinbox.setRange(0, 100)
        self.strength_step_spinbox.setValue(30)
        self.controller_form.addRow("强度步长:", self.strength_step_spinbox)

        # 调节强度步长
        self.adjust_strength_step_spinbox = QSpinBox()
        self.adjust_strength_step_spinbox.setRange(0, 100)
        self.adjust_strength_step_spinbox.setValue(5)
        self.controller_form.addRow("调节步长:", self.adjust_strength_step_spinbox)

        # 创建A通道波形选择下拉框
        self.waveform_combo_a = QComboBox()
        # 从PULSE_DATA中获取波形名称
        for waveform_name in PULSE_DATA.keys():
            self.waveform_combo_a.addItem(waveform_name, waveform_name)
        # 默认选择第一个波形
        self.waveform_combo_a.setCurrentIndex(0)
        # 连接信号槽，当选择变化时发送波形数据
        self.waveform_combo_a.currentIndexChanged.connect(lambda index: self.on_waveform_changed(index, Channel.A))
        
        # 创建A通道波形按钮
        self.waveform_button_a = QPushButton("开始循环")
        self.waveform_button_a.clicked.connect(lambda: self.on_waveform_button_clicked(Channel.A))
        
        # 存储A通道波形发送任务和状态
        self.a_waveform_task = None
        self.a_waveform_running = False
        self.a_waveform_task_id = None  # 用于标识任务的唯一ID
        
        # 创建A通道波形水平布局
        self.waveform_layout_a = QHBoxLayout()
        self.waveform_layout_a.addWidget(self.waveform_combo_a)
        self.waveform_layout_a.addWidget(self.waveform_button_a)

        # 创建B通道波形选择下拉框
        self.waveform_combo_b = QComboBox()
        # 从PULSE_DATA中获取波形名称
        for waveform_name in PULSE_DATA.keys():
            self.waveform_combo_b.addItem(waveform_name, waveform_name)
        # 默认选择第一个波形
        self.waveform_combo_b.setCurrentIndex(0)
        # 连接信号槽，当选择变化时发送波形数据
        self.waveform_combo_b.currentIndexChanged.connect(lambda index: self.on_waveform_changed(index, Channel.B))
        
        # 创建B通道波形按钮
        self.waveform_button_b = QPushButton("开始循环")
        self.waveform_button_b.clicked.connect(lambda: self.on_waveform_button_clicked(Channel.B))
        
        # 存储B通道波形发送任务和状态
        self.b_waveform_task = None
        self.b_waveform_running = False
        self.b_waveform_task_id = None  # 用于标识任务的唯一ID
        
        # 创建B通道波形水平布局
        self.waveform_layout_b = QHBoxLayout()
        self.waveform_layout_b.addWidget(self.waveform_combo_b)
        self.waveform_layout_b.addWidget(self.waveform_button_b)

        # 添加到表单布局
        self.controller_form.addRow("A通道波形:", self.waveform_layout_a)
        self.controller_form.addRow("B通道波形:", self.waveform_layout_b)

        # 添加测试按钮
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.test_connection)
        self.controller_form.addRow(self.test_button)

        self.controller_group.setLayout(self.controller_form)
        self.left_layout.addWidget(self.controller_group)

        # 右侧二维码显示区域
        self.right_panel = QWidget()
        self.right_layout = QVBoxLayout(self.right_panel)
        
        self.qrcode_group = QGroupBox("设备连接二维码")
        self.qrcode_layout = QVBoxLayout()
        
        # 二维码显示标签
        self.qrcode_label = QLabel("请使用郊狼App扫描此二维码进行连接")
        self.qrcode_label.setAlignment(Qt.AlignCenter)
        self.qrcode_layout.addWidget(self.qrcode_label)
        
        # 二维码图像标签
        self.qrcode_image_label = QLabel()
        self.qrcode_image_label.setAlignment(Qt.AlignCenter)
        self.qrcode_layout.addWidget(self.qrcode_image_label)
        
        self.qrcode_group.setLayout(self.qrcode_layout)
        self.right_layout.addWidget(self.qrcode_group)

        # 添加到主布局
        self.main_layout.addWidget(self.left_panel, 2)  # 左侧占2份
        self.main_layout.addWidget(self.right_panel, 1)  # 右侧占1份

        # 连接UI到控制器更新方法
        self.strength_step_spinbox.valueChanged.connect(self.update_strength_step)
        self.adjust_strength_step_spinbox.valueChanged.connect(self.update_adjust_strength_step)

    def bind_controller_settings(self):
        """将GUI设置与DGLabController变量绑定。
        
        将UI中设置的参数值同步到控制器实例中，建立控制器与界面的连接。
        """
        if self.main_window.controller:
            self.dg_controller = self.main_window.controller
            self.dg_controller.fire_mode_strength_step = self.strength_step_spinbox.value()
            self.dg_controller.adjust_strength_step = self.adjust_strength_step_spinbox.value()
            logger.info("DGLabController 参数已绑定")
        else:
            logger.warning("控制器尚未初始化")

    def sync_from_controller(self, controller):
        """从控制器同步设置到UI。
        
        参数:
            controller: DGLabController实例
        """
        if controller:
            # 阻止信号触发的更新循环
            self.strength_step_spinbox.blockSignals(True)
            self.adjust_strength_step_spinbox.blockSignals(True)
            self.waveform_combo_a.blockSignals(True)
            self.waveform_combo_b.blockSignals(True)
            
            # 同步其他控制设置
            self.strength_step_spinbox.setValue(controller.fire_mode_strength_step)
            self.adjust_strength_step_spinbox.setValue(controller.adjust_strength_step)
            
            # 同步波形设置
            # 由于我们现在使用PULSE_DATA中的波形名称
            if PULSE_DATA:
                first_waveform_name = next(iter(PULSE_DATA.keys()))
                # 设置A通道波形
                for i in range(self.waveform_combo_a.count()):
                    waveform_name = self.waveform_combo_a.itemData(i)
                    if waveform_name == first_waveform_name:
                        self.waveform_combo_a.setCurrentIndex(i)
                        break
                # 设置B通道波形
                for i in range(self.waveform_combo_b.count()):
                    waveform_name = self.waveform_combo_b.itemData(i)
                    if waveform_name == first_waveform_name:
                        self.waveform_combo_b.setCurrentIndex(i)
                        break
            
            # 初始化强度上限显示
            # 如果已有强度数据（从手机获取），则使用该数据更新UI
            if hasattr(controller, 'last_strength') and controller.last_strength:
                self.update_channel_strength_labels(controller.last_strength)
            else:
                # 如果还没有从手机获取数据，设置默认的强度上限为100
                # 创建一个模拟的StrengthData对象
                from pydglab_ws import StrengthData
                default_strength_data = StrengthData(a=0, b=0, a_limit=100, b_limit=100)
                self.update_channel_strength_labels(default_strength_data)
            
            # 恢复信号
            self.strength_step_spinbox.blockSignals(False)
            self.adjust_strength_step_spinbox.blockSignals(False)
            self.waveform_combo_a.blockSignals(False)
            self.waveform_combo_b.blockSignals(False)
            
            logger.info("已从控制器同步UI状态")

    def on_waveform_changed(self, index, channel):
        """处理波形选择变更事件。
        
        参数:
            index: int，选择的索引
            channel: Channel枚举，目标通道
        """
        if self.main_window.controller:
            # 根据通道选择对应的下拉框
            combo_box = self.waveform_combo_a if channel == Channel.A else self.waveform_combo_b
            # 获取选中的波形名称
            waveform_name = combo_box.itemData(index)
            
            channel_name = "A" if channel == Channel.A else "B"
            logger.info(f"{channel_name}通道波形已更改为: {waveform_name}")
            
            # 检查当前通道是否正在运行波形任务
            if channel == Channel.A and self.a_waveform_running:
                # 停止当前任务
                self.stop_waveform_task(Channel.A)
                # 启动新任务
                self.start_waveform_task(Channel.A, waveform_name)
            elif channel == Channel.B and self.b_waveform_running:
                # 停止当前任务
                self.stop_waveform_task(Channel.B)
                # 启动新任务
                self.start_waveform_task(Channel.B, waveform_name)

    def on_waveform_button_clicked(self, channel):
        """处理波形按钮点击事件。
        
        参数:
            channel: Channel枚举，目标通道
        """
        if self.main_window.controller:
            combo_box = self.waveform_combo_a if channel == Channel.A else self.waveform_combo_b
            waveform_name = combo_box.itemData(combo_box.currentIndex())
            
            if channel == Channel.A:
                if self.a_waveform_running:
                    self.stop_waveform_task(Channel.A)
                else:
                    self.start_waveform_task(Channel.A, waveform_name)
            else:
                if self.b_waveform_running:
                    self.stop_waveform_task(Channel.B)
                else:
                    self.start_waveform_task(Channel.B, waveform_name)

    def start_waveform_task(self, channel, waveform_name):
        """启动波形循环发送任务。
        
        参数:
            channel: Channel枚举，目标通道
            waveform_name: str，波形名称
        """
        import uuid  # 用于生成唯一的任务ID
        
        # 先生成新的任务ID
        new_task_id = str(uuid.uuid4())[:8]  # 使用短ID以便日志清晰
        
        if channel == Channel.A:
            # 取消当前任务（如果存在）
            if self.a_waveform_task:
                logger.info(f"取消A通道正在运行的波形任务(ID: {self.a_waveform_task_id})")
                self.a_waveform_task.cancel()
            # 创建新任务，传递任务ID
            self.a_waveform_task = asyncio.create_task(self.loop_send_waveform_data(waveform_name, Channel.A, new_task_id))
            self.a_waveform_running = True
            self.a_waveform_task_id = new_task_id
            self.waveform_button_a.setText("停止循环")
        else:
            # 取消当前任务（如果存在）
            if self.b_waveform_task:
                logger.info(f"取消B通道正在运行的波形任务(ID: {self.b_waveform_task_id})")
                self.b_waveform_task.cancel()
            # 创建新任务，传递任务ID
            self.b_waveform_task = asyncio.create_task(self.loop_send_waveform_data(waveform_name, Channel.B, new_task_id))
            self.b_waveform_running = True
            self.b_waveform_task_id = new_task_id
            self.waveform_button_b.setText("停止循环")
        
        channel_name = "A" if channel == Channel.A else "B"
        logger.info(f"开始{channel_name}通道波形循环(ID: {new_task_id}): {waveform_name}")

    def stop_waveform_task(self, channel):
        """停止波形循环发送任务。
        
        参数:
            channel: Channel枚举，目标通道
        """
        channel_name = "A" if channel == Channel.A else "B"
        task_var = self.a_waveform_task if channel == Channel.A else self.b_waveform_task
        task_id = self.a_waveform_task_id if channel == Channel.A else self.b_waveform_task_id
        
        # 强制设置为非运行状态，确保UI反映正确状态
        if channel == Channel.A:
            self.a_waveform_running = False
            self.waveform_button_a.setText("开始循环")
        else:
            self.b_waveform_running = False
            self.waveform_button_b.setText("开始循环")
        
        # 立即清除任务引用，防止任务继续被访问
        if channel == Channel.A:
            self.a_waveform_task = None
            self.a_waveform_task_id = None
        else:
            self.b_waveform_task = None
            self.b_waveform_task_id = None
        
        if task_var:
            logger.info(f"准备取消{channel_name}通道波形循环任务(ID: {task_id})")
            task_var.cancel()
            logger.info(f"已发送取消请求到{channel_name}通道波形循环任务(ID: {task_id})")
        else:
            logger.info(f"{channel_name}通道没有正在运行的波形循环任务")
        
        logger.info(f"已停止{channel_name}通道波形循环，状态已更新")

    async def send_waveform_data(self, waveform_name, channel, task_id=None):
        """将选择的波形数据发送到指定通道。
        
        参数:
            waveform_name: str，波形名称
            channel: Channel枚举，目标通道
            task_id: str，可选，任务的唯一标识
        """
        # 在发送前检查任务是否仍然有效
        is_task_valid = True
        if task_id:
            if channel == Channel.A:
                is_task_valid = (self.a_waveform_task_id == task_id and self.a_waveform_running)
            else:
                is_task_valid = (self.b_waveform_task_id == task_id and self.b_waveform_running)
        
        if not is_task_valid:
            logger.info(f"任务已无效，跳过波形发送: 通道{channel.name}, ID: {task_id}")
            return
        
        if self.main_window.controller and hasattr(self.main_window.controller, 'add_pulses'):
            try:
                # 再次检查任务是否有效，防止在检查后状态发生变化
                if task_id:
                    if channel == Channel.A:
                        is_task_valid = (self.a_waveform_task_id == task_id and self.a_waveform_running)
                    else:
                        is_task_valid = (self.b_waveform_task_id == task_id and self.b_waveform_running)
                
                if is_task_valid and waveform_name in PULSE_DATA:
                    pulse_data = PULSE_DATA[waveform_name]
                    # 只发送1份波形数据，而不是5份
                    pulses_to_send = pulse_data  # 不重复发送多次，而是每次只发送一次
                    # 使用控制器发送波形到指定通道
                    await self.main_window.controller.add_pulses(channel, *pulses_to_send)
                else:
                    if waveform_name not in PULSE_DATA:
                        logger.warning(f"未找到波形数据: {waveform_name}")
                    
                    # 如果是因为任务无效而跳过，记录日志
                    if task_id and not is_task_valid:
                        logger.info(f"任务已无效，跳过波形发送: 通道{channel.name}, ID: {task_id}")
            except Exception as e:
                logger.error(f"发送波形数据时出错: {e}")

    def calculate_waveform_duration(self, waveform_name):
        """计算波形的总播放时间（毫秒）。
        
        参数:
            waveform_name: str，波形名称
        
        返回:
            int: 波形的总播放时间（毫秒）
        """
        if waveform_name in PULSE_DATA:
            total_duration = 0
            for pulse in PULSE_DATA[waveform_name]:
                # 每个脉冲的持续时间是第一个元组中的值的总和
                duration_values = pulse[0]
                # 假设每个值代表的是10毫秒（根据波形数据的模式推断）
                pulse_duration = sum(duration_values) * 10  # 转换为毫秒
                total_duration += pulse_duration
            return total_duration
        return 0

    async def loop_send_waveform_data(self, waveform_name, channel, task_id):
        """循环发送波形数据到指定通道。
        
        参数:
            waveform_name: str，波形名称
            channel: Channel枚举，目标通道
            task_id: str，任务的唯一标识
        """
        channel_name = channel.name
        logger.info(f"波形循环任务已启动: 通道{channel_name}, 波形: {waveform_name}, ID: {task_id}")
        
        # 验证任务ID是否与当前记录的一致
        is_task_valid = lambda: ((channel == Channel.A and self.a_waveform_task_id == task_id) or \
                                 (channel == Channel.B and self.b_waveform_task_id == task_id)) and \
                                ((channel == Channel.A and self.a_waveform_running) or \
                                 (channel == Channel.B and self.b_waveform_running))
        
        try:
            while True:
                # 在每次循环开始时检查任务是否有效
                if not is_task_valid():
                    logger.info(f"波形循环任务已被终止(无效状态): 通道{channel_name}, ID: {task_id}")
                    break
                    
                # 检查是否有取消请求
                if asyncio.current_task().done():
                    logger.info(f"波形循环任务检测到取消信号: 通道{channel_name}, ID: {task_id}")
                    break
                    
                # 发送波形数据
                await self.send_waveform_data(waveform_name, channel, task_id)
                logger.info(f"已发送波形数据: 通道{channel_name}, 波形: {waveform_name}, ID: {task_id}")
                
                # 再次检查任务有效性
                if not is_task_valid():
                    logger.info(f"波形循环任务已被终止(无效状态): 通道{channel_name}, ID: {task_id}")
                    break
                    
                # 等待波形播放间隔，设置固定的0.5秒
                wait_time = 0.5  # 直接设置为0.5秒的固定间隔
                logger.info(f"等待波形播放间隔: {wait_time:.2f}秒")
                
                # 使用分片的sleep，以便能够及时检测到取消信号
                start_time = asyncio.get_event_loop().time()
                remaining_wait = wait_time
                while remaining_wait > 0 and is_task_valid():
                    # 每次等待一小段时间以提高响应速度
                    sleep_duration = min(0.2, remaining_wait)  # 最大等待0.2秒
                    await asyncio.sleep(sleep_duration)
                    
                    # 检查任务是否仍然有效
                    if not is_task_valid():
                        logger.info(f"波形循环任务在等待期间被终止: 通道{channel_name}, ID: {task_id}")
                        break
                    
                    # 检查是否有取消请求
                    if asyncio.current_task().done():
                        logger.info(f"波形循环任务在等待期间检测到取消信号: 通道{channel_name}, ID: {task_id}")
                        break
                    
                    # 更新剩余等待时间
                    elapsed = asyncio.get_event_loop().time() - start_time
                    remaining_wait = wait_time - elapsed
        except asyncio.CancelledError:
            # 任务被取消时正常退出
            logger.info(f"波形循环任务已确认取消: 通道{channel_name}, ID: {task_id}")
            # 确保状态已正确更新
            if channel == Channel.A and self.a_waveform_running:
                self.a_waveform_running = False
                self.waveform_button_a.setText("开始循环")
                logger.info(f"A通道波形循环任务状态已最终确认更新")
            elif channel == Channel.B and self.b_waveform_running:
                self.b_waveform_running = False
                self.waveform_button_b.setText("开始循环")
                logger.info(f"B通道波形循环任务状态已最终确认更新")
            # 重新抛出CancelledError以确保任务正确终止
            raise

    # Controller update methods
    def update_strength_step(self, value):
        """更新一键开火模式的强度步长。
        
        参数:
            value: int，新的强度步长值
        """
        if self.main_window.controller:
            controller = self.main_window.controller
            controller.fire_mode_strength_step = value
            logger.info(f"强度步长已更新为 {value}")

    def update_adjust_strength_step(self, value):
        """更新调节强度的步进值。
        
        参数:
            value: int，新的调节步进值
        """
        if self.main_window.controller:
            controller = self.main_window.controller
            controller.adjust_strength_step = value
            logger.info(f"调节步长已更新为 {value}")

    def set_a_channel_strength(self, value):
        """根据滑动条的值设定A通道强度。
        
        参数:
            value: int，A通道的目标强度值
        """
        if self.main_window.controller and self.allow_a_channel_update:
            controller = self.main_window.controller
            asyncio.create_task(controller.add_command(
                CommandType.GUI_COMMAND,
                Channel.A,
                StrengthOperationType.SET_TO,
                value,
                "gui_slider_a"
            ))
            self.a_channel_slider.setToolTip(f"设置A通道强度: {value}")

    def set_b_channel_strength(self, value):
        """根据滑动条的值设定B通道强度。
        
        参数:
            value: int，B通道的目标强度值
        """
        if self.main_window.controller and self.allow_b_channel_update:
            controller = self.main_window.controller
            asyncio.create_task(controller.add_command(
                CommandType.GUI_COMMAND,
                Channel.B,
                StrengthOperationType.SET_TO,
                value,
                "gui_slider_b"
            ))
            self.b_channel_slider.setToolTip(f"设置B通道强度: {value}")

    def disable_a_channel_updates(self):
        """禁用A通道的外部更新。
        
        当用户拖动滑动条时调用，防止设备状态更新与用户操作冲突。
        """
        self.allow_a_channel_update = False

    def enable_a_channel_updates(self):
        """启用A通道的外部更新。
        
        当用户释放滑动条时调用，恢复设备状态更新并应用用户设置。
        """
        self.allow_a_channel_update = True
        self.set_a_channel_strength(self.a_channel_slider.value())  # 用户释放时，更新设备

    def disable_b_channel_updates(self):
        """禁用B通道的外部更新。
        
        当用户拖动滑动条时调用，防止设备状态更新与用户操作冲突。
        """
        self.allow_b_channel_update = False

    def enable_b_channel_updates(self):
        """启用B通道的外部更新。
        
        当用户释放滑动条时调用，恢复设备状态更新并应用用户设置。
        """
        self.allow_b_channel_update = True
        self.set_b_channel_strength(self.b_channel_slider.value())  # 用户释放时，更新设备

    def test_connection(self):
        """测试与DG-Lab设备的连接状态。
        
        向设备发送测试命令，验证连接是否正常。
        短暂地向两个通道发送强度为30的命令，随后归零。
        """
        if self.main_window.controller:
            logger.info("正在测试设备连接...")
            async def test_sequence():
                try:
                    controller = self.main_window.controller
                    # 短暂向两个通道发送强度为30的命令
                    await controller.add_command(
                        CommandType.GUI_COMMAND,
                        Channel.A,
                        StrengthOperationType.SET_TO,
                        30,
                        "connection_test"
                    )
                    await controller.add_command(
                        CommandType.GUI_COMMAND,
                        Channel.B,
                        StrengthOperationType.SET_TO,
                        30,
                        "connection_test"
                    )
                    
                    # 等待短暂时间
                    await asyncio.sleep(0.5)
                    
                    # 发送归零命令
                    await controller.add_command(
                        CommandType.GUI_COMMAND,
                        Channel.A,
                        StrengthOperationType.SET_TO,
                        0,
                        "connection_test_end"
                    )
                    await controller.add_command(
                        CommandType.GUI_COMMAND,
                        Channel.B,
                        StrengthOperationType.SET_TO,
                        0,
                        "connection_test_end"
                    )
                    
                    logger.info("连接测试完成，已向两个通道发送强度30的命令并恢复为0")
                except Exception as e:
                    logger.error(f"连接测试失败: {e}", exc_info=True)
            
            # 创建异步任务执行测试序列
            asyncio.create_task(test_sequence())

    @Slot(object)
    def update_channel_strength_labels(self, strength_data):
        """更新通道强度显示标签和滑动条状态。
        
        参数:
            strength_data: StrengthData对象，包含当前通道强度和限制信息
        """
        logger.info(f"通道状态已更新 - A通道强度: {strength_data.a}, B通道强度: {strength_data.b}")
        if self.main_window.controller:
            # 仅当允许外部更新时更新A通道滑动条
            if self.allow_a_channel_update:
                self.a_channel_slider.blockSignals(True)
                self.a_channel_slider.setRange(0, strength_data.a_limit)  # 根据限制更新范围
                self.a_channel_slider.setValue(strength_data.a)
                self.a_channel_slider.blockSignals(False)
                self.a_channel_label.setText(
                    f"A通道强度: {strength_data.a}/{strength_data.a_limit}")

            # 仅当允许外部更新时更新B通道滑动条
            if self.allow_b_channel_update:
                self.b_channel_slider.blockSignals(True)
                self.b_channel_slider.setRange(0, strength_data.b_limit)  # 根据限制更新范围
                self.b_channel_slider.setValue(strength_data.b)
                self.b_channel_slider.blockSignals(False)
                self.b_channel_label.setText(
                    f"B通道强度: {strength_data.b}/{strength_data.b_limit}")


    def update_qrcode(self, qrcode_pixmap):
        """更新二维码显示"""
        self.qrcode_image_label.setPixmap(qrcode_pixmap)
        self.qrcode_image_label.setFixedSize(qrcode_pixmap.size())  # 根据二维码尺寸调整标签大小
        logger.info("二维码已更新")