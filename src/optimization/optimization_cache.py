import hashlib
import json
from pathlib import Path


class OptimizationCache:
    """Persistent JSONL cache keyed by candidate and study fingerprint."""

    def __init__(self, directory, study_fingerprint):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.study_fingerprint = str(study_fingerprint)
        self.path = self.directory / "candidate_results.jsonl"
        self._records = {}
        self._load()

    @staticmethod
    def candidate_payload(candidate):
        return {
            "start_positions": list(candidate.start_positions),
            "parking_positions": list(candidate.parking_positions)
        }

    def key(self, candidate, phase):
        payload = {
            "study": self.study_fingerprint,
            "phase": str(phase),
            "candidate": self.candidate_payload(candidate)
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _load(self):
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("study") != self.study_fingerprint:
                continue
            self._records[record["key"]] = record

    def get(self, candidate, phase):
        return self._records.get(self.key(candidate, phase))

    def put(self, candidate, phase, serialized_result):
        key = self.key(candidate, phase)
        record = {
            "key": key,
            "study": self.study_fingerprint,
            "phase": str(phase),
            "candidate": self.candidate_payload(candidate),
            "result": serialized_result
        }
        self._records[key] = record
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        return record

    def count(self):
        return len(self._records)
