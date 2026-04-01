# Judge Extraction Rules

## 1. Objetivo

Este documento define las reglas del **juez semántico** del subsistema **Canonical Extraction Service**.

El juez no extrae información. Su función es **evaluar** una propuesta de extracción canónica generada por el extractor principal o el fallback y decidir si esa propuesta:

- puede aceptarse
- puede aceptarse con observaciones
- debe rechazarse

Además, debe producir una evaluación estructurada con:

- `decision`
- `score`
- `score_breakdown`
- `critical_issues`
- `strengths`
- `issues`
- `improvement_actions`
- `feedback`

---

## 2. Principio general

El juez debe comportarse como un **evaluador riguroso, conservador, trazable y estricto con omisiones**.

Debe comparar:

1. el SMS/documento fuente
2. la propuesta de extracción canónica

y determinar si la propuesta es:

- fiel al contenido fuente
- estructuralmente correcta
- semánticamente prudente
- suficientemente completa
- útil para persistencia y razonamiento posterior

El juez **no debe inventar información** para corregir la propuesta.  
Debe evaluar lo recibido.

---

## 3. Entrada evaluada

El juez recibe:

- el documento fuente
- una propuesta de extracción canónica

La propuesta suele contener:

- `incident_case`
- `timeline_entries`
- `troubleshooting_actions`
- `extraction_metadata`

---

## 4. Salida esperada

La salida del juez debe ser JSON compatible con esta estructura conceptual:

