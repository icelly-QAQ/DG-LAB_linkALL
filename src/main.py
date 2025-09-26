#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import asyncio
import os
import socket

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QHBoxLayout, QWidget
from PySide6.QtGui import QIcon, QPixmap
from qasync import QEventLoop
import logging

# 导入GUI模块
from src.gui.controller_settings_tab import ControllerSettingsTab
from src.gui.logger_tab import LoggerTab
from src.gui.plugin_manager_tab import PluginManagerTab
# 导入控制器和二维码生成函数
from src.dglab_controller import DGLabController
from src.ton_websocket_handler import generate_qrcode
from src.command_types import CommandType, Channel
# 导入pydglab_ws库
from pydglab_ws import DGLabWSServer
from pydglab_ws import StrengthOperationType, FeedbackButton, RetCode
# 导入插件系统相关模块
from src.plugin_loader import PluginLoader

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
  """DG-LAB游戏联动控制器主窗口类。

  管理整个应用的界面和功能，包括控制器设置、日志显示和插件管理等选项卡。

  属性:
    controller: DGLabController实例，用于控制DG-LAB设备
    app_status_online: bool，表示App是否在线
    tab_widget: QTabWidget，用于管理多个选项卡
    controller_settings_tab: ControllerSettingsTab，控制器设置选项卡
    logger_tab: LoggerTab，日志显示选项卡
    plugin_manager_tab: PluginManagerTab，插件管理选项卡
    plugin_manager: 插件管理器实例，用于加载和管理插件
  """
  
  def __init__(self):
    """初始化主窗口实例，设置窗口属性和创建UI组件。"""
    super().__init__()
    self.setWindowTitle("DG-LAB 游戏联动控制器")
    self.setGeometry(300, 300, 800, 300)

    # 初始控制器为None
    self.controller = None
    self.app_status_online = False
    self.plugin_manager = None

    # 创建选项卡部件
    self.tab_widget = QTabWidget()
    self.setCentralWidget(self.tab_widget)

    # 创建选项卡并传递MainWindow引用
    self.controller_settings_tab = ControllerSettingsTab(self)
    self.logger_tab = LoggerTab(self)
    self.plugin_manager_tab = PluginManagerTab(self)

    # 将选项卡添加到选项卡部件
    self.tab_widget.addTab(self.controller_settings_tab, "控制器设置")
    self.tab_widget.addTab(self.logger_tab, "控制台日志")
    self.tab_widget.addTab(self.plugin_manager_tab, "插件管理")

  def init_dg_lab_connection(self):
    """初始化DG-Lab设备连接。

    创建WebSocket服务器、获取本地客户端、初始化控制器、生成二维码并启动数据处理循环。
    捕获并记录初始化过程中的所有异常。
    """
    try:
      # 获取本机实际IP地址
      local_ip = socket.gethostbyname(socket.gethostname())
      logger.info(f"获取到本机IP地址: {local_ip}")
      
      # 查找可用端口
      port = 5678
      while True:
        try:
          # 尝试绑定端口以检查可用性
          test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
          test_socket.bind((local_ip, port))
          test_socket.close()
          break  # 端口可用，退出循环
        except socket.error:
          port += 1  # 端口被占用，尝试下一个
      
      logger.info(f"使用可用端口: {port}")
      
      # 创建WebSocket服务器
      self.server = DGLabWSServer(local_ip, port, 60)
      
      # 获取本地客户端
      self.client = self.server.new_local_client()
      
      # 初始化控制器
      controller = DGLabController(self.client, self)
      self.controller = controller
      
      # 绑定控制器设置
      self.controller_settings_tab.bind_controller_settings()
      
      # 加载插件
      logger.info("开始加载插件...")
      self.plugin_loader = PluginLoader()
      self.plugin_manager = self.plugin_loader.load_all_plugins(controller, self)
      # 刷新插件列表
      self.plugin_manager_tab.refresh_plugin_list()
      
      # 刷新插件列表
      self.plugin_manager_tab.refresh_plugin_list()
      
      # 生成二维码，使用实际IP地址和选择的端口
      url = self.client.get_qrcode(f"ws://{local_ip}:{port}")
      # 确保URL使用实际IP而非0.0.0.0
      url = url.replace('ws://0.0.0.0:', f'ws://{local_ip}:')
      logger.info(f"生成二维码URL: {url}")
      
      # 直接使用generate_qrcode返回的QPixmap对象
      qrcode_pixmap = generate_qrcode(url)
      self.controller_settings_tab.update_qrcode(qrcode_pixmap)
      
      # 启动数据处理循环
      loop = asyncio.get_event_loop()
      loop.create_task(self.initialize_controller_async_components(controller))
      loop.create_task(self.run_data_loop())
      
      logger.info("DG-Lab连接初始化完成，请使用郊狼App扫描二维码进行连接")
    except Exception as e:
      import traceback
      logger.error(f"初始化DG-Lab连接时出错: {e}")
      logger.error(f"错误堆栈: {traceback.format_exc()}")

  async def initialize_controller_async_components(self, controller):
    """初始化控制器的异步组件。

    参数:
      controller: DGLabController实例
    """
    await controller.initialize_async_components()



  async def run_data_loop(self):
    """运行数据处理循环。

    使用上下文管理器启动服务器，等待与App绑定，并处理从App接收的数据，
    包括强度数据、反馈按钮事件和断开连接事件。
    """
    try:
      # 使用上下文管理器启动服务器
      async with self.server:
        # 等待绑定
        await self.client.bind()
        logger.info(f"已与 App {self.client.target_id} 成功绑定")
        
        # 启用控制器设置
        self.controller_settings_tab.controller_group.setEnabled(True)
        
        # 通知插件连接状态变化
        if self.plugin_manager:
          self.plugin_manager.notify_connection_status_changed(True)
        
        # 初始化波形数据迭代器
        from src.dglab_controller import PULSE_DATA
        pulse_data_iterator = iter(PULSE_DATA.values())
        
        # 开始接收数据
        async for data in self.client.data_generator():
          # 处理强度数据
          if hasattr(data, 'a') and hasattr(data, 'b'):  # StrengthData
            logger.info(f"接收到强度数据 - A通道: {data.a}/{data.a_limit}, B通道: {data.b}/{data.b_limit}")
            self.controller.last_strength = data
            self.controller.app_status_online = True
            self.app_status_online = True
            # 更新UI显示 - 通过信号在主线程中执行
            self.controller_settings_tab.strength_data_updated.emit(data)
            # 通知插件 - 使用新插件系统的事件机制
            if self.plugin_manager:
              await self.plugin_manager.emit_event("strength_data_received", strength_data=data)
          # 处理反馈按钮
          elif isinstance(data, FeedbackButton):
            logger.info(f"App 触发了反馈按钮：{data.name}")
            
            # 通知插件 - 使用新插件系统的事件机制
            if self.plugin_manager:
              await self.plugin_manager.emit_event("feedback_button_pressed", button_data=data)
            
            # 通过信号更新UI，确保在Qt主线程中执行
            self.controller_settings_tab.strength_data_updated.emit(self.controller.last_strength)
          # 处理断开连接
          elif data == RetCode.CLIENT_DISCONNECTED:
            logger.warning("App 已断开连接")
            self.controller.app_status_online = False
            self.app_status_online = False
            # 禁用控制器设置
            self.controller_settings_tab.controller_group.setEnabled(False)
            # 通知插件 - 使用新插件系统的事件机制
            if self.plugin_manager:
              await self.plugin_manager.emit_event("connection_status_changed", is_connected=False)
            
            # 等待重新绑定
            logger.info("请尝试重新扫码进行连接绑定")
            try:
              await self.client.rebind()
              logger.info("重新绑定成功")
              # 重新启用控制器设置
              self.controller_settings_tab.controller_group.setEnabled(True)
              # 通知插件连接状态变化 - 使用新插件系统的事件机制
              if self.plugin_manager:
                await self.plugin_manager.emit_event("connection_status_changed", is_connected=True)
            except Exception as e:
              logger.error(f"重新绑定失败: {e}")
    except Exception as e:
      logger.error(f"连接过程中出错: {e}")
      # 禁用控制器设置
      self.controller_settings_tab.controller_group.setEnabled(False)

  def update_channel_display(self, strength_data):
    """更新通道显示信息。

    参数:
      strength_data: StrengthData实例，包含通道强度信息
    """
    self.controller_settings_tab.update_channel_strength_labels(strength_data)
    
  def closeEvent(self, event):
    """关闭窗口时的事件处理。

    确保在应用程序退出时正确关闭所有插件。

    参数:
      event: QCloseEvent，关闭事件
    """
    logger.info("应用程序正在关闭，正在清理插件...")
    
    # 禁用并清理所有插件 - 使用新插件系统
    if self.plugin_manager:
      try:
        # 使用事件循环运行异步禁用插件的操作
        loop = asyncio.get_event_loop()
        if loop.is_running():
          # 创建一个任务来禁用插件
          disable_task = asyncio.create_task(self.plugin_manager.disable_all_plugins())
          
          # 尝试等待任务完成，但设置超时以防任务卡住
          try:
            # 使用asyncio.run_coroutine_threadsafe将等待操作提交到事件循环
            future = asyncio.run_coroutine_threadsafe(asyncio.wait_for(disable_task, timeout=2.0), loop)
            # 等待结果，最多等待2秒
            future.result(timeout=2.0)
          except (asyncio.TimeoutError, Exception):
            # 如果超时或出错，至少确保任务在后台继续执行
            logger.warning("禁用插件的操作超时，将在后台继续完成")
        else:
          # 如果事件循环没有运行，直接运行直到完成
          loop.run_until_complete(self.plugin_manager.disable_all_plugins())
      except Exception as e:
        logger.error(f"禁用插件时出错: {e}")
    
    # 给异步操作一些时间完成
    import time
    time.sleep(0.5)
    
    logger.info("插件清理完成，应用程序正在退出...")
    event.accept()


if __name__ == "__main__":
  """程序入口点。"""
  app = QApplication(sys.argv)
  loop = QEventLoop(app)
  asyncio.set_event_loop(loop)

  window = MainWindow()
  window.show()
  
  # 初始化DG-Lab连接
  window.init_dg_lab_connection()

  with loop:
    loop.run_forever()