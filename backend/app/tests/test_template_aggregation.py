import unittest
import math

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

    def test_v4_arithmetic_expressions(self):
        self.assertEqual(
            evaluate_template_expression("sum(count) + sum(count, gt(6))", ROWS),
            16418,
        )
        self.assertEqual(
            evaluate_template_expression("sum(count) - count(*)", ROWS),
            8206,
        )
        self.assertEqual(
            evaluate_template_expression("count(*) * 2", ROWS),
            10,
        )
        self.assertEqual(
            evaluate_template_expression("sum(count) + count(*) * 2", ROWS),
            8221,
        )
        self.assertEqual(
            evaluate_template_expression("(sum(count) + count(*)) / 2", ROWS),
            4108,
        )
        self.assertEqual(
            evaluate_template_expression("add(sum(count), count(*))", ROWS),
            8216,
        )
        self.assertEqual(
            evaluate_template_expression("sub(sum(count), count(*))", ROWS),
            8206,
        )
        self.assertEqual(
            evaluate_template_expression("mul(count(*), 3)", ROWS),
            15,
        )
        self.assertEqual(
            evaluate_template_expression("div(sum(count), count(*))", ROWS),
            1642.2,
        )
        self.assertTrue(math.isnan(evaluate_template_expression("sum(count) / 0", ROWS)))
        self.assertTrue(
            math.isnan(
                evaluate_template_expression(
                    'div(sum(count), count(name, where(category, eq("unknown"))))',
                    ROWS,
                )
            )
        )
        self.assertEqual(
            evaluate_template_expression("first(count) + 1", ROWS),
            8189,
        )

    def test_v5_scalar_first_last(self):
        self.assertEqual(
            evaluate_template_expression("first(name)", ROWS),
            "jjj hahah write",
        )
        self.assertEqual(
            evaluate_template_expression("last(name)", ROWS),
            "abc hahah",
        )
        self.assertEqual(
            evaluate_template_expression('first(name, where(category, eq("beta")))', ROWS),
            "other",
        )
        self.assertEqual(
            evaluate_template_expression('last(name, where(category, eq("alpha")))', ROWS),
            "jjj hahah write",
        )

    def test_v6_date_helpers_add_years(self):
        self.assertEqual(
            evaluate_template_expression(
                "count(*, where(created_at, date_between(add_years(date(22, 3, 2027), -1), add_years(date(25, 3, 2027), -1))))",
                ROWS,
            ),
            3,
        )
        self.assertEqual(
            evaluate_template_expression(
                "count(*, where(created_at, before(add_years(date(1, 1, 2027), -1))))",
                ROWS,
            ),
            0,
        )
        self.assertEqual(
            evaluate_template_expression(
                'count(*, where(name, eq(first(name, where(category, eq("beta"))))))',
                ROWS,
            ),
            1,
        )

    def test_v7_template_variables_set_var(self):
        variables: dict[str, object] = {}
        self.assertEqual(
            evaluate_template_expression(
                'set(base_name, first(name, where(category, eq("beta"))))',
                ROWS,
                variables,
            ),
            "",
        )
        self.assertEqual(variables.get("base_name"), "other")
        self.assertEqual(
            evaluate_template_expression("var(base_name)", ROWS, variables),
            "other",
        )
        self.assertEqual(
            evaluate_template_expression(
                "count(*, where(name, eq(var(base_name))))",
                ROWS,
                variables,
            ),
            1,
        )
        self.assertEqual(
            evaluate_template_expression(
                'set(road_filter, where(category, eq("alpha")))',
                ROWS,
                variables,
            ),
            "",
        )
        self.assertEqual(
            evaluate_template_expression("count(*, var(road_filter))", ROWS, variables),
            2,
        )

    def test_render_template_content_with_variables(self):
        template = (
            '{{ set(target, first(name, where(category, eq("beta")))) }}'
            'Target={{ var(target) }}, '
            'Count={{ count(*, where(name, eq(var(target)))) }}'
        )
        result = render_template_content(template, ROWS)
        self.assertIn("Target=other", result)
        self.assertIn("Count=1", result)

    def test_render_template_content_division_by_zero_renders_dash(self):
        template = "Ratio={{ sum(count) / 0 }}"
        result = render_template_content(template, ROWS)
        self.assertIn("Ratio=-", result)

    def test_render_template_content_zero_numerator_division_renders_dash(self):
        template = "Ratio={{ 0 / count(*) }}"
        result = render_template_content(template, ROWS)
        self.assertIn("Ratio=-", result)

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

    def test_render_template_content_with_odt_inline_tags(self):
        template = (
            "Total={{ <text:s/>sum(count)<text:s/> }}, "
            "Span={{ <text:span>count</text:span>(*) }}"
        )
        result = render_template_content(template, ROWS)
        self.assertIn("Total=8211", result)
        self.assertIn("Span=5", result)

    def test_render_template_content_decodes_xml_entities_in_expression(self):
        template = "Alpha={{ count(category, eq(&quot;alpha&quot;)) }}"
        result = render_template_content(template, ROWS)
        self.assertIn("Alpha=2", result)

    def test_render_template_content_ignores_empty_odt_placeholder(self):
        template = "Guide text {{ <text:s/>}} should stay unchanged"
        result = render_template_content(template, ROWS)
        self.assertEqual(result, template)

    def test_validation_errors(self):
        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression("median(count)", ROWS)

        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression("sum()", ROWS)

        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression("sum(count, gt())", ROWS)

        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression('sum(count, regex("["))', ROWS)

        with self.assertRaises(TemplateAggregationError):
            evaluate_template_expression("count(*, where(created_at, before(add_years(\"bad-date\", -1))))", ROWS)



if __name__ == "__main__":
    unittest.main()
