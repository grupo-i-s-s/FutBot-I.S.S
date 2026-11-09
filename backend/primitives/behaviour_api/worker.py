import hashlib
import json
import sys
from dataclasses import asdict

from primitives.behaviour_api.context import snapshot_from_dict
from primitives.behaviour_api.registry import API_VERSION
from primitives.behaviour_api.validation import ExecutionError, _restrict_worker, execute_once, execution_diagnostic, execute_dt_once, \
    validate_static
from primitives.dt_behaviour import DtObservation

MAX_MESSAGE = 512 * 1024
MAX_PROGRAMS = 6


def emit(message: dict) -> None:
    print(json.dumps(message, allow_nan=False), flush=True)


def main() -> None:
    try:
        _restrict_worker(cpu_seconds=None)
    except Exception:
        emit({
            "op": "ready",
            "ok": False,
            "code": "SANDBOX_UNAVAILABLE",
        })
        return

    emit({
        "op": "ready",
        "ok": True,
        "api": API_VERSION,
    })

    programs = {}

    while True:
        line = sys.stdin.buffer.readline(MAX_MESSAGE + 1)

        if not line or len(line) > MAX_MESSAGE:
            return

        response = {
            "id": None,
            "ok": False,
        }

        try:
            request = json.loads(line)

            response["id"] = request["id"]
            operation = request["op"]
            key = request["key"]

            if operation == "load":
                source = request["source"]
                kind = request.get("kind", "PLAYER")
                expected = hashlib.sha256(f"{API_VERSION}\0{source}".encode("utf-8")).hexdigest()

                if key != expected:
                    raise ValueError("Identificador de programa inválido.")

                diagnostics = validate_static(source, kind)

                if diagnostics:
                    response.update(code="INVALID_PROGRAM", diagnostics=diagnostics,)

                else:
                    if key not in programs and len(programs) >= MAX_PROGRAMS:
                        raise ValueError("Se superó el límite de programas.")

                    if key not in programs:
                        programs[key] = compile(
                            source,
                            "<behaviour>",
                            "exec",
                        )

                    response["ok"] = True

            elif operation == "unload":
                programs.pop(key, None)
                response["ok"] = True

            elif operation == "decide":
                command = execute_once(
                    programs[key],
                    snapshot_from_dict(request["snapshot"]),
                    request["player_id"],
                )

                response.update(
                    ok=True,
                    command=asdict(command),
                )

            elif operation == "decide_dt":
                obs_data = request["observation"]
                obs = DtObservation(**obs_data)

                action = execute_dt_once(
                    programs[key],
                    obs,
                )
                response.update(
                    ok=True,
                    action={"tactical_changes": action.tactical_changes},
                )
            else:
                raise ValueError("Operación desconocida.")

        except ExecutionError as error:
            response.update(
                code=error.diagnostics[0]["code"],
                message=str(error),
                diagnostics=error.diagnostics,
            )

        except MemoryError:
            response.update(
                code="RESOURCE_LIMIT",
                message="El programa superó la memoria permitida.",
            )

        except Exception as error:
            diagnostic = execution_diagnostic(error)

            response.update(
                code=diagnostic["code"],
                message=diagnostic["message"],
                diagnostics=[diagnostic],
            )

        emit(response)
