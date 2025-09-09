from flask import Flask, request, jsonify
import requests
import re
import dns.resolver

app = Flask(__name__)

def resolve_domain(domain, dns_server="8.8.8.8"):
    """Resolve a domain to an IP address using a specified DNS server."""
    try:
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [dns_server]
        answers = resolver.resolve(domain, 'A')
        return [answer.address for answer in answers][0]
    except Exception as e:
        return None

def extract_resource_id(url):
    """Extract resource ID from Freepik URL."""
    match = re.search(r'[\w-]+_(\d+)', url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Could not extract resource ID from the provided URL")

def fetch_freepik_asset(resource_id, api_key):
    """Fetch Freepik resource details by ID."""
    domain = "api.freepik.com"
    url = f"https://{domain}/v1/resources/{resource_id}/download"
    headers = {"x-freepik-api-key": api_key}

    # Try resolving domain with system DNS first, then fallback to Google DNS
    ip = resolve_domain(domain) or resolve_domain(domain, "8.8.8.8")
    if not ip:
        return {"error": "Could not resolve api.freepik.com. Check DNS settings or network."}

    try:
        # Make API request with timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'data' in data and 'url' in data['data'] and 'filename' in data['data']:
            return {
                "status": "success",
                "resource_id": resource_id,
                "filename": data['data']['filename'],
                "download_url": data['data']['url'],
                "full_response": data,
                "API Developer": "@ISmartCoder"
            }
        else:
            return {
                "status": "error",
                "message": "No download URL or filename found in the response",
                "full_response": data
            }

    except requests.exceptions.DNSFailure:
        return {"status": "error", "message": "DNS resolution error. Try setting DNS to 8.8.8.8 or 1.1.1.1 in network settings."}
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Request timed out. Check your internet connection or try again later."}
    except requests.exceptions.HTTPError as e:
        return {"status": "error", "message": f"HTTP error: {str(e)}", "response": e.response.text}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Connection error. Ensure you are connected to the internet and 'api.freepik.com' is accessible."}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

@app.route('/', methods=['GET'])
def welcome():
    """Welcome endpoint with API usage instructions."""
    return jsonify({
        "status": "success",
        "message": "Welcome to Freepik Download API!",
        "usage": "Use the /dl endpoint with a Freepik URL: /dl?url=<freepik_resource_url>",
        "example": "/dl?url=https://www.freepik.com/vectors/abstract-background_1234567",
        "developer": "@ISmartCoder"
    })

@app.route('/dl', methods=['GET'])
def freepik_api():
    """API endpoint to fetch Freepik resource details via GET request."""
    freepik_url = request.args.get('url')
    if not freepik_url:
        return jsonify({"status": "error", "message": "Missing 'url' query parameter"}), 400

    api_key = "FPSXaff6e6683c2a51a3980262f6fc9653fc"  # Hardcoded for simplicity; consider using environment variables

    try:
        # Extract resource ID
        resource_id = extract_resource_id(freepik_url)
        # Fetch asset details
        result = fetch_freepik_asset(resource_id, api_key)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')