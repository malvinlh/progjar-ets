#!/usr/bin/env python3
"""
file_protocol.py
Utility: dict ↔ JSON dan Base64 file I/O.
"""
import json
import base64

class FileProtocol:
    def to_json(self, obj: dict) -> str:
        return json.dumps(obj)

    def read_base64(self, path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def write_base64(self, path: str, data_b64: str) -> None:
        data = base64.b64decode(data_b64)
        with open(path, "wb") as f:
            f.write(data)