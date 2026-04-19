import time
import socket
import threading
import os
import http.server
import socketserver
from typing import Optional

import pychromecast
from pychromecast.controllers.media import MediaStatusListener
from fastapi import FastAPI
import uvicorn

# --- 設定 ---
TARGET_FILE_PATH = r"/home/ry0/Music/White_Noise_for_Babies.mp3"
CHROMECAST_NAME = "ベッドルーム" #"ダイニング ルーム" 
FILE_SERVER_PORT = 9100
API_SERVER_PORT = 9101
# ----------
app = FastAPI()

class ChromecastManager(MediaStatusListener):
    def __init__(self, device_name: str, file_path: str):
        self.device_name = device_name
        self.file_path = file_path
        self.file_dir = os.path.dirname(os.path.abspath(file_path))
        self.file_name = os.path.basename(file_path)
        
        self.cast: Optional[pychromecast.Chromecast] = None
        self.browser: Optional[pychromecast.discovery.CastBrowser] = None
        self.status = "STOPPED"

    def _init_chromecast(self):
        try:
            print(f"'{self.device_name}' を探索中...")
            chromecasts, browser = pychromecast.get_chromecasts()
            cast = next((cc for cc in chromecasts if cc.name == self.device_name), None)
            
            if not cast:
                print("デバイスが見つかりませんでした。")
                browser.stop_discovery()
                return
            
            cast.wait()
            
            # --- リスナーの登録 ---
            # 1. メディア（再生・停止など）のリスナー
            cast.media_controller.register_status_listener(self)
            # 2. 接続状態（ネットワーク切断など）のリスナーを追加！
            cast.register_connection_listener(self)
            
            if self.browser:
                self.browser.stop_discovery()
                
            self.cast = cast
            self.browser = browser
            print(f"'{self.device_name}' に接続完了")
        except Exception as e:
            print(f"初期化エラー: {e}")
            self.status = "STOPPED"
            self.cast = None

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip

    # ==========================================
    # --- Listener Callbacks (イベント検知) ---
    # ==========================================

    def new_media_status(self, status):
        """Chromecast側から再生状態が変わった時に呼ばれる"""
        if status.player_state in ["PLAYING", "BUFFERING"]:
            self.status = "PLAYING"
        else:
            self.status = "STOPPED"
        print(f"Media State Changed: {status.player_state}")

    def new_connection_status(self, connection_status):
        """Chromecastとの接続状態が変わった時に呼ばれる (新規追加)"""
        print(f"Connection Status Changed: {connection_status.status}")
        # 'DISCONNECTED' や 'CONNECTING', 'CONNECTED' などが返ります
        if connection_status.status == "DISCONNECTED":
            print("デバイスから切断されました。内部ステータスをリセットします。")
            self.cast = None
            self.status = "STOPPED"

    # ==========================================
    # --- Control Methods (APIからの操作) ---
    # ==========================================

    def play(self):
        self.status = "PLAYING"
        # リスナーによって self.cast が None になっていれば再接続が走る
        if not self.cast:
            print("デバイス未接続。再接続を試みます...")
            self._init_chromecast()
            
        if not self.cast:
            self.status = "STOPPED"
            return {"error": "Device not found or cannot connect", "status": self.status}
        
        try:
            self.cast.wait()
            local_ip = self.get_local_ip()
            url = f"http://{local_ip}:{FILE_SERVER_PORT}/{self.file_name}"
            
            print(f"再生を試みます: {url}")
            self.cast.media_controller.play_media(url, "audio/mp3")
            return {"message": "Started playing", "url": url}
            
        except Exception as e:
            print(f"Play Error: {e}")
            self.status = "STOPPED"
            self.cast = None
            return {"error": str(e), "status": self.status}

    def stop(self):
        if not self.cast:
            self.status = "STOPPED"
            return {"error": "Device not connected", "status": self.status}
        
        try:
            self.cast.media_controller.stop()
            time.sleep(0.5)
            self.cast.quit_app()
            print("停止し、アプリを終了しました。")
        except Exception as e:
            print(f"Stop Error: {e}")
            self.cast = None
        finally:
            self.status = "STOPPED"
            return {"message": "Stopped and quit app", "status": self.status}


# --- バックグラウンドのファイルサーバー ---
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def handle(self):
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

def start_file_server(directory):
    os.chdir(directory)
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", FILE_SERVER_PORT), QuietHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print(f"File Server Error: {e}")


manager = ChromecastManager(CHROMECAST_NAME, TARGET_FILE_PATH)
threading.Thread(target=start_file_server, args=(manager.file_dir,), daemon=True).start()

# --- API Endpoints ---
@app.get("/play")
def api_play(): return manager.play()

@app.get("/stop")
def api_stop(): return manager.stop()

@app.get("/status")
def api_status(): return {"status": manager.status}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=API_SERVER_PORT)