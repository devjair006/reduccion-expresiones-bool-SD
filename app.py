import os
from datetime import datetime

from flask import Flask, render_template, request, session

from simplifier import simplify_boolean_expression

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

DEFAULT_MIN_VARIABLES = 6
DEFAULT_MAX_VARIABLES = 10
HISTORY_LIMIT = 8

RECOMMENDED_EXAMPLES = [
    {
        "title": "Complemento Basico",
        "expression": "F = A.B + A.B'",
        "min": 2,
        "max": 4,
        "hint": "Mira como X.Y + X.Y' se reduce a X.",
    },
    {
        "title": "AND Implicito",
        "expression": "F = A(B+C)+D+E+F+G+H",
        "min": 6,
        "max": 10,
        "hint": "Valida multiplicacion implicita sin usar punto.",
    },
    {
        "title": "Constantes 0 y 1",
        "expression": "F = X*0 + Y*1",
        "min": 2,
        "max": 5,
        "hint": "Comprueba anulacion e identidad.",
    },
    {
        "title": "Caso DNF Grande",
        "expression": "F = A.B.C + A.B.C' + D.E.F + D.E.F' + G.H.I + G.H.I'",
        "min": 9,
        "max": 12,
        "hint": "Ideal para ver trazabilidad paso a paso.",
    },
]


@app.route("/", methods=["GET", "POST"])
def index():
    expression = ""
    show_trace = True
    check_equivalence = False
    min_variables = DEFAULT_MIN_VARIABLES
    max_variables = DEFAULT_MAX_VARIABLES
    result = None
    error = None
    info = None
    history = _get_history()

    if request.method == "POST":
        action = request.form.get("action", "simplify")
        if action == "clear_history":
            session["expression_history"] = []
            session.modified = True
            history = []
            info = "Se borro el historial de expresiones."
            return render_template(
                "index.html",
                expression=expression,
                show_trace=show_trace,
                check_equivalence=check_equivalence,
                min_variables=min_variables,
                max_variables=max_variables,
                result=result,
                error=error,
                info=info,
                history=history,
                recommended_examples=RECOMMENDED_EXAMPLES,
            )

        expression = request.form.get("expression", "").strip()
        show_trace = request.form.get("show_trace") == "on"
        check_equivalence = request.form.get("check_equivalence") == "on"

        min_raw = request.form.get("min_variables", "").strip()
        max_raw = request.form.get("max_variables", "").strip()

        min_variables, min_error = _parse_positive_int(
            min_raw, DEFAULT_MIN_VARIABLES, "minimo"
        )
        max_variables, max_error = _parse_positive_int(
            max_raw, DEFAULT_MAX_VARIABLES, "maximo"
        )

        if min_error:
            error = min_error
        elif max_error:
            error = max_error
        elif min_variables > max_variables:
            error = "El valor minimo de variables no puede ser mayor al maximo."

        if not error and not expression:
            error = "Debes ingresar una expresion booleana."
        elif not error:
            outcome = simplify_boolean_expression(
                expression,
                with_trace=show_trace,
                min_variables=min_variables,
                max_variables=max_variables,
                with_truth_table=check_equivalence,
            )
            if outcome.get("error"):
                error = outcome["error"]
            else:
                result = outcome
                history = _append_history_entry(
                    history=history,
                    expression=expression,
                    simplified=outcome["simplified_expression"],
                    min_variables=min_variables,
                    max_variables=max_variables,
                    checked_equivalence=check_equivalence,
                )
                session["expression_history"] = history
                session.modified = True

    return render_template(
        "index.html",
        expression=expression,
        show_trace=show_trace,
        check_equivalence=check_equivalence,
        min_variables=min_variables,
        max_variables=max_variables,
        result=result,
        error=error,
        info=info,
        history=history,
        recommended_examples=RECOMMENDED_EXAMPLES,
    )


def _parse_positive_int(raw_value: str, default: int, label: str) -> tuple[int, str | None]:
    if not raw_value:
        return default, None

    try:
        parsed = int(raw_value)
    except ValueError:
        return default, f"El valor {label} de variables debe ser un numero entero."

    if parsed < 1:
        return default, f"El valor {label} de variables debe ser mayor o igual a 1."

    return parsed, None


def _get_history() -> list[dict]:
    history = session.get("expression_history", [])
    if isinstance(history, list):
        return history
    return []


def _append_history_entry(
    history: list[dict],
    expression: str,
    simplified: str,
    min_variables: int,
    max_variables: int,
    checked_equivalence: bool,
) -> list[dict]:
    filtered_history = [entry for entry in history if entry.get("expression") != expression]
    filtered_history.insert(
        0,
        {
            "expression": expression,
            "simplified": simplified,
            "min": min_variables,
            "max": max_variables,
            "check_equivalence": checked_equivalence,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        },
    )
    return filtered_history[:HISTORY_LIMIT]


if __name__ == "__main__":
    app.run(debug=True)
