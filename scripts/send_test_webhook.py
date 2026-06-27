#!/usr/bin/env python3
"""Simple script to POST a test Stripe-like webhook event to your local webhook endpoint.

Usage:
  python scripts/send_test_webhook.py --url http://localhost:8000/api/v1/webhooks/stripe --local-payment-id 1

If you use `STRIPE_WEBHOOK_SECRET` on the backend, use the Stripe CLI or ngrok instead.
"""
import argparse
import json
import requests


def build_event(local_payment_id: str, provider_payment_id: str = "in_test_123"):
    return {
        "id": "evt_test_123",
        "object": "event",
        "type": "invoice.payment_succeeded",
        "data": {
            "object": {
                "id": provider_payment_id,
                "metadata": {"local_payment_id": str(local_payment_id)},
            }
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://localhost:8000/api/v1/webhooks/stripe", help="Webhook endpoint URL")
    p.add_argument("--local-payment-id", default="1", help="Local payment id stored in DB")
    p.add_argument("--provider-payment-id", default="in_test_123", help="Simulated provider payment id")
    args = p.parse_args()

    event = build_event(args.local_payment_id, args.provider_payment_id)
    headers = {"Content-Type": "application/json"}

    print(f"POSTing test event to {args.url}")
    r = requests.post(args.url, headers=headers, data=json.dumps(event))
    print("status:", r.status_code)
    try:
        print(r.json())
    except Exception:
        print(r.text)


if __name__ == "__main__":
    main()
