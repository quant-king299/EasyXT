"""回测实验元数据清单。"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict


def build_experiment_manifest(*, expression: str, data_snapshot: str,
                              universe_version: str, parameters: Dict[str, Any],
                              cost_model: Dict[str, Any],
                              signal_timing: str = "close_to_next_open") -> Dict[str, Any]:
    if not expression or not data_snapshot or not universe_version:
        raise ValueError("实验表达式、数据快照和股票池版本不能为空")
    manifest = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_snapshot": data_snapshot,
        "universe_version": universe_version,
        "signal_timing": signal_timing,
        "parameters": parameters,
        "cost_model": cost_model,
        "factor": {
            "expression": expression,
            "expression_sha256": hashlib.sha256(expression.encode()).hexdigest(),
        },
    }
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    manifest["manifest_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return manifest
