# Reduccion de Expresiones Booleanas (Flask)

Aplicacion web en Python/Flask para simplificar expresiones booleanas con entre 6 y 10 variables.

## Caracteristicas

- Entrada de expresion booleana en formato habitual:
  - `+` para OR
  - `.` o `*` o `·` para AND
  - `'` para NOT (ejemplo: `A'`)
- Soporta entradas con o sin `F = ...`
- Simplificacion minima usando `sympy`
- Modulo opcional de trazabilidad paso a paso con leyes aplicadas

## Instalacion

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecucion

```bash
python app.py
```

Luego abre `http://127.0.0.1:5000`.

## Ejemplo

Entrada:

`F = A.B.C + A.B.C' + D.E.F + D.E.F'`

Salida esperada:

`A.B + D.E`
