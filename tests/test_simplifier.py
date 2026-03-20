import unittest

from simplifier import simplify_boolean_expression


class SimplifierValidationTests(unittest.TestCase):
    def test_rejects_numeric_constants_outside_binary_domain(self):
        result = simplify_boolean_expression("A+B+C+D+E+F+2", with_trace=False)
        self.assertEqual(
            result["error"],
            "Constante numerica invalida '2'. Solo se permiten 0 y 1.",
        )

    def test_rejects_invalid_characters(self):
        result = simplify_boolean_expression("A+B+C+D+E+F+@", with_trace=False)
        self.assertEqual(result["error"], "Se detectaron caracteres no permitidos: '@'.")

    def test_rejects_unbalanced_parentheses(self):
        result = simplify_boolean_expression("(A+B+C+D+E+F", with_trace=False)
        self.assertEqual(result["error"], "Falta cerrar un parentesis ')'.")

    def test_supports_binary_constants(self):
        result = simplify_boolean_expression("A+B+C+D+E+F+1", with_trace=False)
        self.assertEqual(result["simplified_expression"], "1")

    def test_supports_implicit_and(self):
        result = simplify_boolean_expression("A(B+C)+D+E+F+G+H", with_trace=False)
        self.assertIn("(A . B)", result["simplified_expression"])
        self.assertIn("(A . C)", result["simplified_expression"])

    def test_accepts_configurable_variable_range(self):
        result = simplify_boolean_expression(
            "A+B",
            with_trace=False,
            min_variables=1,
            max_variables=3,
        )
        self.assertNotIn("error", result)
        self.assertEqual(result["variable_range"], {"min": 1, "max": 3})

    def test_rejects_invalid_range_configuration(self):
        result = simplify_boolean_expression(
            "A+B+C",
            with_trace=False,
            min_variables=4,
            max_variables=2,
        )
        self.assertEqual(result["error"], "El minimo de variables no puede ser mayor al maximo.")

    def test_builds_truth_table_and_equivalence_report(self):
        result = simplify_boolean_expression(
            "A.B + A.B'",
            with_trace=False,
            min_variables=2,
            max_variables=2,
            with_truth_table=True,
            truth_table_limit=4,
        )
        self.assertTrue(result["equivalence_check"]["is_equivalent"])
        self.assertEqual(result["equivalence_check"]["total_rows"], 4)
        self.assertEqual(len(result["truth_table"]["rows"]), 4)

    def test_truth_table_can_be_truncated_for_display(self):
        result = simplify_boolean_expression(
            "A+B+C",
            with_trace=False,
            min_variables=3,
            max_variables=3,
            with_truth_table=True,
            truth_table_limit=4,
        )
        self.assertTrue(result["truth_table"]["truncated"])
        self.assertEqual(result["truth_table"]["displayed_rows"], 4)


if __name__ == "__main__":
    unittest.main()
