import unittest
from project import benchmark, percentile, summarize


class BenchmarkTests(unittest.TestCase):
    def test_percentile_and_pending_are_separate(self):
        self.assertEqual(percentile(list(range(1, 21)), 0.95), 19)
        rows = [
            {"state": "delivered", "elapsed_ms": 100, "attempts": 2},
            {"state": "pending", "elapsed_ms": 9000, "attempts": 0},
        ]
        self.assertEqual(summarize(rows, 0.5)["p95_observed_ms"], 100)
        self.assertEqual(summarize(rows, 0.5)["other"], 1)
        self.assertEqual(summarize(rows, 0.5)["repeated_attempts"], 1)

    def test_reject_remote_endpoint(self):
        with self.assertRaises(ValueError):
            benchmark(
                "https://example.com", count=1, concurrency=1, poll_seconds=0.1, injected_every=0
            )
