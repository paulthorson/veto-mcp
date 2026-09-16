"""Automated UAT acceptance journeys for Veto's shipped roadmap initiatives.

Each ``test_uat_iNN.py`` module models a REAL user journey for one initiative
as unittest cases. Journeys run two ways:

1. CI: ``tests/run.py`` discovers ``test_uat_i*.py`` automatically.
2. UAT report: ``.venv/bin/python tests/uat/run_uat.py [--report out.md]``
   runs the seven journeys and renders a plain-English report for Paul,
   with epic -> check -> pass/fail traceability.

Every journey test method maps to exactly one roadmap epic via EPIC_MAP.
"""
