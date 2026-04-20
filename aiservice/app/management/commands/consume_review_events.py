import json
import os
import time

import pika
import requests
from django.core.management.base import BaseCommand

AISERVICE_URL = os.getenv("AISERVICE_URL", "http://aiservice:8000")
SERVICE_SHARED_TOKEN = os.getenv("SERVICE_SHARED_TOKEN", "")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
REVIEW_EVENT_QUEUE = os.getenv("REVIEW_EVENT_QUEUE", "review.events")
EVENT_BATCH_SIZE = int(os.getenv("RETRAIN_BATCH_SIZE", "12"))


def _internal_headers():
    if not SERVICE_SHARED_TOKEN:
        return {}
    return {"X-Service-Token": SERVICE_SHARED_TOKEN}


class Command(BaseCommand):
    help = "Consume review events and create drift snapshots for periodic retraining"

    def _trigger_retrain(self, source, note=""):
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
            self.stderr.write(f"[worker] retrain trigger failed ({source}): {exc}")
            return None

        if not response.content:
            return {}

        try:
            return response.json()
        except ValueError:
            return {}

    def handle(self, *args, **options):
        if not RABBITMQ_URL:
            self.stderr.write("[worker] RABBITMQ_URL not configured, stop worker")
            return

        self.stdout.write("[worker] starting review event consumer")

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
                        snapshot = self._trigger_retrain(source="event-batch", note=note)
                        if snapshot:
                            self.stdout.write(
                                "[worker] snapshot "
                                f"#{snapshot.get('id')} divergence={snapshot.get('divergence')} "
                                f"retrain={snapshot.get('needs_retrain')}"
                            )

                    if event.get("sentiment_label") == "negative" and float(event.get("sentiment_score", 0.5)) < 0.2:
                        snapshot = self._trigger_retrain(
                            source="negative-spike",
                            note="Detected strong negative review spike from event stream.",
                        )
                        if snapshot:
                            self.stdout.write(f"[worker] negative spike snapshot #{snapshot.get('id')}")

                    ch.basic_ack(delivery_tag=method.delivery_tag)

                channel.basic_consume(queue=REVIEW_EVENT_QUEUE, on_message_callback=_on_message)
                channel.start_consuming()

            except KeyboardInterrupt:
                self.stdout.write("[worker] stopped by user")
                break
            except Exception as exc:
                self.stderr.write(f"[worker] connection error: {exc!r}")
                time.sleep(5)
            finally:
                if connection and connection.is_open:
                    try:
                        connection.close()
                    except Exception:
                        pass