```json
{
  "decision": "accepted | accepted_with_observations | rejected",
  "score": 0.0,
  "score_breakdown": {
    "fidelity": 0.0,
    "coverage": 0.0,
    "structural_classification": 0.0,
    "semantic_prudence": 0.0,
    "metadata_quality": 0.0
  },
  "critical_issues": [],
  "strengths": [],
  "issues": [],
  "improvement_actions": [],
  "feedback": ""
}

---

## 5. Decisión por score

### 5.1 Escala
La puntuación final debe expresarse en escala **1 a 10**.

### 5.2 Umbrales
- **9.0 a 10.0** → `accepted`
- **8.0 a <9.0** → `accepted_with_observations`
- **<8.0** → `rejected`

### 5.3 Regla crítica
Aunque el score parezca aceptable, si existe un **error crítico automático**, la decisión final debe ser:

- `rejected`

### 5.4 Reglas de techo de score
Aunque no exista error crítico automático, el juez no debe asignar score alto ni decisión `accepted` si la propuesta presenta:

- `case_id` vacío, nulo o inconsistente cuando el SMS contiene ticket explícito
- campos explícitos del SMS dejados vacíos o `null` sin justificación
- cobertura gravemente baja de `timeline_entries`
- cobertura gravemente baja de `troubleshooting_actions`

Aplicar estas restricciones:

- si `case_id` viene vacío y el SMS sí tiene ticket explícito, la propuesta no puede ser `accepted`
- si el SMS contiene bitácora multi-hito y la propuesta conserva muy pocos `timeline_entries`, la propuesta no puede recibir `coverage` alta
- si el SMS contiene varias acciones técnicas y la propuesta conserva solo una acción o una fracción mínima del troubleshooting real, la propuesta no puede recibir `coverage` alta

---

## 6. Criterios de puntuación

### 6.1 Fidelidad al SMS fuente — 35%
Evaluar si la propuesta:

- evita inventar causa, solución, remediación o equipos
- no contradice el SMS
- no tergiversa el significado operativo del caso
- respeta el sentido operativo del incidente

### 6.2 Cobertura de campos relevantes — 20%
Evaluar si la propuesta capturó los elementos importantes presentes en la fuente.

Revisar:

- `header`
- `failure_text`
- `impact_text`
- `tickets`
- `case_id`
- `start_time` si existe explícitamente
- `solution_time` si existe explícitamente
- `probable_cause_text` si existe causa explícita
- `resolution_summary` si existe solución explícita
- `timeline_entries` si existe bitácora operativa
- `troubleshooting_actions` si existen acciones técnicas claras

#### Regla de severidad para campos faltantes o null
El juez debe ser estricto cuando el SMS aporta evidencia explícita y la propuesta deja el campo vacío, nulo o ausente.

Penalizar fuertemente `coverage` cuando:

- un ticket explícito existe y `case_id` está vacío o ausente
- el SMS tiene fecha/hora explícita de inicio y falta `start_time`
- el SMS tiene fecha/hora explícita de fin/solución y falta `solution_time`
- existe causa explícita y no se refleja
- existe solución explícita y no se refleja
- el SMS contiene una bitácora rica y la propuesta la resume en exceso
- el SMS contiene varias acciones técnicas y la propuesta conserva muy pocas

Los faltantes/null relevantes deben aparecer explícitamente en:

- `issues`
- `improvement_actions`
- `feedback`

### 6.3 Calidad de clasificación estructural — 20%
Evaluar:

- separación razonable entre `timeline_entries` y `troubleshooting_actions`
- secuencia temporal
- consistencia de `action_type`
- consistencia de `action_role`
- calidad estructural general de la propuesta

### 6.4 Prudencia semántica — 15%
Evaluar si la propuesta:

- deja vacíos razonables cuando no hay evidencia
- evita afirmar causa raíz no demostrada
- evita afirmar remediación efectiva no demostrada
- distingue evidencia de inferencia
- no sobreinterpreta

### 6.5 Calidad de metadata — 10%
Evaluar:

- `confidence_notes`
- `warnings`
- `missing_fields`
- `inferred_fields`

La metadata debe ser útil, no decorativa.

---

## 7. Score breakdown obligatorio

El juez debe devolver siempre `score_breakdown` con estas claves:

- `fidelity`
- `coverage`
- `structural_classification`
- `semantic_prudence`
- `metadata_quality`

Cada valor debe estar en escala **1 a 10**.

El campo `score` debe reflejar el resultado ponderado final.

---

## 8. Errores críticos automáticos

La propuesta debe ser `rejected` si existe al menos uno de estos errores críticos:

- causa raíz inventada o no respaldada
- solución técnica inventada
- remediación efectiva inventada
- ticket inexistente
- equipo inexistente o no respaldado
- contradicción fuerte con el SMS
- clasificación gravemente errónea que cambie el significado operativo del caso
- marcar como `troubleshooting_action` algo que claramente no es acción y alterar el razonamiento posterior
- afirmar cierre, estabilidad o resolución sin respaldo textual suficiente
- `case_id` vacío, nulo o ausente cuando el SMS contiene un ticket explícito y claramente identificable
- `case_id` inconsistente con los tickets explícitos del SMS
- omitir completamente los tickets explícitos del SMS y aun así presentar la propuesta como correcta

Si existe error crítico:

- agregarlo a `critical_issues`
- incluirlo claramente en `feedback`
- devolver `decision = rejected`

---

## 9. Reglas específicas de evaluación

### 9.1 Sobre `incident_case`
Evaluar si:

- `header` es razonable
- `failure_text` representa el problema principal
- `impact_text` representa la afectación real
- `start_time` solo se llena cuando existe una fecha/hora explícita y clara de inicio
- `solution_time` solo se llena cuando existe una fecha/hora explícita y clara de fin/solución
- `incident_status` no contradice el SMS
- `probable_cause_text` solo se llena con respaldo suficiente
- `resolution_summary` no inventa remediación
- `tickets` son reales y consistentes
- `case_id` está presente cuando el SMS contiene ticket explícito
- `case_id` corresponde a un ticket real del SMS y no a texto libre o valor incompleto

#### Regla de severidad para `case_id`
- Si el SMS contiene ticket explícito y `case_id` está vacío, nulo o inconsistente, es una falla grave.
- En ese escenario, la propuesta no debe ser `accepted`.
- Si contradice los tickets explícitos del SMS, debe tratarse como error crítico.

#### Regla de severidad para tiempos faltantes
- Si el SMS contiene `FECHA/H.Inicio`, `H.Inicio` o equivalente claro y falta `start_time`, debe penalizarse en `coverage`.
- Si el SMS contiene `FECHA/H.Fin`, `Hora de solución`, `Fecha de solución` o equivalente claro y falta `solution_time`, debe penalizarse en `coverage`.
- Estos faltantes deben mencionarse explícitamente en `issues`, `improvement_actions` y `feedback`.

### 9.2 Sobre `timeline_entries`
El juez debe evaluar `timeline_entries` con criterio estricto cuando el SMS contenga una **bitácora operativa explícita**.

#### Qué es bitácora operativa
Es el bloque del SMS que narra la evolución temporal del incidente, normalmente después de encabezados como:

- `ACCIONES:`
- `SOLUCIONADO:`

o equivalentes.

#### Regla general
- Si existe bitácora operativa explícita, el juez debe verificar si la propuesta refleja de manera suficiente esa cronología.
- Cuando la bitácora contiene múltiples entradas cronológicas que inician con hora, cada una debe evaluarse como un candidato fuerte a `timeline_entry`.
- No toda hora del SMS es automáticamente timeline; la exigencia aplica al cuerpo de la bitácora operativa.

#### Penalizar cuando
- faltan múltiples entradas horarias relevantes
- se omiten pasos intermedios importantes
- se resume una bitácora extensa a muy pocos hitos
- se pierden eventos de revisión, descarte, coordinación, autorización, validación o conformidad

#### Regla de severidad adicional
- Si el SMS contiene una bitácora claramente multi-hito y la propuesta conserva solo 2 o 3 hitos principales sin suficiente justificación, el juez debe castigar fuertemente `coverage`.
- No basta con inicio, solución y cierre cuando la fuente contiene más proceso operativo.

#### Cobertura adecuada
Una propuesta tiene buena cobertura de `timeline_entries` si:

- representa de forma razonablemente completa la secuencia del incidente
- conserva hitos relevantes del desarrollo temporal
- permite reconstruir el flujo sin perder pasos importantes

### 9.3 Sobre `troubleshooting_actions`
El juez debe evaluar `troubleshooting_actions` con rigor cuando el SMS describa acciones técnicas, diagnósticas o de validación.

#### Regla general
- Si el SMS contiene revisión, descarte, validación, rollback, monitoreo, revisión de logs, revisión de servidores, revisión de IPs, revisión de pases o validaciones funcionales, el juez debe verificar si esas acciones fueron reflejadas adecuadamente.
- No basta con capturar únicamente la remediación final si el SMS describe varias acciones previas.

#### Penalizar cuando
- solo aparece la acción final y faltan acciones diagnósticas previas
- faltan revisiones técnicas explícitas
- faltan descartes claramente descritos
- faltan validaciones técnicas o funcionales relevantes
- la propuesta reduce el troubleshooting a una sola acción cuando el SMS describe un proceso técnico más amplio

#### Regla de severidad adicional
- Si el SMS describe un proceso técnico claramente multi-hito y la propuesta conserva solo una `troubleshooting_action` o una fracción mínima del troubleshooting real, el juez debe castigar fuertemente `coverage`.
- Si la omisión del troubleshooting intermedio impide entender cómo se llegó a la solución, la decisión debe tender a `accepted_with_observations` o `rejected`.

#### Cobertura adecuada
Una propuesta tiene buena cobertura de `troubleshooting_actions` si:

- representa las acciones técnicas relevantes del SMS
- distingue razonablemente entre diagnóstico, remediación y validación
- conserva las acciones que permiten entender cómo se llegó a la solución

#### Clasificación
El juez debe revisar si las acciones fueron clasificadas con prudencia:

- revisión o descarte → tienden a diagnóstico
- rollback o corrección → tienden a remediación
- validación o conformidad → tienden a validación

Si la clasificación es imperfecta pero razonable, puede aceptarse con observaciones.  
Si la propuesta omite casi todo el troubleshooting o cambia fuertemente su significado, debe penalizarse con mayor severidad.

---

## 10. Reglas de prudencia

El juez debe premiar propuestas que:

- no inventan
- no sobreinterpretan
- dejan vacíos razonables cuando no hay evidencia
- distinguen evidencia vs inferencia

El juez debe penalizar propuestas que:

- suenan convincentes pero no están respaldadas
- agregan interpretación técnica excesiva
- presentan como hechos cosas que son solo hipótesis

### Regla importante sobre vacíos razonables vs vacíos incorrectos
- Un valor vacío o `null` es correcto si el SMS no aporta evidencia suficiente.
- Un valor vacío o `null` es incorrecto si el SMS sí aporta evidencia explícita o muy clara.
- El juez debe distinguir ambos casos y reflejarlo en `issues` y `feedback`.

---

## 11. Reglas sobre feedback

El campo `feedback` debe ser:

- explícito
- detallado
- accionable
- útil para un segundo intento o para el fallback

### 11.1 Qué debe incluir
El feedback debe indicar claramente:

- si la propuesta es aceptable o no
- qué hizo bien
- qué hizo mal
- qué debe corregirse
- por qué se tomó la decisión

### 11.2 Qué debe evitar
No usar feedback genérico como:

- “mejorar extracción”
- “faltan detalles”
- “la propuesta no es buena”

Debe especificar:

- qué campo falló
- qué dato faltó o vino `null`
- qué clasificación fue incorrecta
- qué inferencia fue débil
- qué corrección se espera

### 11.3 Regla obligatoria sobre faltantes/null
Si la propuesta deja vacío, nulo o ausente un dato importante que sí estaba presente en el SMS, el juez debe:

- mencionarlo explícitamente en `issues`
- convertirlo en una corrección concreta en `improvement_actions`
- describirlo claramente en `feedback`

### 11.4 Estilo recomendado
El feedback debe sonar como una revisión técnica útil para otro agente.

Ejemplo:

> “La propuesta identifica correctamente el ticket y el impacto, pero omite `solution_time` pese a que el SMS contiene una fecha/hora de fin explícita. Debe poblar ese campo y ampliar el timeline intermedio.”

---

## 12. Reglas sobre `strengths`, `issues` e `improvement_actions`

### 12.1 `strengths`
Debe listar aspectos positivos concretos.

Ejemplos:
- “Captura correctamente el ticket principal.”
- “Representa bien la cronología operativa.”
- “Mantiene prudencia sobre la causa raíz.”

### 12.2 `issues`
Debe listar problemas concretos.

Incluir especialmente:

- campos faltantes o `null` que debieron poblarse
- cobertura insuficiente
- clasificación incorrecta
- metadata inconsistente

Ejemplos:
- “Omite `solution_time` pese a existir fecha/hora de fin explícita.”
- “Reduce una bitácora multi-hito a solo 3 `timeline_entries`.”
- “Conserva solo una acción de troubleshooting en un proceso técnico claramente más amplio.”

### 12.3 `improvement_actions`
Debe proponer correcciones concretas para el siguiente intento.

Ejemplos:
- “Poblar `case_id` desde el ticket explícito del SMS.”
- “Agregar `solution_time` usando la fecha/hora de fin explícita.”
- “Ampliar `timeline_entries` para conservar los hitos intermedios relevantes.”
- “Agregar acciones diagnósticas omitidas antes de la remediación final.”