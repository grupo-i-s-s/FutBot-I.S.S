import json
import os
import select
import subprocess
import sys

from collections import OrderedDict
from dataclasses import asdict
from pathlib import Path
from time import monotonic

from primitives.behaviours import (
    BehaviourMode,
    resolve_behaviour,
)
from primitives.behaviour_api.actions import Command
from primitives.behaviour_api.context import to_point
from primitives.behaviour_api.registry import API_VERSION, program_key
from primitives.behaviour_api.validation import validate_action, validate_dt_action, validate_static
from primitives.dt_behaviour import DtAction, DtObservation


MAX_MESSAGE = 512 * 1024
MAX_PROGRAMS = 6


class BehaviourRuntimeError(RuntimeError):
    def __init__(self, code: str, message: str, diagnostics=None):
        super().__init__(message)
        self.code = code
        self.diagnostics = diagnostics


class BehaviourWorkerDead(BehaviourRuntimeError):
    pass


def resolve_program(code: str, name: str, version: int = 1) -> dict:

    if type(version) is not int or version < 1:
        raise ValueError(
            "La versión del comportamiento es inválida."
        )

    try:
        mode = resolve_behaviour(code, name)
        source = None

    except ValueError:
        diagnostics = validate_static(code)

        if diagnostics:
            raise ValueError(
                diagnostics[0]["message"]
            )

        # Se conserva el enum anterior por compatibilidad.
        # La presencia de source determina la ejecución custom.
        mode = BehaviourMode.BALANCED
        source = code

    return {
        "behaviour_mode": mode,
        "behaviour_code": source,
        "behaviour_version": version,
        "behaviour_api_version": API_VERSION,
    }


