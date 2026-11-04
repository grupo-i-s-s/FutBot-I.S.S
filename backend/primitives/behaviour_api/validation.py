import ast
import ctypes
import json
import signal
import subprocess
import sys
import resource
from dataclasses import fields
from math import isfinite
from pathlib import Path
from types import SimpleNamespace

from primitives.behaviours import Action, Observation
from primitives.behaviour_api.actions import Command
from primitives.behaviour_api.context import PlayerView, TickSnapshot, distance
from primitives.behaviour_api.queries import Queries
from primitives.behaviour_api.registry import build_registry

def _diagnostic( code: str, message: str, line: int = 1, column: int = 1) -> dict:
    return {
        "line": line,
        "column": column,
        "code": code,
        "message": message
    }

def validate_syntax(code: str) -> list[dict]:
    try:
        ast.parse(code)
    except (SyntaxError, ValueError, RecursionError) as error:
        return [_diagnostic(
            "SYNTAX_ERROR",
            getattr(error, "msg", str(error)),
            getattr(error, "lineno", 1) or 1,
            getattr(error, "offset", 1) or 1,
        )]
    return []

def validate_entrypoint(tree: ast.Module) -> list[dict]:
    functions=[
        node 
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) 
        and node.name == "decide"
    ]

    if len(functions) != 1:
        return[{
            "line": 1,
            "column": 1,
            "code": "INVALID_ENTRYPOINT",
            "message": "Debe existir exactamente una funcion decide",
        }]

    function = functions[0]
    args = function.args

    invalid = (
        isinstance(function, ast.AsyncFunctionDef)
        or len(args.posonlyargs + args.args) != 1
        or bool(args.defaults)
        or bool(args.kwonlyargs)
        or args.kwarg is not None
        or args.vararg is not None
        or bool(function.decorator_list)
    )

    if invalid:
        return [{ 
            "line": function.lineno,
            "column": function.col_offset + 1,
            "code": "INVALID_SIGNATURE",
            "message": ("Decide debe ser una funcion normal, sin decoradores, con un unico argumento obligatorio."),
        }]
    return []

def validate_imports(tree: ast.Module) -> list[dict]:
    allowed_names = { "Action", "Observation"} 
    diagnostics = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            invalid = True
        elif isinstance(node, ast.ImportFrom):
            invalid = (
                node.level !=0
                or node.module != "primitives.behaviours"
                or any(name.name not in allowed_names
                       for name in node.names )
            )
        else:
            continue

        if invalid:
            diagnostics.append({
                "line": node.lineno,
                "column": node.col_offset + 1,
                "code": "IMPORT_NOT_ALLOWED",
                "message": ("Solo se permite importar Action y Observation" 
                            "desde primitives.behaviours.")
            })

    return diagnostics

def is_valid_target(target, width:float, height:float) -> bool:
    if not isinstance(target, tuple) or len(target) != 2:
        return False

    x, y= target

    if not (isinstance(x, (int, float)) and isinstance(y, (int, float))):
        return False

    if isinstance(x, bool) or isinstance(y,bool):
        return False

    return(
        0<= x <= width
        and 0<= y <= height
    )

def validate_action(action: object, width: float, height: float)->list[dict]:
    if type(action) not in (Action, Command):
        return [_diagnostic(
            "INVALID_ACTION",
            "El comportamiento debe devolver una Action o un Command.",
        )]

    if not is_valid_target(action.move_target, width, height):
        return[{
            "line": 1,
            "column": 1,
            "code": "INVALID_POSITION",
            "message": "La posicion deben ser coordenadas dentro de la cancha."
        }]

    if (action.kick_target is not None) and (not is_valid_target(action.kick_target, width, height)):
        return [{
            "line": 1,
            "column": 1,
            "code": "INVALID_POSITION",
            "message": "El destino debe contener coordenadas dentro de la cancha."
        }]

    if type(action) is Command:
        speed = action.kick_speed
        invalid_speed = (
            (action.kick_target is None) != (speed is None)
            or (
                speed is not None
                and (
                    type(speed) not in (int, float)
                    or speed <= 0
                    or (type(speed) is float and not isfinite(speed))
                )
            )
        )

        if invalid_speed:
            return [_diagnostic(
                "INVALID_KICK_SPEED",
                "La patada necesita una velocidad positiva y finita.",
            )]
    
    return []

