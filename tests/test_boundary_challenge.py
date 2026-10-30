import unittest
from tools.evaluate_boundary_challenge import evaluate


class BoundaryChallengeTests(unittest.TestCase):
    def test_unsafe_claim_is_not_excused_by_uncertainty_in_another_clause(self):
        result = evaluate()
        self.assertEqual(result["model_calls"], 0)
        for case in result["cases"]:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["passed"], case)


if __name__ == "__main__":
    unittest.main()
