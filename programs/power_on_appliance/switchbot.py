import asyncio
import threading
import time
from bleak import BleakScanner, BleakClient


# ========================================
# SwitchBotデバイスを制御するクラス
# ========================================

class SwitchBot:
    
    # SwitchBot BLE定数
    SERVICE_UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
    CHAR_UUID = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
    
    # コマンド
    COMMAND_ON = bytearray([0x57, 0x01, 0x01])
    COMMAND_OFF = bytearray([0x57, 0x01, 0x02])
    
    def __init__(self, address=None):
        """
        SwitchBotインスタンスを初期化
        
        Args:
            address: SwitchBotのBLEアドレス（Noneの場合は自動検出）
        """
        self.address = address
        self.off_time = None
        self.timer_lock = threading.Lock()
        self.timer_thread = None
    
    @classmethod
    async def scan_devices(cls, timeout=5.0) -> list:
        """
        SwitchBotデバイスをスキャン
        
        Args:
            timeout: スキャンのタイムアウト時間（秒）
        
        Returns:
            list: 検出されたSwitchBotデバイスのリスト
        """
        print(f"Scanning for bluetooth devices... (timeout: {timeout}s)")
        devices = await BleakScanner.discover(timeout=timeout)
        
        found_devices = []
        
        for device in devices:
            try:
                print(f"Checking device: {device.address} | {device.name or 'Unknown'}")
                
                async with BleakClient(device.address, timeout=5.0) as client:
                    if client.is_connected:
                        services = [service.uuid for service in client.services]
                        
                        if cls.SERVICE_UUID in services:
                            print(f"✓ Target device found: {device.address} | {device.name}")
                            found_devices.append({
                                'address': device.address,
                                'name': device.name or 'Unknown',
                                'rssi': getattr(device, 'rssi', None)
                            })
            except Exception as e:
                print(f"ERROR checking {device.address}: {str(e)}")
                print("Keep scanning...")
        
        return found_devices
    
    @classmethod
    async def auto_detect(cls):
        """
        最初に見つかったSwitchBotデバイスを自動検出してインスタンス化
        
        Returns:
            SwitchBot: SwitchBotインスタンス、見つからない場合はNone
        """
        print("SwitchBot Auto-Detection Starting...")
        switchbots = await cls.scan_devices(timeout=5.0)
        
        if len(switchbots) == 0:
            print("\n❌ No SwitchBot devices found!")
            return None
        
        print(f"\n{'=' * 50}")
        print(f"Found {len(switchbots)} SwitchBot device(s):")
        print(f"{'=' * 50}")
        
        for i, sb in enumerate(switchbots, 1):
            print(f"{i}. Address: {sb['address']}")
            print(f"   Name: {sb['name']}")
            print()
        
        return cls(address=switchbots[0]['address'])
    
    async def send_command(self, command):
        """
        SwitchBotにコマンドを送信
        
        Args:
            command: 送信するコマンド（bytearray）
        
        Returns:
            bool: 成功時True、失敗時False
        """
        if not self.address:
            print("Error: No address set")
            return False
        
        try:
            async with BleakClient(self.address, timeout=10.0) as client:
                if not client.is_connected:
                    print(f"Failed to connect to {self.address}")
                    return False
                
                char = client.services.get_characteristic(self.CHAR_UUID)
                if not char:
                    print("Characteristic not found")
                    return False
                
                await client.write_gatt_char(char, command, response=True)
                
                if command == self.COMMAND_ON:
                    print("✓ SwitchBot turned ON")
                elif command == self.COMMAND_OFF:
                    print("✓ SwitchBot turned OFF")
                else:
                    print("✓ SwitchBot pressed")
                
                return True
            
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    async def turn_on(self):
        """SwitchBotをONにする"""
        return await self.send_command(self.COMMAND_ON)
    
    async def turn_off(self):
        """SwitchBotをOFFにする"""
        return await self.send_command(self.COMMAND_OFF)
    
    def _timer_worker(self):
        """タイマースレッドのワーカー関数"""
        
        print(f"Timer thread started for {self.address}")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # ONにする
            loop.run_until_complete(self.turn_on())
            
            # OFF時刻を監視
            while True:
                current_time = time.time()
                
                with self.timer_lock:
                    if self.off_time is None:
                        print("Timer thread stopping (no off_time)")
                        break
                    
                    off_time = self.off_time
                
                # OFF時刻に到達したかチェック
                if current_time >= off_time:
                    print("OFF time reached, turning off switchbot")
                    loop.run_until_complete(self.turn_off())
                    
                    with self.timer_lock:
                        self.off_time = None
                    
                    break
                
                # 0.1秒ごとにチェック
                time.sleep(0.1)
        
        except Exception as e:
            print(f"[ERROR] Timer thread exception: {e}")
            import traceback
            traceback.print_exc()
        finally:
            loop.close()
    
    def switch_on_with_timer(self, duration_seconds):
        """
        SwitchBotをONにして、指定時間後に自動でOFFにする
        
        Args:
            duration_seconds: ON状態を保つ秒数
        """
        new_off_time = time.time() + duration_seconds
        
        with self.timer_lock:
            is_new_timer = self.off_time is None
            self.off_time = new_off_time
        
        if is_new_timer:
            print("Starting new timer thread")
            self.timer_thread = threading.Thread(
                target=self._timer_worker,
                daemon=True
            )
            self.timer_thread.start()
        else:
            print(f"Extended timer by {duration_seconds} seconds")
    
    def stop_timer(self):
        """タイマーを停止する"""

        with self.timer_lock:
            self.off_time = None
        print("Timer stopped")
        