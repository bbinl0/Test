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
        external_api_url = f"https://web-production-27209.up.railway.app/get_user_info?username={username}"
        response = requests.get(external_api_url)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()
        return jsonify(data), 200
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user info: {e}")
        return jsonify({"error": "Failed to fetch user information.", "details": str(e)}), 500

if __name__ == '__main__':
    # This is for local development only. Vercel will handle the WSGI server.
    app.run(debug=True)
