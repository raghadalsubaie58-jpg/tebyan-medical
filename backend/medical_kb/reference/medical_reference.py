"""
MedicalKB — runtime knowledge base loaded from JSON schemas.
Provides panel lookup, test lookup, and severity classification.
"""
from __future__ import annotations
import json
import pathlib

_SCHEMAS_DIR = pathlib.Path(__file__).parent.parent / "schemas"


class MedicalKB:

    def __init__(self) -> None:
        self._panels: dict[str, dict] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not _SCHEMAS_DIR.exists():
            return
        for path in sorted(_SCHEMAS_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                code = data.get("panel_code", path.stem).lower()
                self._panels[code] = data
            except Exception as e:
                print(f"[MedicalKB] Failed to load {path.name}: {e}")
        print(f"[MedicalKB] Loaded {len(self._panels)} panels: {list(self._panels)}")

    # ── Panel-level ────────────────────────────────────────────────────────

    def get_panel(self, code: str) -> dict | None:
        return self._panels.get(code.lower())

    def list_panels(self) -> list[str]:
        return list(self._panels.keys())

    # ── Test-level ─────────────────────────────────────────────────────────

    def get_test(self, panel_code: str, test_name: str) -> dict | None:
        panel = self.get_panel(panel_code)
        if not panel:
            return None
        tests = panel.get("tests", {})
        name_lower = test_name.lower().strip()
        for canonical, data in tests.items():
            if canonical.lower() == name_lower:
                return data
            aliases = [a.lower() for a in data.get("abbreviations", [])]
            if name_lower in aliases:
                return data
        return None

    def find_test_panel(self, test_name: str) -> tuple[str, dict] | None:
        """Search all panels for a test name. Returns (panel_code, test_data) or None."""
        name_lower = test_name.lower().strip()
        for code, panel in self._panels.items():
            for canonical, data in panel.get("tests", {}).items():
                if canonical.lower() == name_lower:
                    return code, data
                if name_lower in [a.lower() for a in data.get("abbreviations", [])]:
                    return code, data
        return None

    # ── Range lookup ───────────────────────────────────────────────────────

    def get_range(
        self, panel_code: str, test_name: str, gender: str = "adult"
    ) -> tuple[float, float] | None:
        test = self.get_test(panel_code, test_name)
        if not test:
            return None
        ranges = test.get("ranges", {})
        gender_key = f"adult_{gender}" if gender in ("male", "female") else gender
        r = ranges.get(gender_key) or ranges.get("adult")
        if r:
            lo = r.get("low", float("-inf"))
            hi = r.get("high", float("inf"))
            return lo, hi
        return None

    def classify(
        self, panel_code: str, test_name: str, value: float, gender: str = "adult"
    ) -> str:
        rng = self.get_range(panel_code, test_name, gender)
        if rng is None:
            return "unknown"
        lo, hi = rng
        if value < lo:
            return "low"
        if value > hi:
            return "high"
        return "normal"

    def get_severity(
        self, panel_code: str, test_name: str, value: float
    ) -> str | None:
        """Return human-readable severity label from severity_thresholds if defined."""
        test = self.get_test(panel_code, test_name)
        if not test:
            return None
        thresholds = test.get("severity_thresholds", {})
        if not thresholds:
            return None
        if "critical_low" in thresholds and value <= thresholds["critical_low"]:
            return "critical_low"
        if "severe_low" in thresholds and value <= thresholds["severe_low"]:
            return "severe_low"
        if "critical_high" in thresholds and value >= thresholds["critical_high"]:
            return "critical_high"
        if "acute_liver_failure" in thresholds and value >= thresholds["acute_liver_failure"]:
            return "acute_liver_failure"
        if "severe_elevation" in thresholds and value >= thresholds["severe_elevation"]:
            return "severe_elevation"
        if "moderate_elevation_x10" in thresholds and value >= thresholds["moderate_elevation_x10"]:
            return "moderate_high"
        if "mild_elevation_x3" in thresholds and value >= thresholds["mild_elevation_x3"]:
            return "mild_high"
        return None

    # ── Context building ───────────────────────────────────────────────────

    def build_panel_context(self, panel_code: str) -> str:
        """Return a compact Arabic text summary of a panel's reference ranges."""
        panel = self.get_panel(panel_code)
        if not panel:
            return ""
        lines = [f"لوحة {panel.get('name_ar', panel_code)}:"]
        for test_name, data in panel.get("tests", {}).items():
            ranges = data.get("ranges", {})
            adult = ranges.get("adult") or ranges.get("adult_male")
            if adult:
                lo, hi = adult.get("low", "?"), adult.get("high", "?")
                unit = data.get("unit", "")
                lines.append(f"  {test_name}: {lo}–{hi} {unit}")
        return "\n".join(lines)
