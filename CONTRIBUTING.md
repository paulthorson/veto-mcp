# Contributing

## How to contribute

1. Fork the repo and open a pull request from your branch.
2. Describe what the change does and why.
3. Make sure the test suite passes before you open the PR:

   ```bash
   .venv/bin/python tests/run.py
   ```

   (`tests/run.py` is the unittest-based runner CI uses — see
   `.github/workflows/ci.yml:46` (`run: python tests/run.py`); plain
   `.venv/bin/python -m unittest discover -s tests` works too.)

## Sign-off

Every commit must be signed off with `git commit -s`, which adds a
`Signed-off-by:` line certifying the Developer Certificate of Origin.
Commits without a sign-off can't be merged.
