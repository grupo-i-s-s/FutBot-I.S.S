import pytest

from app.services.behaviour_validation_service import validate_program, is_valid_target, validate_action
from primitives.behaviours import Action

def test_syntax_error_returns_localized_diagnostic():
    code = "def decide(observation)\n    return None"

    diagnostics = validate_program(code)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic["code"] == "SYNTAX_ERROR"
    assert diagnostic["line"] == 1
    assert diagnostic["column"] >= 1
    assert diagnostic["message"]


@pytest.mark.parametrize("code", [
    "",
    "def otra_funcion(observation):\n    return None",
    (
        "def decide(observation):\n    return None\n"
        "def decide(observation):\n    return None"
    ),
    (
        "def otra_funcion():\n"
        "    def decide(observation):\n"
        "        return None"
    ),
])
def test_requires_exactly_one_top_level_decide(code):
    diagnostics = validate_program(code)

    assert [item["code"] for item in diagnostics] == [
        "INVALID_ENTRYPOINT"
    ]


@pytest.mark.parametrize("definition", [
    "async def decide(observation):",
    "def decide():",
    "def decide(observation, extra):",
    "def decide(observation=None):",
    "def decide(*, observation):",
    "def decide(observation, *args):",
    "def decide(observation, **kwargs):",
    "def decide(observation, *, extra):",
    "@decorador\ndef decide(observation):",
])
def test_rejects_invalid_signature(definition):
    code = definition + "\n    return None"

    diagnostics = validate_program(code)

    assert len(diagnostics) == 1
    assert diagnostics[0]["code"] == "INVALID_SIGNATURE"
    assert diagnostics[0]["line"] >= 1
    assert diagnostics[0]["column"] >= 1
    assert diagnostics[0]["message"]


@pytest.mark.parametrize("import_statement", [
    "import os",
    "import primitives.behaviours",
    "from otro_modulo import Action",
    "from primitives.behaviours import offensive",
    "from primitives.behaviours import offensive as Action",
    "from primitives.behaviours import *",
    "from .primitives.behaviours import Action",
    "from primitives.behaviours import Action, defensive",
])
def test_rejects_forbidden_imports(import_statement):
    code = (
        import_statement
        + "\ndef decide(observation):\n    return None"
    )

    diagnostics = validate_program(code)

    assert len(diagnostics) == 1
    assert diagnostics[0]["code"] == "IMPORT_NOT_ALLOWED"
    assert diagnostics[0]["line"] == 1
    assert diagnostics[0]["column"] == 1
    assert diagnostics[0]["message"]


def test_rejects_forbidden_import_inside_function():
    code = (
        "def decide(observation):\n"
        "    import os\n"
        "    return None"
    )

    diagnostics = validate_program(code)

    assert diagnostics[0]["code"] == "IMPORT_NOT_ALLOWED"
    assert diagnostics[0]["line"] == 2


def test_allowed_imports_pass_static_checks_but_require_runtime():
    code = (
        "from primitives.behaviours import Action, Observation\n"
        "def decide(observation):\n"
        "    return Action(move_target=observation.ball_position)"
    )

    diagnostics = validate_program(code)

    assert [item["code"] for item in diagnostics] == [
        "RUNTIME_VALIDATION_PENDING"
    ]


def test_collects_entrypoint_and_import_errors():
    diagnostics = validate_program("import os")

    assert {item["code"] for item in diagnostics} == {
        "INVALID_ENTRYPOINT",
        "IMPORT_NOT_ALLOWED",
    }

def test_target_coordinates():
    assert is_valid_target((10.5, 20), 100, 60)
    assert is_valid_target((0, 60), 100, 60)

    assert not is_valid_target("hola", 100, 60)
    assert not is_valid_target((10,), 100, 60)
    assert not is_valid_target((150, 20), 100, 60)
    assert not is_valid_target((10, -1), 100, 60)
    assert not is_valid_target((True, 20), 100, 60)
    assert not is_valid_target((float("nan"), 20), 100, 60)
    assert not is_valid_target((float("inf"), 20), 100, 60)

@pytest.mark.parametrize("result", [None, "patear"])
def test_rejects_results_that_are_not_actions(result):
    diagnostics = validate_action(result, 100, 60)

    assert len(diagnostics) == 1
    assert diagnostics[0]["code"] == "INVALID_ACTION"

@pytest.mark.parametrize("result", [
    None,
    "patear",
    42,
    {"move_target": (10, 20)},
])
def test_rejects_results_that_are_not_actions(result):
    diagnostics = validate_action(result, 100, 60)

    assert len(diagnostics) == 1
    assert diagnostics[0]["code"] == "INVALID_ACTION"


@pytest.mark.parametrize("move_target, kick_target", [
    ((10, 20), None),
    ((10.5, 20.5), None),
    ((10, 20), (100, 30)),
    ((0, 0), (100, 60)),
    ((100, 60), (0, 0)),
])
def test_accepts_valid_actions(move_target, kick_target):
    action = Action(
        move_target=move_target,
        kick_target=kick_target,
    )

    assert validate_action(action, 100, 60) == []


@pytest.mark.parametrize("field", [
    "move_target",
    "kick_target",
])
@pytest.mark.parametrize("invalid_target", [
    "hola",
    [10, 20],
    (10,),
    (10, 20, 30),
    ("10", 20),
    (True, 20),
    (10, False),
    (-1, 20),
    (101, 20),
    (10, -1),
    (10, 61),
    (float("nan"), 20),
    (10, float("inf")),
])
def test_rejects_invalid_action_coordinates(field, invalid_target):
    targets = {
        "move_target": (10, 20),
        "kick_target": (100, 30),
    }
    targets[field] = invalid_target
    action = Action(**targets)

    diagnostics = validate_action(action, 100, 60)

    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic["code"] == "INVALID_POSITION"
    assert diagnostic["line"] >= 1
    assert diagnostic["column"] >= 1
    assert diagnostic["message"]


def test_rejects_missing_move_target():
    action = Action(move_target=None)

    diagnostics = validate_action(action, 100, 60)

    assert len(diagnostics) == 1
    assert diagnostics[0]["code"] == "INVALID_POSITION"