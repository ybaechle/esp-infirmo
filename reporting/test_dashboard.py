import unittest

from dashboard import ci_counts, effort_metrics, number, percentage


class DashboardTest(unittest.TestCase):
    def test_unknowns_zero_and_invalid_measurements(self):
        self.assertIsNone(number(""))
        self.assertEqual(number("0"), 0)
        self.assertIsNone(percentage(0, 0))
        self.assertEqual(percentage(2, 8), 25)
        for bad in ("-1", "nan", "inf"):
            with self.assertRaises(ValueError):
                number(bad)

    def test_forecast_does_not_invent_remaining_work(self):
        row = dict(id="PM-4", owner="TL", baseline_hours="21", actual_hours="8",
                   etc_hours="", status="In Progress", evidence="", sprint="1", committed="yes")
        rows, planned, delivered = effort_metrics([row])
        self.assertIsNone(rows[0]["forecast"])
        self.assertEqual((planned, delivered), (21, 0))
        row["etc_hours"] = "16"
        self.assertEqual(effort_metrics([row])[0][0]["variance"], 3)
        row["status"] = "Done"
        with self.assertRaises(ValueError):
            effort_metrics([row])
        row.update(etc_hours="0", evidence="review accepted")
        self.assertEqual(effort_metrics([row])[2], 21)

    def test_ci_budget_is_not_a_test_failure(self):
        counts = ci_counts([
            dict(status="completed", conclusion="failure", infrastructure_blocked=True),
            dict(status="completed", conclusion="failure"),
            dict(status="completed", conclusion="success"),
            dict(status="in_progress", conclusion=""),
            dict(status="completed", conclusion="timed_out"),
        ])
        self.assertEqual(dict(counts), dict(blocked=1, failure=1, success=1, pending=1, timed_out=1))


if __name__ == "__main__":
    unittest.main()
