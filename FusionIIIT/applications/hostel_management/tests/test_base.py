"""Shared workflow test base for hostel_management."""

from .conftest import BaseModuleTestCase


class WFTestBase(BaseModuleTestCase):
    """Workflow test helpers used by test_workflows.py."""

    def setUp(self):
        super().setUp()
        self._steps = []

    def _add_step(self, step_no, action, expected, actual, passed):
        self._steps.append({
            "step": step_no,
            "action": action,
            "expected": expected,
            "actual": actual,
            "passed": bool(passed),
        })

    def _all_steps_passed(self):
        return all(step["passed"] for step in self._steps)

    def _record_result(self, actual: str, verdict: str, raw: str = ""):
        super()._record_result(actual, verdict, raw)
