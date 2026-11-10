"""Comprueba la tabla de api_endpoints.md con el OpenAPI recibido por stdin."""

import json
import re
import sys
from pathlib import Path


def documented_operations():
    reference = Path(__file__).with_name("api_endpoints.md").read_text(encoding="utf-8")
    rows = re.findall(
        r"^\| (GET|POST|PUT|PATCH|DELETE) \| `([^`]+)` \| `(2\d\d)` \| (`[^`]+`|—) \|",
        reference,
        re.MULTILINE,
    )
    return {(method, path, status, model.strip("`")) for method, path, status, model in rows}


def openapi_operations(specification):
    operations = set()
    for path, methods in specification["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            body = operation.get("requestBody")
            model = "—"
            if body:
                schema = body["content"]["application/json"]["schema"]
                model = schema["$ref"].rsplit("/", 1)[-1]
            for status in operation["responses"]:
                if status.startswith("2"):
                    operations.add((method.upper(), path, status, model))
    return operations


if __name__ == "__main__":
    documented = documented_operations()
    current = openapi_operations(json.load(sys.stdin))
    if documented != current:
        for label, difference in (("Falta en la referencia", current - documented),
                                  ("Sobra en la referencia", documented - current)):
            for operation in sorted(difference):
                print(label, *operation, sep=" | ", file=sys.stderr)
        sys.exit(1)
    print(f"{len(current)} operaciones HTTP coinciden con OpenAPI.")
