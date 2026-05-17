"""Backward-compatible wrapper for the packaged compliance report CLI."""

from aireadi_retinal_imaging.cli.compliance_report import main, sort_them_by_sop_class


if __name__ == "__main__":
    raise SystemExit(main())
