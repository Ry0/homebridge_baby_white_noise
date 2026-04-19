import time
import socket
import threading
import http.server
import socketserver
import pychromecast
import os
import sys

# --- 設定 ---
# 再生したいファイルのフルパスを指定してください
# Windows の場合は r"C:\path\to\music.mp3" のように r を付けると安全です
TARGET_FILE_PATH = r"/home/ry0/Music/White_Noise_for_Babies.mp3" 
CHROMECAST_NAME = "ダイニング ルーム"
PORT = 8102

def get_local_ip():
    """自分のPCのローカルIPアドレスを取得する"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip

def start_server(directory):
    """指定されたディレクトリをルートとしてHTTPサーバーを起動する"""
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        # ログ出力（アクセス記録）を少し静かにする設定
        def log_message(self, format, *args):
            print(f"Server Log: {format % args}")

    # 指定したディレクトリに移動してサーバーを実行
    os.chdir(directory)
    handler = QuietHandler
    
    # allow_reuse_address を有効にして、再起動時のエラーを防ぐ
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"HTTP Server: Serving {directory} at port {PORT}")
        httpd.serve_forever()

def play_local_file():
    # 1. パスの解析
    if not os.path.exists(TARGET_FILE_PATH):
        print(f"エラー: ファイルが見つかりません: {TARGET_FILE_PATH}")
        return

    # ディレクトリ部分とファイル名部分に分ける
    file_dir = os.path.dirname(os.path.abspath(TARGET_FILE_PATH))
    file_name = os.path.basename(TARGET_FILE_PATH)

    # 2. サーバーを別スレッドで起動（ファイルがあるディレクトリを公開）
    server_thread = threading.Thread(target=start_server, args=(file_dir,), daemon=True)
    server_thread.start()
    time.sleep(1) # サーバー起動待ち

    # 3. URLの生成
    local_ip = get_local_ip()
    file_url = f"http://{local_ip}:{PORT}/{file_name}"
    print(f"Cast URL: {file_url}")

    # 4. Chromecastの準備
    print(f"'{CHROMECAST_NAME}' を探索中...")
    chromecasts, browser = pychromecast.get_chromecasts()
    cast = next((cc for cc in chromecasts if cc.name == CHROMECAST_NAME), None)

    if not cast:
        print("デバイスが見つかりませんでした。")
        browser.stop_discovery()
        return

    cast.wait()
    mc = cast.media_controller

    # 5. 再生実行
    print("Chromecast にコマンド送信中...")
    # コンテンツタイプは拡張子から判断（簡易的に mp3/wav/mpeg に対応）
    ext = os.path.splitext(file_name)[1].lower()
    mime = "audio/mp3" if ext == ".mp3" else "audio/wav" if ext == ".wav" else "audio/mpeg"
    
    mc.play_media(file_url, mime)
    mc.block_until_active()

    print("5秒間再生します...")
    time.sleep(5)

    print("停止中...")
    mc.stop()
    cast.quit_app()
    
    # 探索を終了
    browser.stop_discovery()
    print("完了。")

if __name__ == "__main__":
    play_local_file()


