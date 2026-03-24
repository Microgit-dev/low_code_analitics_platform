import unittest

from app.application.services.template_aggregation import (
    TemplateAggregationError,
    evaluate_template_expression,
    render_template_content,
)


ROWS = [
    {
        "name": "jjj hahah write",
        "count": 8188,
        "category": "alpha",
        "created_at": "2026-03-20T10:00:00",
    },
    {
        "name": "other",
        "count": 3,
        "category": "beta",
        "created_at": "2026-03-23T09:30:00",
    },
    {
        "name": "abc hahah",
        "count": "7",
        "category": "gamma",
        "created_at": "2026-03-24",
    },
    {
        "name": None,
        "count": 12,
        "category": "alpha",
        "created_at": "2026-03-25T00:00:00",
    },
    {
        "count": True,
        "category": "delta",
        "created_at": "invalid-date",
    },
]


class TemplateAggregationTests(unittest.TestCase):
    def test_backward_compatible_aggregations(self):
        self.assertEqual(evaluate_template_expression("count(*)", ROWS), 5)
        self.assertEqual(evaluate_template_expression("count(name)", ROWS), 3)
        self.assertEqual(evaluate_template_expression("sum(count)", ROWS), 8211)
        self.assertEqual(evaluate_template_expression("avg(count)", ROWS), 1642.2)
        self.assertEqual(evaluate_template_expression("min(count)", ROWS), 1)
        self.assertEqual(evaluate_template_expression("max(count)", ROWS), 8188)

    def test_v1_numeric_and_logic_conditions(self):
        self.assertEqual(evaluate_template_expression("sum(count, gt(6))", ROWS), 8207)
        self.assertEqual(evaluate_template_expression("sum(count, and(gt(6), lt(100)))", ROWS), 19)
        self.assertEqual(
            evaluate_template_expression('sum(count, where(name, contains("hahah")))', ROWS),
            8195,
        )
        self.assertEqual(
            evaluate_template_expression('count(name, where(name, starts_with("jjj")))', ROWS),
            1,
        )
        self.assertEqual(
            evaluate_template_expression("count(name, not(where(name, contains('hahah'))))", ROWS),
            1,
        )

    def test_v2_date_conditions(self):
        self.assertEqual(
            evaluate_template_expression(
                'count(*, where(created_at, after("2026-03-22")))',
                ROWS,
            ),
            3,
        )
        self.assertEqual(
            evaluate_template_expression(
                'sum(count, where(created_at, date_between("2026-03-23", "2026-03-24")))',
                ROWS,
            ),
            10,
        )
        self.assertEqual(
            evaluate_template_expression(
                'count(*, where(created_at, before("2026-03-21")))',
                ROWS,
            ),
            1,
        )

    def test_v3_set_and_regex_conditions(self):
        self.assertEqual(
            evaluate_template_expression('count(category, in("alpha", "beta"))', ROWS),
            3,
        )
        self.assertEqual(
            evaluate_template_expression('count(category, not_in("alpha", "beta"))', ROWS),
            2,
        )
        self.assertEqual(evaluate_template_expression('count(name, regex("^jjj"))', ROWS), 1)
        self.assertEqual(evaluate_template_expression('count(name, regex("hahah$"))', ROWS), 1)

    def test_render_template_content(self):
        template = (
            'Rows={{ count(*) }}, '
            'SumGt6={{ sum(count, gt(6)) }}, '
            'HasHahah={{ count(*, where(name, contains("hahah"))) }}'
        )
        result = render_template_content(template, ROWS)
        self.assertIn("Rows=5", result)
        self.assertIn("SumGt6=8207", result)
        self.assertIn("HasHahah=2", result)

    def test_validation_errors(self):
        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression("median(count)", ROWS)

        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression("sum()", ROWS)

        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression("sum(count, gt())", ROWS)

        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression('sum(count, regex("["))', ROWS)


if __name__ == "__main__":
    unittest.main()
