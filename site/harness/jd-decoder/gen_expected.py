"""Regenerate expected outputs: run jd_decoder.jd_verdict over every
sample and dump canonical JSON. The Node runner compares the TS port
against these files byte-for-byte (after key-sorted canonicalization)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))  # repo root: jd_decoder.py

from jd_decoder import jd_verdict  # noqa: E402


def main() -> None:
    samples = sorted((HERE / "samples").glob("*.txt"))
    out_dir = HERE / "expected"
    out_dir.mkdir(exist_ok=True)
    for sample in samples:
        # Read raw bytes: Node's readFileSync does no universal-newline
        # translation, so \r stays \r. Python's text-mode read would turn
        # it into \n and the two engines would analyze different inputs.
        # Strip only trailing newlines, mirroring the Node reader.
        raw = sample.read_bytes().decode("utf-8")
        text = raw
        while text.endswith("\n"):
            text = text[:-1]
        result = jd_verdict(text)
        (out_dir / (sample.stem + ".json")).write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"wrote {len(samples)} expected files")


if __name__ == "__main__":
    main()
