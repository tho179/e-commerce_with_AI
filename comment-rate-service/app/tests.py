import os
from unittest.mock import Mock, patch

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Review


class ReviewIntelligenceTests(TestCase):
	def setUp(self):
		self.client = APIClient()
		shared_token = os.getenv("SERVICE_SHARED_TOKEN", "")
		self.request_headers = {}
		if shared_token:
			self.client.credentials(HTTP_X_SERVICE_TOKEN=shared_token)
			self.request_headers = {"HTTP_X_SERVICE_TOKEN": shared_token}

	@patch("app.views.requests.get")
	def test_create_review_enriches_ai_fields(self, mock_get):
		mocked = Mock()
		mocked.raise_for_status.return_value = None
		mocked.json.return_value = {"purchased": True}
		mock_get.return_value = mocked

		response = self.client.post(
			"/reviews/",
			{
				"customer_id": 1,
				"book_id": 1000001,
				"rating": 5,
				"comment": "Giao hang nhanh va chat luong tot.",
			},
			format="json",
			**self.request_headers,
		)

		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertIn(payload["sentiment_label"], ["positive", "neutral", "negative"])
		self.assertIsInstance(payload["sentiment_score"], float)
		self.assertIsInstance(payload["aspect_tags"], list)
		self.assertTrue(payload["advice"])

	def test_insights_returns_book_scope_aggregation(self):
		Review.objects.create(
			customer_id=1,
			book_id=1000001,
			rating=5,
			comment="Rat hai long",
			sentiment_label="positive",
			sentiment_score=0.9,
			aspect_tags=["delivery"],
			advice="Upsell",
			ai_metadata={"source": "test"},
		)
		Review.objects.create(
			customer_id=2,
			book_id=1000001,
			rating=2,
			comment="Giao hang cham",
			sentiment_label="negative",
			sentiment_score=0.2,
			aspect_tags=["delivery"],
			advice="Investigate",
			ai_metadata={"source": "test"},
		)

		response = self.client.get("/reviews/insights/", {"book_id": 1000001}, **self.request_headers)
		self.assertEqual(response.status_code, 200)
		payload = response.json()
		self.assertEqual(payload["scope"], "book")
		self.assertEqual(payload["book_id"], 1000001)
		self.assertEqual(payload["total_reviews"], 2)
		self.assertIn("sentiment_distribution", payload)
		self.assertIn("recommended_actions", payload)
