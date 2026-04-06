import json
import os

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "")
REVIEW_EVENT_QUEUE = os.getenv("REVIEW_EVENT_QUEUE", "review.events")


def publish_review_event(payload):
    if not RABBITMQ_URL:
        return False, "RabbitMQ URL not configured"

    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue=REVIEW_EVENT_QUEUE, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=REVIEW_EVENT_QUEUE,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
        connection.close()
        return True, None
    except Exception as exc:
        return False, repr(exc)
