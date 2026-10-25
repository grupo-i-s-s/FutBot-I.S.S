import ast

def validate_syntax(code: str) -> list[dict]:
    try: 
        ast.parse(code)
    except SyntaxError as error:
        return[{
            "line": error.lineno or 1,
            "column": error.offset or 1, 
            "code": "SYNTAX_ERROR",
            "message": error.msg,
        }]
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


def validate_program(code: str) -> list[dict]:
    diagnostics = validate_syntax(code)

    if diagnostics:
        return diagnostics

    tree = ast.parse(code)

    diagnostics.extend(validate_entrypoint(tree))
    diagnostics.extend(validate_imports(tree))

    if diagnostics:
        return diagnostics

    return[{
        "line": 1,
        "column": 1,
        "code": "RUNTIME_VALIDATION_PENDING",
        "message": "La validacion estatica paso, falta validar ejecucion"
    }]
