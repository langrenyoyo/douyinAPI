import argparse
import hashlib
import json
import time

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a signed Douyin webhook request to local demo")
    parser.add_argument("--url", default="http://127.0.0.1:8081/webhook/douyin")
    parser.add_argument("--secret", required=True)
    parser.add_argument("--payload", default="sample_webhook_payload.json")
    args = parser.parse_args()

    with open(args.payload, "r", encoding="utf-8") as f:
        payload = json.load(f)

    body_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = str(int(time.time()))
    signature = hashlib.sha256((args.secret + body_text + "-" + timestamp).encode("utf-8")).hexdigest()

    resp = requests.post(
        args.url,
        data=body_text.encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Auth-Timestamp": timestamp,
            "Authorization": signature,
        },
        timeout=20,
    )
    print("status:", resp.status_code)
    print(resp.text)


if __name__ == "__main__":
    main()