def validate_access(tree: ast.Module) -> list[dict]:
    allowed = (
        ast.Module, ast.FunctionDef, ast.arguments, ast.arg,
        ast.ImportFrom, ast.alias,
        ast.Return, ast.Assign, ast.AugAssign,
        ast.Name, ast.Load, ast.Store, ast.Constant,
        ast.If, ast.While, ast.For, ast.Break, ast.Continue, ast.Pass,
        ast.Expr, ast.Call, ast.keyword,
        ast.Tuple, ast.List, ast.Subscript, ast.Slice,
        ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.Attribute,
        ast.operator, ast.unaryop, ast.boolop, ast.cmpop,
    )
    readable = {field.name for field in fields(Observation)}
    forbidden = {
        "open", "eval", "exec", "compile", "globals", "locals",
        "vars", "dir", "getattr", "setattr", "delattr",
        "type", "object", "super", "input", "help", "breakpoint",
    }

    entrypoint = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "decide"
    )

    for node in ast.walk(tree):
        invalid = not isinstance(node, allowed)
        invalid |= isinstance(node, ast.FunctionDef) and node is not entrypoint
        invalid |= isinstance(node, ast.Name) and (
            node.id.startswith("_") or node.id in forbidden
        )
        invalid |= isinstance(node, ast.Attribute) and (
            node.attr not in readable
            or not isinstance(node.ctx, ast.Load)
        )
        invalid |= isinstance(node, ast.alias) and (
            node.asname is not None and node.asname.startswith("_")
        )
        invalid |= isinstance(node, ast.arg) and node.arg.startswith("_")

        if invalid:
            return [_diagnostic(
                "FORBIDDEN_ACCESS",
                "Esta operación no está permitida.",
                getattr(node, "lineno", 1),
                getattr(node, "col_offset", 0) + 1,
            )]

    for node in tree.body:
        if not isinstance(node, (ast.ImportFrom, ast.FunctionDef)):
            return [_diagnostic(
                "FORBIDDEN_ACCESS",
                "Fuera de decide solo se permiten imports.",
                node.lineno,
                node.col_offset + 1,
            )]

    return []

def _restrict_worker() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (1, 1))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    lib = ctypes.CDLL("libseccomp.so.2")
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint,
    ]
    lib.seccomp_rule_add.restype = ctypes.c_int
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_load.restype = ctypes.c_int
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.restype = None

    context = lib.seccomp_init(0x00050001)  # SCMP_ACT_ERRNO(EPERM).
    if not context:
        raise RuntimeError("No se pudo crear el filtro.")

    try:
        for name in (
            b"read", b"write", b"close",
            b"brk", b"mmap", b"mprotect", b"munmap", b"mremap", b"madvise",
            b"futex", b"clock_gettime",
            b"rt_sigaction", b"rt_sigprocmask", b"rt_sigreturn", b"sigaltstack",
            b"getrandom", b"getpid", b"gettid", b"exit", b"exit_group",
        ):
            number = lib.seccomp_syscall_resolve_name(name)
            if number >= 0:
                result = lib.seccomp_rule_add(context, 0x7FFF0000, number, 0)
                if result < 0:
                    raise RuntimeError("No se pudo configurar el filtro.")

        if lib.seccomp_load(context) < 0:
            raise RuntimeError("No se pudo activar el filtro.")
    finally:
        lib.seccomp_release(context)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    if level or name != "primitives.behaviours" or not fromlist:
        raise ImportError("Importación no permitida.")

    if any(item not in {"Action", "Observation"} for item in fromlist):
        raise ImportError("Importación no permitida.")

    return SimpleNamespace(Action=Action, Observation=Observation)


def _samples():
    players = (
        PlayerView(1, 10, (25, 30), (0, 0), (20, 30), 3, 0, 10, 25),
        PlayerView(2, 10, (40, 20), (0, 0), (30, 20), 3, 0, 10, 25),
        PlayerView(3, 20, (75, 30), (0, 0), (80, 30), 3, 0, 10, 25),
    )

    for left in (10, 20):
        for possession in (None, 1, 2, 3):
            for score in (0, 1, 2):
                snapshot = TickSnapshot(
                    time=30,
                    duration=90,
                    width=100,
                    height=60,
                    goal_width=15,
                    left_club_id=left,
                    scores=((10, score), (20, 1)),
                    players=players,
                    ball_position=(
                        (50, 30) if possession is None
                        else next(p.position for p in players if p.id == possession)
                    ),
                    ball_velocity=(0, 0),
                    possessor_id=possession,
                )
                queries = Queries(snapshot, 1)
                closest = min(
                    (p for p in players if p.club_id == 10),
                    key=lambda p: (
                        distance(p.position, snapshot.ball_position), p.id,
                    ),
                )

                observation = Observation(
                    player_position=queries.my_position(),
                    ball_position=queries.ball_position(),
                    home_position=queries.base_position(),
                    opponent_goal=queries.their_goal(),
                    is_closest_teammate=closest.id == 1,
                    ball_in_own_half=queries.ball_on_our_side(),
                    can_kick=queries.can_kick(),
                )
                yield queries, observation


