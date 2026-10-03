BEGIN;

-- Actualiza sólo los placeholders originales; conserva cualquier otro código.
UPDATE behaviors
SET code = $program$from primitives.behaviours import balanced

def decide(observation):
    return balanced(observation)$program$,
    description = 'El más cercano busca la pelota; los demás acompañan manteniendo su línea.'
WHERE name = 'Equilibrado' AND btrim(code) = 'print("hola futbot!")';

UPDATE behaviors
SET code = $program$from primitives.behaviours import offensive

def decide(observation):
    return offensive(observation)$program$,
    description = 'Busca la pelota en toda la cancha y patea hacia el arco rival.'
WHERE name = 'Ofensivo' AND btrim(code) = 'print("hola futbot!")';

UPDATE behaviors
SET code = $program$from primitives.behaviours import defensive

def decide(observation):
    return defensive(observation)$program$,
    description = 'Protege su posición y busca la pelota cuando está en su mitad de cancha.'
WHERE name = 'Defensivo' AND btrim(code) = 'print("hola futbot!")';

COMMIT;
