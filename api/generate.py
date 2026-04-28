from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 設置 HTTP 回應標頭 (CORS)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.wfile.write(json.dumps({"error": "沒有收到請求資料"}).encode('utf-8'))
            return
            
        post_data = self.rfile.read(content_length)
        req_body = json.loads(post_data.decode('utf-8'))
        
        # 提取所有參數，並給予預設值
        api_key = req_body.get('apiKey', '').strip()
        user_prompt = req_body.get('prompt', '')
        size = req_body.get('size', 'auto')
        output_format = req_body.get('format', 'png')
        moderation = req_body.get('moderation', 'low')
        n_count = req_body.get('n', 1)
        is_strict = req_body.get('strict', True)

        if not api_key or not user_prompt:
            self.wfile.write(json.dumps({"error": "缺少 API 金鑰或提示詞"}).encode('utf-8'))
            return

        # 根據用戶選擇，決定是否加上「強制不改寫」的魔法咒語
        final_prompt = user_prompt
        if is_strict:
            final_prompt = f"Use the following text as the complete prompt. Do not rewrite it:\n{user_prompt}"
        
        # 建構完整的自訂 Payload
        api_payload = {
            "model": "gpt-image-2",
            "prompt": final_prompt,
            "size": size,
            "output_format": output_format,
            "moderation": moderation,
            "n": n_count
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        request = urllib.request.Request(
            url="https://api.banana2556.com/v1/images/generations",
            data=json.dumps(api_payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(request) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                
                # 處理可能回傳的多張圖片 (因為 n 可能大於 1)
                images = []
                data_list = response_data.get('data', [])
                
                for item in data_list:
                    if item.get('b64_json'):
                        images.append(f"data:image/{output_format};base64,{item['b64_json']}")
                    elif item.get('url'):
                        images.append(item['url'])
                
                if images:
                    self.wfile.write(json.dumps({"images": images}).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({"error": "伺服器成功回應，但找不到圖片資料"}).encode('utf-8'))
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            self.wfile.write(json.dumps({"error": f"API 錯誤: {error_body}"}).encode('utf-8'))
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))