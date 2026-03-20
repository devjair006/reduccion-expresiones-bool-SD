import re
from dataclasses import dataclass
from itertools import product

from sympy import Symbol, false, true
from sympy.logic.boolalg import simplify_logic, to_dnf


ALLOWED_VAR_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*|[0-9]+|[+.'()]")
INVALID_CHAR_RE = re.compile(r"[^A-Za-z0-9_+.*·'()\s]")
RESERVED_IDENTIFIERS = {"True", "False"}


@dataclass(frozen=True)
class Literal:
    name: str
    positive: bool = True


@dataclass
class TraceStep:
    title: str
    expression: str
    law: str


def simplify_boolean_expression(
    raw_expression: str,
    with_trace: bool = True,
    min_variables: int = 6,
    max_variables: int = 10,
    with_truth_table: bool = False,
    truth_table_limit: int = 64,
) -> dict:
    if min_variables < 1 or max_variables < 1:
        return {"error": "Los limites de variables deben ser enteros positivos."}
    if min_variables > max_variables:
        return {"error": "El minimo de variables no puede ser mayor al maximo."}

    expression = _extract_rhs(raw_expression)
    normalized = _normalize_symbols(expression)

    try:
        tokens = _tokenize_expression(normalized)
        _validate_expression_syntax(tokens)
    except ValueError as exc:
        return {"error": str(exc)}

    variables = sorted({token for token in tokens if _is_identifier(token)})

    if not variables:
        return {"error": "No se detectaron variables en la expresion."}

    if len(variables) < min_variables or len(variables) > max_variables:
        return {
            "error": (
                "La expresion debe contener entre "
                f"{min_variables} y {max_variables} variables distintas "
                f"(actual: {len(variables)})."
            )
        }

    try:
        sympy_expr = _to_sympy_boolean(tokens, variables)
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
        "variable_range": {"min": min_variables, "max": max_variables},
        "simplified_expression": _pretty_boolean(str(simplified)),
    }

    if with_trace:
        trace = _build_trace(normalized, variables, sympy_expr, simplified)
        result["trace"] = [step.__dict__ for step in trace]

    if with_truth_table:
        table = _build_truth_table(sympy_expr, simplified, variables, limit=truth_table_limit)
        result["equivalence_check"] = {
            "is_equivalent": table["is_equivalent"],
            "total_rows": table["total_rows"],
            "displayed_rows": table["displayed_rows"],
            "truncated": table["truncated"],
        }
        result["truth_table"] = table
    else:
        result["equivalence_check"] = None

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
    expr = re.sub(r"\s+", "", expression)
    expr = expr.replace("·", ".")
    expr = expr.replace("*", ".")
    return expr


def _is_identifier(token: str) -> bool:
    return bool(ALLOWED_VAR_RE.fullmatch(token))


def _is_factor_start(token: str | None) -> bool:
    return token is not None and (_is_identifier(token) or token in {"0", "1", "("})


def _tokenize_expression(expression: str) -> list[str]:
    if not expression:
        raise ValueError("Debes ingresar una expresion booleana.")

    invalid_chars = sorted(set(INVALID_CHAR_RE.findall(expression)))
    if invalid_chars:
        chars = ", ".join(f"'{char}'" for char in invalid_chars)
        raise ValueError(f"Se detectaron caracteres no permitidos: {chars}.")

    tokens: list[str] = []
    index = 0
    for match in TOKEN_RE.finditer(expression):
        if match.start() != index:
            fragment = expression[index : match.start()]
            raise ValueError(f"No se pudo interpretar la secuencia '{fragment}'.")
        token = match.group(0)
        if token.isdigit() and token not in {"0", "1"}:
            raise ValueError(
                f"Constante numerica invalida '{token}'. Solo se permiten 0 y 1."
            )
        if token in RESERVED_IDENTIFIERS:
            raise ValueError(
                f"'{token}' es una palabra reservada; usa otro nombre de variable."
            )
        tokens.append(token)
        index = match.end()

    if index != len(expression):
        fragment = expression[index:]
        raise ValueError(f"No se pudo interpretar la secuencia '{fragment}'.")

    if not tokens:
        raise ValueError("Debes ingresar una expresion booleana.")

    return tokens


def _validate_expression_syntax(tokens: list[str]) -> None:
    parser = _BooleanSyntaxParser(tokens)
    parser.parse()


