import argparse
import json

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Call local Douyin DM demo endpoints")
    parser.add_argument("--base-url", default="http://127.0.0.1:8081")
    parser.add_argument("--path", required=True, help="Local API path, for example /douyin/get-auth-url")
    parser.add_argument("--payload", required=True, help="Path to a JSON payload file")
    args = parser.parse_args()

    with open(args.payload, "r", encoding="utf-8") as f:
        payload = json.load(f)

    resp = requests.post(
        f"{args.base_url}{args.path}",
        json=payload,
        timeout=30,
    )
    print("status:", resp.status_code)
    print(resp.text)


if __name__ == "__main__":
    main()
