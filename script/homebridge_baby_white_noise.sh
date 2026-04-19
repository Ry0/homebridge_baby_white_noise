#!/bin/bash

# $1 = Action (Get / Set)
# $2 = displayName (アクセサリ名)
# $3 = Characteristic (On など)
# $4 = Value (Setの場合のみ: 1 / 0)

# --- 設定 ---
# 先ほど作成したPython APIサーバーのURL
# (Homebridgeと同じCM4上で動かしている場合は 127.0.0.1)
API_BASE_URL="http://127.0.0.1:9101"
# -----------

# ---------------------------------------------------------
# Get: 現在のステータス確認 (ポーリング時)
# ---------------------------------------------------------
if [ "$1" = "Get" ]; then
    case "$3" in
        "On")
            # 1. APIからステータスを取得 
            # (-m 3 は3秒でタイムアウトさせる設定。Homebridge全体のハングアップを防ぎます)
            RESPONSE=$(curl -s -m 3 "${API_BASE_URL}/status")

            # 2. JSONの中に "PLAYING" という文字列が含まれているかチェック
            if echo "$RESPONSE" | grep -q '"PLAYING"'; then
                # 再生中なら「オン(1)」を返す
                echo 1
            else
                # 停止中、またはサーバーに繋がらない場合は「オフ(0)」を返す
                echo 0
            fi
            ;;
    esac
    exit 0
fi

# ---------------------------------------------------------
# Set: ステータスの変更 (スイッチ操作時)
# ---------------------------------------------------------
if [ "$1" = "Set" ]; then
    case "$3" in
        "On")
            if [ "$4" = "1" ]; then
                # ==============
                # スイッチ ON (再生)
                # ==============
                # APIを叩いて再生を開始
                # (API側で探索・接続に数秒かかる場合があるため、末尾に & をつけてバックグラウンド実行し、Homebridgeにすぐ応答を返します)
                curl -s -m 10 "${API_BASE_URL}/play" > /dev/null &
                exit 0

            else
                # ==============
                # スイッチ OFF (停止)
                # ==============
                # APIを叩いて停止とアプリ終了を実行
                curl -s -m 5 "${API_BASE_URL}/stop" > /dev/null &
                exit 0
            fi
            ;;
    esac
fi