#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""插件系统异常模块"""


class PluginError(Exception):
    """插件系统的基础异常类"""
    pass


class PluginLoadError(PluginError):
    """插件加载失败异常
    
    当插件无法被正确加载时抛出此异常。
    """
    pass


class PluginExecutionError(PluginError):
    """插件执行错误异常
    
    当插件执行过程中出现错误时抛出此异常。
    """
    pass


class PluginRegistrationError(PluginLoadError):
    """插件注册错误异常
    
    当插件无法被正确注册时抛出此异常。
    """
    pass


class PluginDependencyError(PluginLoadError):
    """插件依赖错误异常
    
    当插件依赖项缺失或不满足时抛出此异常。
    """
    pass


class PluginConfigError(PluginError):
    """插件配置错误异常
    
    当插件配置无效或缺失时抛出此异常。
    """
    pass


class EventError(PluginError):
    """事件系统错误异常
    
    当事件系统出现错误时抛出此异常。
    """
    pass


class EventNotFoundError(EventError):
    """事件未找到异常
    
    当尝试访问不存在的事件时抛出此异常。
    """
    pass


class CommandError(PluginError):
    """命令系统错误异常
    
    当命令系统出现错误时抛出此异常。
    """
    pass


class CommandNotFoundError(CommandError):
    """命令未找到异常
    
    当尝试执行不存在的命令时抛出此异常。
    """
    pass


class PluginDisabledError(PluginExecutionError):
    """插件已禁用异常
    
    当尝试在禁用状态下执行插件功能时抛出此异常。
    """
    pass


class ControllerError(PluginError):
    """控制器错误异常
    
    当与控制器交互时出现错误时抛出此异常。
    """
    pass


class InvalidParameterError(PluginError):
    """无效参数异常
    
    当提供的参数无效时抛出此异常。
    """
    pass