# Reduccion de Expresiones Booleanas (Flask)

Aplicacion web en Python/Flask para simplificar expresiones booleanas con rango de variables configurable.

## Caracteristicas

- Entrada de expresion booleana en formato habitual:
  - `+` para OR
  - `.` o `*` o `·` para AND
  - `'` para NOT (ejemplo: `A'`)
  - Constantes numericas permitidas: `0` y `1`
- Soporta entradas con o sin `F = ...`
- Simplificacion minima usando `sympy`
- Modulo opcional de trazabilidad paso a paso con leyes aplicadas
- Validaciones sintacticas (parentesis, operadores y caracteres permitidos)
- Rango configurable de variables min/max desde la interfaz
- Validacion opcional de equivalencia por tabla de verdad
- Historial reciente de expresiones (recuperable con un click)
- Ejemplos recomendados y panel visual de guia de uso

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

## Como usar la app

1. Escribe tu expresion booleana (con o sin `F = ...`).
2. Ajusta el rango de variables (`min` y `max`) segun tu ejercicio.
3. Activa `Mostrar trazabilidad` si quieres ver leyes aplicadas.
4. Activa `Validar equivalencia` para generar tabla de verdad.
5. Revisa la expresion final y, si aplica, la tabla para confirmar equivalencia.

Tambien puedes usar los botones de ejemplos en la interfaz para cargar casos de prueba al instante.

## Ejemplo

Entrada:

`F = A.B.C + A.B.C' + D.E.F + D.E.F'`

Salida esperada:

`A.B + D.E`
