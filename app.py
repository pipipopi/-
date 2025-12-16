from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import pandas as pd
import os

app = Flask(__name__)

# --- 設定區 (請修改這裡) ---

# 1. 貼上你剛剛複製的 Google Sheets CSV 網址
CSV_URL = 'https://docs.google.com/spreadsheets/d/1s9mB7ubw40rf_lyvaTX2bEMSPRZ1rDMWBTRVTqHXysY/edit?usp=sharing'

# 2. 貼上你的座位圖 Imgur 網址 (必須是 .jpg 或 .png 結尾)
MAP_IMAGE_URL = 'https://meee.com.tw/gtC5RGo'

# 3. 這裡先不用改，等一下去 Render 設定環境變數即可
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# --- 核心功能區 ---

def search_guest(name):
    try:
        # 每次查詢都重新讀取 Google Sheets，確保資料最新
        df = pd.read_csv(CSV_URL)
        
        # 清理資料：去除空格、統一轉字串
        df['姓名'] = df['姓名'].astype(str).str.strip()
        df['桌號'] = df['桌號'].astype(str).str.strip()
        
        # 搜尋 (忽略大小寫)
        target = name.strip()
        result = df[df['姓名'] == target]
        
        if not result.empty:
            # 找到人了，回傳桌號
            return result.iloc[0]['桌號']
        else:
            return None
    except Exception as e:
        print(f"讀取錯誤: {e}")
        return "ERROR"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_input = event.message.text.strip()
    
    # 執行搜尋
    table_number = search_guest(user_input)
    
    if table_number == "ERROR":
        reply_text = "系統讀取名單發生錯誤，請稍後再試，或是聯繫現場招待人員。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        
    elif table_number:
        # 找到了！回傳文字 + 圖片
        text_msg = f"歡迎 {user_input}！\n您的座位在【 第 {table_number} 桌 】。\n請參考下方座位圖入座，祝您用餐愉快！"
        
        line_bot_api.reply_message(
            event.reply_token,
            [
                TextSendMessage(text=text_msg),
                ImageSendMessage(original_content_url=MAP_IMAGE_URL, preview_image_url=MAP_IMAGE_URL)
            ]
        )
    else:
        # 找不到
        reply_text = f"抱歉，名單中找不到「{user_input}」。\n請確認輸入的是中文全名 (例如: 王小明)。\n如有疑問請詢問現場招待人員。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run()
