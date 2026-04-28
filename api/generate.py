from http.server import BaseHTTPRequestHandler
import json
import socket
import urllib.request
import urllib.error

UPSTREAM_TIMEOUT_SECONDS = 85

class handler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode('utf-8'))

    def do_OPTIONS(self):
        self._send_json(200, {})

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except ValueError:
            self._send_json(400, {"error": "Content-Length 格式錯誤"})
            return

        if content_length == 0:
            self._send_json(400, {"error": "沒有收到請求資料"})
            return

        try:
            post_data = self.rfile.read(content_length)
            req_body = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_json(400, {"error": "請求資料不是有效的 JSON"})
            return
        
        # 提取所有參數，並給予預設值
        api_key = req_body.get('apiKey', '').strip()
        user_prompt = req_body.get('prompt', '')
        size = req_body.get('size', 'auto')
        output_format = req_body.get('format', 'png')
        quality = req_body.get('quality', 'high')
        moderation = req_body.get('moderation', 'low')
        n_count = req_body.get('n', 1)
        is_strict = req_body.get('strict', True)

        if not api_key or not user_prompt:
            self._send_json(400, {"error": "缺少 API 金鑰或提示詞"})
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
            "quality": quality,
            "n": n_count
        }

        # 👇 就是這裡！加上 User-Agent 偽裝成 Chrome 瀏覽器
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        request = urllib.request.Request(
            url="https://api.banana2556.com/v1/images/generations",
            data=json.dumps(api_payload).encode('utf-8'),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=UPSTREAM_TIMEOUT_SECONDS) as response:
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
                    self._send_json(200, {"images": images})
                else:
                    self._send_json(502, {"error": "伺服器成功回應，但找不到圖片資料", "upstream": response_data})
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8', errors='replace')
            if e.code == 524:
                self._send_json(504, {
                    "error": "圖片生成逾時",
                    "details": "上游服務回傳 524。請先用 1 張、Low 或 Medium 品質、較短提示詞重試；High 品質可能需要更久。"
                })
                return
            self._send_json(e.code, {"error": f"上游 API 回傳 {e.code}", "details": error_body})
        except (TimeoutError, socket.timeout):
            self._send_json(504, {
                "error": "圖片生成逾時",
                "details": f"上游服務超過 {UPSTREAM_TIMEOUT_SECONDS} 秒仍未完成。請先用 1 張、Low 或 Medium 品質重試。"
            })
        except Exception as e:
            self._send_json(502, {"error": "生成服務連線失敗", "details": str(e)})