def _validation_worker() -> None:
    source = sys.stdin.read(65_537)

    try:
        _restrict_worker()
    except Exception:
        print(json.dumps([_diagnostic(
            "SANDBOX_UNAVAILABLE",
            "No se pudo aislar la ejecución.",
        )]))
        return

    try:
        program = compile(source, "<behaviour>", "exec")

        for queries, observation in _samples():
            query_registry, action_registry = build_registry(queries)
            namespace = {
                "__builtins__": {
                    "__import__": _safe_import,
                    "abs": abs,
                    "min": min,
                    "max": max,
                    "len": len,
                    "range": range,
                    "round": round,
                    "int": int,
                    "float": float,
                    "bool": bool,
                },
                **query_registry,
                **action_registry,
            }

            exec(program, namespace)
            action = namespace["decide"](observation)
            diagnostics = validate_action(action, 100, 60)
            if diagnostics:
                break
        else:
            diagnostics = []

    except MemoryError:
        diagnostics = [_diagnostic(
            "RESOURCE_LIMIT",
            "El programa superó la memoria permitida.",
        )]
    except Exception as error:
        line = 1
        traceback = error.__traceback__

        while traceback is not None:
            if traceback.tb_frame.f_code.co_filename == "<behaviour>":
                line = traceback.tb_lineno
            traceback = traceback.tb_next

        diagnostics = [_diagnostic(
            "RUNTIME_ERROR",
            type(error).__name__,
            line,
        )]

    print(json.dumps(diagnostics))


def validate_runtime(code: str) -> list[dict]:
    bootstrap = (
        "import sys; sys.path.insert(0, sys.argv[1]); "
        "from primitives.behaviour_api.validation import _validation_worker;"
        "_validation_worker()"
    )

    try:
        result = subprocess.run(
            [
                sys.executable, "-I", "-B", "-c", bootstrap,
                str(Path(__file__).resolve().parents[2]),
            ],
            input=code,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=3,
            env={},
            close_fds=True,
        )
    except subprocess.TimeoutExpired:
        return [_diagnostic("TIMEOUT", "El programa superó el tiempo permitido.")]
    except OSError:
        return [_diagnostic(
            "SANDBOX_UNAVAILABLE",
            "No se pudo iniciar la ejecución aislada.",
        )]

    if result.returncode == -signal.SIGKILL:
        return [_diagnostic(
            "TIMEOUT",
            "La ejecución fue detenida por su límite de recursos.",
        )]

    if result.returncode:
        return [_diagnostic(
            "SANDBOX_ERROR",
            "El entorno aislado terminó inesperadamente.",
        )]

    try:
        return json.loads(result.stdout)
    except (ValueError, TypeError):
        return [_diagnostic(
            "SANDBOX_ERROR",
            "El entorno aislado devolvió una respuesta inválida.",
        )]

def validate_program(code: str, kind: str = "PLAYER") -> list[dict]:
    if kind != "PLAYER":
        return [_diagnostic(
            "UNSUPPORTED_KIND",
            "La validación de DT todavía no está implementada.",
        )]

    if len(code.encode("utf-8")) > 65_536:
        return [_diagnostic(
            "CODE_TOO_LARGE",
            "El código no puede superar los 64 KiB.",
        )]

    diagnostics = validate_syntax(code)
    if diagnostics:
        return diagnostics

    tree = ast.parse(code)
    diagnostics = validate_entrypoint(tree) + validate_imports(tree)
    if diagnostics:
        return diagnostics

    diagnostics = validate_access(tree)
    if diagnostics:
        return diagnostics

    try:
        compile(tree, "<behaviour>", "exec")
    except (SyntaxError, ValueError, RecursionError) as error:
        return [_diagnostic(
            "SYNTAX_ERROR",
            str(error),
            getattr(error, "lineno", 1) or 1,
        )]

    return validate_runtime(code)
