from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

@app.route('/api/get_user_info', methods=['GET'])
def get_user_info():
    username = request.args.get('username')

    if not username:
        return jsonify({"error": "Username parameter is required."}), 400

    try:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        external_api_url = f"https://web-production-27209.up.railway.app/get_user_info?username={username}"
        response = requests.get(external_api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        text_data = response.text
        return text_data, 200, {'Content-Type': 'text/plain'}
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user info: {e}")
        return f"Failed to fetch user information. Details: {str(e)}", 500, {'Content-Type': 'text/plain'}

if __name__ == '__main__':
    # This is for local development only. Vercel will handle the WSGI server.
    app.run(debug=True)