class _BooleanSyntaxParser:
    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.position = 0

    def parse(self) -> None:
        self._parse_expression()
        if self._peek() is not None:
            token = self._peek()
            if token == ")":
                raise ValueError("Hay un parentesis ')' de cierre sin apertura.")
            raise ValueError(f"Token inesperado '{token}'.")

    def _parse_expression(self) -> None:
        self._parse_term()
        while self._peek() == "+":
            self._consume()
            self._parse_term()

    def _parse_term(self) -> None:
        self._parse_factor()
        while True:
            token = self._peek()
            if token == ".":
                self._consume()
                self._parse_factor()
                continue
            if _is_factor_start(token):
                self._parse_factor()
                continue
            return

    def _parse_factor(self) -> None:
        self._parse_primary()
        while self._peek() == "'":
            self._consume()

    def _parse_primary(self) -> None:
        token = self._peek()
        if token is None:
            raise ValueError("La expresion termino de forma incompleta.")

        if _is_identifier(token) or token in {"0", "1"}:
            self._consume()
            return

        if token == "(":
            self._consume()
            if self._peek() == ")":
                raise ValueError("No se permiten parentesis vacios '()'.")
            self._parse_expression()
            if self._peek() != ")":
                raise ValueError("Falta cerrar un parentesis ')'.")
            self._consume()
            return

        if token == ")":
            raise ValueError("Hay un parentesis ')' de cierre sin apertura.")
        if token in {"+", "."}:
            raise ValueError(f"Operador '{token}' en posicion invalida.")
        if token == "'":
            raise ValueError(
                "El apostrofe (') debe ir despues de una variable o parentesis."
            )

        raise ValueError(f"Token inesperado '{token}'.")

    def _peek(self) -> str | None:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]

    def _consume(self) -> str:
        token = self._peek()
        if token is None:
            raise ValueError("La expresion termino de forma incompleta.")
        self.position += 1
        return token


def _to_sympy_boolean(tokens: list[str], variables: list[str]):
    symbols = {name: Symbol(name) for name in variables}
    parser = _BooleanExpressionBuilder(tokens, symbols)
    return parser.parse()


class _BooleanExpressionBuilder:
    def __init__(self, tokens: list[str], symbols: dict[str, Symbol]):
        self.tokens = tokens
        self.symbols = symbols
        self.position = 0

    def parse(self):
        expression = self._parse_expression()
        if self._peek() is not None:
            token = self._peek()
            raise ValueError(f"Token inesperado '{token}'.")
        return expression

    def _parse_expression(self):
        expression = self._parse_term()
        while self._peek() == "+":
            self._consume()
            expression = expression | self._parse_term()
        return expression

    def _parse_term(self):
        expression = self._parse_factor()
        while True:
            token = self._peek()
            if token == ".":
                self._consume()
                expression = expression & self._parse_factor()
                continue
            if _is_factor_start(token):
                expression = expression & self._parse_factor()
                continue
            return expression

    def _parse_factor(self):
        expression = self._parse_primary()
        while self._peek() == "'":
            self._consume()
            expression = ~expression
        return expression

    def _parse_primary(self):
        token = self._peek()
        if token is None:
            raise ValueError("La expresion termino de forma incompleta.")

        if token == "(":
            self._consume()
            expression = self._parse_expression()
            if self._peek() != ")":
                raise ValueError("Falta cerrar un parentesis ')'.")
            self._consume()
            return expression

        if token == "1":
            self._consume()
            return true

        if token == "0":
            self._consume()
            return false

        if _is_identifier(token):
            self._consume()
            return self.symbols[token]

        raise ValueError(f"Token inesperado '{token}'.")

    def _peek(self) -> str | None:
        if self.position >= len(self.tokens):
            return None
        return self.tokens[self.position]

    def _consume(self) -> str:
        token = self._peek()
        if token is None:
            raise ValueError("La expresion termino de forma incompleta.")
        self.position += 1
        return token


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
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*'?", chunk):
                return []
            name = chunk[:-1] if chunk.endswith("'") else chunk
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


def _build_truth_table(original_expr, simplified_expr, variables: list[str], limit: int = 64) -> dict:
    effective_limit = max(1, limit)
    total_rows = 2 ** len(variables)
    rows = []
    all_match = True
    symbols = [Symbol(name) for name in variables]

    for row_index, bits in enumerate(product((0, 1), repeat=len(variables))):
        assignment = {symbol: bool(bit) for symbol, bit in zip(symbols, bits)}
        original_value = bool(original_expr.subs(assignment))
        simplified_value = bool(simplified_expr.subs(assignment))
        is_match = original_value == simplified_value
        all_match = all_match and is_match

        if row_index < effective_limit:
            rows.append(
                {
                    "values": {name: bit for name, bit in zip(variables, bits)},
                    "input": int(original_value),
                    "simplified": int(simplified_value),
                    "match": is_match,
                }
            )

    return {
        "is_equivalent": all_match,
        "total_rows": total_rows,
        "displayed_rows": len(rows),
        "truncated": total_rows > effective_limit,
        "rows": rows,
    }


def _pretty_boolean(sympy_str: str) -> str:
    pretty = sympy_str
    pretty = pretty.replace("True", "1")
    pretty = pretty.replace("False", "0")

    # Reconstruye negacion simple como apostrofe para mejor legibilidad.
    pretty = re.sub(r"~([A-Za-z][A-Za-z0-9_]*)", r"\1'", pretty)
    pretty = pretty.replace("&", ".")
    pretty = pretty.replace("|", " + ")
    return pretty
