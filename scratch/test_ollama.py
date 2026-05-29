import urllib.request
import json
import traceback

host = "http://127.0.0.1:11434"
models = ["qwen2.5:7b-instruct", "qwen2.5:3b", "qwen2.5:1.5b"]

for model in models:
    print(f"\n--- Testing model: {model} ---")
    request_body = {
        "model": model,
        "prompt": "Say 'hello world' in one word.",
        "stream": False,
    }

    request = urllib.request.Request(
        url=f"{host}/api/generate",
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        print("Sending request...")
        with urllib.request.urlopen(request, timeout=20) as response:
            print("Status:", response.status)
            payload = json.loads(response.read().decode("utf-8"))
            print("Response:", payload.get("response"))
    except urllib.error.HTTPError as he:
        print(f"HTTP Error {he.code}: {he.reason}")
        try:
            print("Error body:", he.read().decode("utf-8"))
        except:
            pass
    except Exception as e:
        print("Error occurred:")
        traceback.print_exc()
