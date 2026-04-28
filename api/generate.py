from http.server import BaseHTTPRequestHandler
import json
from openai import OpenAI

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 設置 HTTP 回應標頭
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        # 讀取前端傳來的資料
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.wfile.write(json.dumps({"error": "沒有收到請求資料"}).encode('utf-8'))
            return
            
        post_data = self.rfile.read(content_length)
        req_body = json.loads(post_data.decode('utf-8'))
        
        # 取得前端傳來的提示詞與 API Key
        prompt = req_body.get('prompt', '')
        api_key = req_body.get('apiKey', '').strip()

        if not api_key:
            self.wfile.write(json.dumps({"error": "請提供有效的 API 金鑰"}).encode('utf-8'))
            return
            
        if not prompt:
            self.wfile.write(json.dumps({"error": "請輸入提示詞"}).encode('utf-8'))
            return

        try:
            # 使用用戶提供的 API Key 進行初始化
            client = OpenAI(
                api_key=api_key, 
                base_url="https://api.banana2556.com/v1"
            )
            
            # 呼叫模型
            response = client.images.generate(
                model="gpt-image-2",
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            
            image_data = response.data[0]
            result = {}
            
            if image_data.b64_json:
                result['image'] = f"data:image/png;base64,{image_data.b64_json}"
            elif image_data.url:
                result['image'] = image_data.url
                
            self.wfile.write(json.dumps(result).encode('utf-8'))
            
        except Exception as e:
            # 如果金鑰無效或額度不足，這裡會將錯誤訊息傳回給前端顯示
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))