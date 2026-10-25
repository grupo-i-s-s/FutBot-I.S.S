import pytest

from app.services.behaviour_validation_service import validate_program


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