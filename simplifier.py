import re
from dataclasses import dataclass

from sympy import Symbol
from sympy.logic.boolalg import simplify_logic, to_dnf
from sympy.parsing.sympy_parser import parse_expr


ALLOWED_VAR_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


@dataclass(frozen=True)
class Literal:
    name: str
    positive: bool = True


@dataclass
class TraceStep:
    title: str
    expression: str
    law: str


def simplify_boolean_expression(raw_expression: str, with_trace: bool = True) -> dict:
    expression = _extract_rhs(raw_expression)
    variables = sorted(set(ALLOWED_VAR_RE.findall(expression)))

    if not variables:
        return {"error": "No se detectaron variables en la expresion."}

    if len(variables) < 6 or len(variables) > 10:
        return {
            "error": (
                "La expresion debe contener entre 6 y 10 variables distintas "
                f"(actual: {len(variables)})."
            )
        }

    normalized = _normalize_symbols(expression)

    try:
        sympy_expr = _to_sympy_boolean(normalized, variables)
    except Exception:
        return {
            "error": (
                "No se pudo interpretar la expresion. Usa operadores como '+' para OR, "
                "'.' para AND y apostrofe (') para NOT."
            )
        }

    simplified = simplify_logic(sympy_expr, form="dnf")

    result = {
        "input_expression": expression,
        "normalized_expression": normalized,
        "variables": variables,
        "simplified_expression": _pretty_boolean(str(simplified)),
    }

    if with_trace:
        trace = _build_trace(normalized, variables, sympy_expr, simplified)
        result["trace"] = [step.__dict__ for step in trace]

    return result


def _build_trace(normalized: str, variables: list[str], sympy_expr, simplified) -> list[TraceStep]:
    steps: list[TraceStep] = [
        TraceStep(
            title="Expresion normalizada",
            expression=normalized,
            law="Normalizacion de operadores (.+ y ')",
        )
    ]

    sop_terms = _parse_sop_terms(normalized)
    if sop_terms:
        reduced_terms, pair_steps = _reduce_by_complement_pairs(sop_terms)
        steps.extend(pair_steps)

        if pair_steps:
            reduced_expr_str = _terms_to_pretty_expression(reduced_terms)
            steps.append(
                TraceStep(
                    title="Resultado tras combinar terminos",
                    expression=reduced_expr_str,
                    law="Distributiva + complemento + identidad",
                )
            )

    dnf_unsimplified = to_dnf(sympy_expr, simplify=False)
    steps.append(
        TraceStep(
            title="Forma disyuntiva (DNF)",
            expression=_pretty_boolean(str(dnf_unsimplified)),
            law="Estandarizacion de forma logica",
        )
    )

    steps.append(
        TraceStep(
            title="Simplificacion final",
            expression=_pretty_boolean(str(simplified)),
            law=(
                "Aplicacion simbolica de leyes booleanas (absorcion, idempotencia, "
                "complemento y consenso)"
            ),
        )
    )
    return steps


def _extract_rhs(expression: str) -> str:
    expr = expression.strip()
    if "=" in expr:
        _, rhs = expr.split("=", 1)
        return rhs.strip()
    return expr


def _normalize_symbols(expression: str) -> str:
    expr = expression.replace(" ", "")
    expr = expr.replace("·", ".")
    expr = expr.replace("*", ".")
    return expr


def _to_sympy_boolean(expression: str, variables: list[str]):
    expr = expression

    # Convierte negacion postfija de grupos: (A+B)' -> ~(A+B)
    while True:
        updated = re.sub(r"(\([^()]+\))'", r"~\1", expr)
        if updated == expr:
            break
        expr = updated

    # Convierte negacion postfija de variables: A' -> ~A
    expr = re.sub(r"([A-Za-z][A-Za-z0-9_]*)'", r"~\1", expr)

    # Convierte operadores a sintaxis de sympy
    expr = expr.replace("+", "|")
    expr = expr.replace(".", "&")

    # Inserta AND implicito entre tokens contiguos: A(B+C), A~B, )A, etc.
    expr = re.sub(r"(?<=[A-Za-z0-9_)])(?=[(~A-Za-z])", "&", expr)

    symbols = {name: Symbol(name) for name in variables}
    return parse_expr(expr, local_dict=symbols, evaluate=False)


def _parse_sop_terms(expression: str) -> list[set[Literal]]:
    if "(" in expression or ")" in expression:
        return []

    terms: list[set[Literal]] = []
    for raw_term in expression.split("+"):
        if not raw_term:
            continue
        chunks = [c for c in re.split(r"[.]", raw_term) if c]
        if not chunks:
            continue

        literals: set[Literal] = set()
        for chunk in chunks:
            if not re.fullmatch(r"[A-Za-z]'+|[A-Za-z]", chunk):
                return []
            name = chunk[0]
            positive = not chunk.endswith("'")
            literals.add(Literal(name=name, positive=positive))
        terms.append(literals)

    return terms


def _reduce_by_complement_pairs(terms: list[set[Literal]]):
    current = [set(t) for t in terms]
    trace_steps: list[TraceStep] = []

    changed = True
    while changed:
        changed = False
        used = set()
        new_terms: list[set[Literal]] = []

        for i in range(len(current)):
            if i in used:
                continue
            merged = False
            for j in range(i + 1, len(current)):
                if j in used:
                    continue
                combined = _combine_if_complements(current[i], current[j])
                if combined is not None:
                    left = _term_to_string(current[i])
                    right = _term_to_string(current[j])
                    out = _term_to_string(combined)
                    trace_steps.append(
                        TraceStep(
                            title="Agrupacion de terminos semejantes",
                            expression=f"{left} + {right} = {out}",
                            law="Distributiva + complemento: X.Y + X.Y' = X",
                        )
                    )
                    used.add(i)
                    used.add(j)
                    new_terms.append(combined)
                    merged = True
                    changed = True
                    break
            if not merged and i not in used:
                new_terms.append(current[i])

        current = _dedupe_terms(new_terms)

    return current, trace_steps


def _combine_if_complements(a: set[Literal], b: set[Literal]):
    if len(a) != len(b):
        return None

    a_map = {lit.name: lit.positive for lit in a}
    b_map = {lit.name: lit.positive for lit in b}
    if set(a_map.keys()) != set(b_map.keys()):
        return None

    diff = [name for name in a_map if a_map[name] != b_map[name]]
    if len(diff) != 1:
        return None

    removed = diff[0]
    combined = {Literal(name=k, positive=v) for k, v in a_map.items() if k != removed}
    return combined


def _dedupe_terms(terms: list[set[Literal]]):
    unique = []
    seen = set()
    for term in terms:
        key = tuple(sorted((lit.name, lit.positive) for lit in term))
        if key not in seen:
            seen.add(key)
            unique.append(term)
    return unique


def _term_to_string(term: set[Literal]) -> str:
    if not term:
        return "1"
    ordered = sorted(term, key=lambda x: x.name)
    return ".".join(f"{lit.name}{'' if lit.positive else "'"}" for lit in ordered)


def _terms_to_pretty_expression(terms: list[set[Literal]]) -> str:
    if not terms:
        return "0"
    return " + ".join(_term_to_string(term) for term in terms)


def _pretty_boolean(sympy_str: str) -> str:
    pretty = sympy_str.replace("~", "")

    # Reconstruye negacion como apostrofe para mejor legibilidad.
    pretty = re.sub(r"~([A-Za-z][A-Za-z0-9_]*)", r"\1'", sympy_str)
    pretty = pretty.replace("&", ".")
    pretty = pretty.replace("|", " + ")
    return pretty