class BehaviourRuntime:
    def __init__(
        self,
        decision_timeout: float = 0.05,
        startup_timeout: float = 3.0,
    ):
        self.decision_timeout = decision_timeout
        self.startup_timeout = startup_timeout

        self._process = None
        self._buffer = bytearray()
        self._sequence = 0
        self._loaded = OrderedDict()

        bootstrap = (
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from primitives.behaviour_api.worker import main; "
            "main()"
        )

        try:
            self._process = subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    "-B",
                    "-u",
                    "-c",
                    bootstrap,
                    str(Path(__file__).resolve().parents[2]),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
                env={},
                close_fds=True,
            )

            os.set_blocking(self._process.stdin.fileno(), False)

            os.set_blocking(self._process.stdout.fileno(), False)

            ready = self._read(monotonic() + startup_timeout)

            if (ready.get("op") != "ready"
                or ready.get("ok") is not True
                or ready.get("api") != API_VERSION):

                raise ValueError("El worker no pudo inicializarse.")

        except Exception as error:
            self.close()

            raise BehaviourWorkerDead(
                "SANDBOX_UNAVAILABLE",
                "No se pudo iniciar el ejecutor aislado.",
            ) from error

    @staticmethod
    def _remaining(deadline: float) -> float:
        remaining = deadline - monotonic()

        if remaining <= 0:
            raise TimeoutError

        return remaining

    def _read(self, deadline: float) -> dict:
        descriptor = self._process.stdout.fileno()

        while b"\n" not in self._buffer:
            readable, _, _ = select.select(
                [descriptor],
                [],
                [],
                self._remaining(deadline),
            )

            if not readable:
                raise TimeoutError

            chunk = os.read(descriptor, 65_536)

            if not chunk:
                raise EOFError(
                    "El worker cerró su salida."
                )

            self._buffer.extend(chunk)

            if len(self._buffer) > MAX_MESSAGE:
                raise ValueError(
                    "Respuesta demasiado grande."
                )

        line, remainder = self._buffer.split(
            b"\n",
            1,
        )

        self._buffer = bytearray(remainder)
        response = json.loads(line)

        if type(response) is not dict:
            raise ValueError(
                "Respuesta inválida."
            )

        return response

    def _write(self, data: bytes, deadline: float) -> None:

        descriptor = self._process.stdin.fileno()
        pending = memoryview(data)

        while pending:
            _, writable, _ = select.select(
                [],
                [descriptor],
                [],
                self._remaining(deadline),
            )

            if not writable:
                raise TimeoutError

            written = os.write(descriptor, pending)

            if written <= 0:
                raise EOFError("El worker cerró su entrada.")

            pending = pending[written:]

    def _request(self, payload: dict, timeout: float) -> dict:

        if self._process is None:
            raise BehaviourWorkerDead(
                "WORKER_DIED",
                "El ejecutor está cerrado.",
            )

        self._sequence += 1

        payload = {
            **payload,
            "id": self._sequence,
        }

        data = (
            json.dumps(
                payload,
                allow_nan=False,
            ).encode("utf-8")
            + b"\n"
        )

        if len(data) > MAX_MESSAGE:
            raise BehaviourRuntimeError(
                "MESSAGE_TOO_LARGE",
                "La petición supera el tamaño permitido.",
            )

        deadline = monotonic() + timeout

        try:
            self._write(data, deadline)
            response = self._read(deadline)

            if (type(response.get("id")) is not int
                or response["id"] != self._sequence
                or type(response.get("ok")) is not bool):

                raise ValueError("Respuesta inesperada.")

        except (TimeoutError, EOFError, OSError, ValueError) as error:
            self.close()

            code = "TIMEOUT" if isinstance(error, TimeoutError) else "WORKER_DIED"

            raise BehaviourWorkerDead(code, "Falló la ejecución aislada.") from error

        if not response["ok"]:
            code = response.get(
                "code",
                "RUNTIME_ERROR",
            )

            error_class = BehaviourRuntimeError

            if code == "RESOURCE_LIMIT":
                self.close()
                error_class = BehaviourWorkerDead

            raise error_class(
                code,
                response.get("message", code),
                response.get("diagnostics"),
            )

        return response

    def load(self, source: str, kind: str = "PLAYER") -> str:
        key = program_key(source, kind)

        if key in self._loaded:
            self._loaded.move_to_end(key)
            return key

        if len(self._loaded) >= MAX_PROGRAMS:
            oldest = next(iter(self._loaded))
            self.unload(oldest)

        self._request(
            {
                "op": "load",
                "key": key,
                "source": source,
                "kind": kind,
            },
            self.startup_timeout,
        )

        self._loaded[key] = None
        return key

    def unload(self, key: str) -> None:
        self._request(
            {
                "op": "unload",
                "key": key,
            },
            self.startup_timeout,
        )

        self._loaded.pop(key, None)

    def decide(self, key: str, snapshot, player_id: int) -> Command:

        response = self._request(
            {
                "op": "decide",
                "key": key,
                "snapshot": asdict(snapshot),
                "player_id": player_id,
            },
            self.decision_timeout,
        )

        try:
            data = response["command"]

            if type(data) is not dict or set(data) != {
                "move_target",
                "kick_target",
                "kick_speed",
            }:
                raise ValueError("Formato de orden inválido.")

            command = Command(
                move_target=to_point(
                    data["move_target"]
                ),
                kick_target=(
                    None
                    if data["kick_target"] is None
                    else to_point(data["kick_target"])
                ),
                kick_speed=data["kick_speed"],
            )

            diagnostics = validate_action(command, snapshot.width, snapshot.height)

            if diagnostics:
                raise ValueError("La orden no es válida.")

            if (command.kick_speed is not None
                and command.kick_speed > snapshot.player(player_id).shot_speed):

                raise ValueError("La patada supera la capacidad del jugador.")

            return command

        except (KeyError, TypeError, ValueError, OverflowError
        ) as error:
            self.close()

            raise BehaviourWorkerDead(
                "INVALID_COMMAND",
                "El ejecutor devolvió una orden inválida.",
            ) from error

    def dt_decide(self, key: str, observation: DtObservation) -> DtAction:
        response = self._request(
            {
                "op": "decide_dt",
                "key": key,
                "observation": asdict(observation),
            },
            self.decision_timeout,
        )
        try:
            data = response["action"]
            if (
                type(data) is not dict or data.keys() != {"tactical_changes", "substitutions"}
                or type(data["tactical_changes"]) is not list
            ):
                raise ValueError("Formato de orden de DT inválido.")

            action = DtAction(
                tactical_changes=[
                    {**change, "mode": BehaviourMode(change["mode"])}
                    for change in data["tactical_changes"]
                ],
                substitutions=data["substitutions"],
            )
            if validate_dt_action(action, observation):
                raise ValueError("La orden de DT no es válida.")
            return action

        except (KeyError, TypeError, ValueError) as error:
            self.close()
            raise BehaviourWorkerDead(
                "INVALID_COMMAND",
                "El ejecutor devolvió una orden de DT inválida.",
            ) from error

    def close(self) -> None:
        process = self._process
        self._process = None

        self._loaded.clear()
        self._buffer.clear()

        if process is None:
            return

        try:
            if process.poll() is None:
                process.kill()

            process.wait()

        finally:
            process.stdin.close()
            process.stdout.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
