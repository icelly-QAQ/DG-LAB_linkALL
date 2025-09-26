# ton_websocket_handler.py
import asyncio
import websockets
import json
import logging
from PySide6.QtCore import Signal, QObject
import qrcode
import io
from PySide6.QtCore import QBuffer, QByteArray
from PySide6.QtGui import QPixmap
import qrcode

logger = logging.getLogger(__name__)

def generate_qrcode(url):
    # 创建QR码对象
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    # 获取PIL图像
    pil_img = qr.make_image(fill='black', back_color='white')
    # 将PIL图像转换为字节
    buffer = io.BytesIO()
    pil_img.save(buffer, format="PNG")
    buffer.seek(0)
    # 创建QPixmap并从字节数据加载
    pixmap = QPixmap()
    pixmap.loadFromData(buffer.read())
    return pixmap

class WebSocketClient(QObject):
    status_update_signal = Signal(str)
    message_received = Signal(str)
    error_signal = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.websocket = None

    async def start_connection(self):
        """Starts the WebSocket connection and listens for messages."""
        try:
            async with websockets.connect(self.url) as ws:
                self.websocket = ws
                async for message in ws:
                    # Process received message
                    await self.process_message(message)
        except Exception as e:
            self.error_signal.emit(f"WebSocket connection error: {e}")

    async def process_message(self, message):
        """Process the received WebSocket message and parse JSON."""
        logger.info(message)
        try:
            # 直接解析收到的消息，不添加 'Received: ' 前缀
            json_data = json.loads(message)

            self.message_received.emit(f"{json.dumps(json_data, indent=4)}")
            self.status_update_signal.emit("connected")

            # # Process based on message type
            # if json_data.get("type") == "STATS":
            #     stats_data = json_data.get("data", {})
            #     formatted_stats = "\n".join([f"{key}: {value}" for key, value in stats_data.items()])
            #     self.status_update_signal.emit(f"STATS Update:\n{formatted_stats}")
            # else:
            #     # Emit the full JSON formatted message for other types
            #     self.status_update_signal.emit(f"{json.dumps(json_data, indent=4)}")
        except json.JSONDecodeError:
            # 如果消息不是 JSON 格式，显示原始消息
            logger.warning("ws message is not json format")
            self.message_received.emit(message)
            self.status_update_signal.emit("error")

    async def close(self):
        """Close the WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
            self.status_update_signal.emit("disconnected")
