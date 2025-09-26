# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


# 分析项目文件和依赖
a = Analysis(['src/main.py'],
             pathex=['.'],
             binaries=[],
             datas=[],
             hiddenimports=[
                 'src.dglab_controller', 
                 'src.gui.controller_settings_tab', 
                 'pydglab_ws', 
                 'qasync',
                 'socket',
                 'asyncio',
                 'qrcode',
                 'PySide6',
                 'PySide6.QtWidgets',
                 'PySide6.QtCore',
                 'PySide6.QtGui'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=['PyQt5'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# 创建可执行文件
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='DG-LAB_Controller',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,  # 设置为True以便查看控制台输出
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None)

# 收集所有文件到一个目录
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='DG-LAB_Controller')