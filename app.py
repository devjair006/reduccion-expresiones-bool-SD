from flask import Flask, render_template, request

from simplifier import simplify_boolean_expression

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    expression = ""
    show_trace = True
    result = None
    error = None

    if request.method == "POST":
        expression = request.form.get("expression", "").strip()
        show_trace = request.form.get("show_trace") == "on"

        if not expression:
            error = "Debes ingresar una expresion booleana."
        else:
            outcome = simplify_boolean_expression(expression, with_trace=show_trace)
            if outcome.get("error"):
                error = outcome["error"]
            else:
                result = outcome

    return render_template(
        "index.html",
        expression=expression,
        show_trace=show_trace,
        result=result,
        error=error,
    )


if __name__ == "__main__":
    app.run(debug=True)
