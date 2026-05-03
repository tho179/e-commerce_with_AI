import json
import os
import time

import pika
import requests

AISERVICE_URL = os.getenv("AISERVICE_URL", "http://ai-service:8000")
SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
REVIEW_EVENT_QUEUE = os.getenv("REVIEW_EVENT_QUEUE", "review.events")
EVENT_BATCH_SIZE = int(os.getenv("RETRAIN_BATCH_SIZE", "12"))


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


def _trigger_retrain(source, note=""):
    payload = {"source": source}
    if note:
        payload["note"] = note

    try:
        response = requests.post(
            f"{AISERVICE_URL}/ai/retrain/",
            json=payload,
            timeout=8,
            headers=_internal_headers(),
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[worker] retrain trigger failed ({source}): {exc}")
        return None

    if not response.content:
        return {}

    try:
        return response.json()
    except ValueError:
        return {}


def main():
    if not RABBITMQ_URL:
        print("[worker] RABBITMQ_URL not configured, stop worker")
        return

    print("[worker] starting review event consumer")

    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
            channel = connection.channel()
            channel.queue_declare(queue=REVIEW_EVENT_QUEUE, durable=True)
            channel.basic_qos(prefetch_count=4)

            state = {"events": 0}

            def _on_message(ch, method, properties, body):
                state["events"] += 1
                event = {}
                try:
                    event = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass

                if state["events"] % EVENT_BATCH_SIZE == 0:
                    note = f"Processed {state['events']} events from queue"
                    snapshot = _trigger_retrain(source="event-batch", note=note)
                    if snapshot:
                        print(f"[worker] snapshot {snapshot.get('id')} created")

                ch.basic_ack(delivery_tag=method.delivery_tag)

            channel.basic_consume(queue=REVIEW_EVENT_QUEUE, on_message_callback=_on_message)
            channel.start_consuming()
        except Exception as exc:
            print(f"[worker] connection error: {exc}")
            time.sleep(5)
        finally:
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
