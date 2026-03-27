# Judge Extraction Rules

## 1. Objetivo

Este documento define las reglas del **juez semántico** del subsistema **Canonical Extraction Service**.

El juez no extrae información desde cero.  
Su función es **evaluar** una propuesta de extracción canónica generada por:

- el extractor principal
- o el extractor fallback

y decidir si esa propuesta:

- puede aceptarse
- puede aceptarse con observaciones
- debe rechazarse

Además, el juez debe producir una evaluación estructurada con:

- decisión
- puntuación
- desglose por criterios
- errores críticos
- fortalezas
- problemas detectados
- acciones de mejora
- feedback detallado y explícito

---

## 2. Principio general

El juez debe comportarse como un **evaluador riguroso, conservador y trazable**.

Debe comparar:

1. el SMS/documento fuente
2. la propuesta de extracción canónica

y determinar si la propuesta es:

- fiel al contenido fuente
- estructuralmente correcta
- semánticamente prudente
- suficientemente completa
- útil para persistencia y posterior razonamiento

El juez **no debe inventar información nueva** para “arreglar” la propuesta.
Debe evaluar lo recibido.

---

## 3. Entrada evaluada por el juez

El juez recibe:

- el documento fuente (SMS/bitácora)
- una propuesta de extracción canónica

La propuesta suele contener:

- `incident_case`
- `timeline_entries`
- `troubleshooting_actions`
- `extraction_metadata`

---

## 4. Salida esperada del juez

La salida del juez debe tener estructura JSON compatible con este formato conceptual:

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

## 5. Regla de decisión por score

### 5.1 Escala

La puntuación final debe expresarse en escala **1 a 10**.

### 5.2 Umbrales

- **8.0 a 10.0** → `accepted`
- **7.0 a <8.0** → `accepted_with_observations`
- **<7.0** → `rejected`

### 5.3 Regla adicional

Aunque el score parezca aceptable, si existe un **error crítico automático**, la decisión final debe ser:

- `rejected`

---

## 6. Criterios de puntuación

El juez debe puntuar la propuesta usando estos criterios ponderados.

### 6.1 Fidelidad al SMS fuente — 35%

**Pregunta principal:**

- ¿La extracción representa fielmente lo que el SMS dice?

**Evaluar:**

- si evita inventar causa, solución, remediación o equipos
- si no contradice el documento
- si no tergiversa el significado del incidente
- si respeta el sentido operativo del caso

### 6.2 Cobertura de campos relevantes — 20%

**Pregunta principal:**

- ¿La extracción capturó los elementos importantes que sí estaban presentes?

**Evaluar:**

- `header`
- `falla/incidencia`
- `impacto/afectación`
- `tickets`
- `causa explícita` si existe
- `solución explícita` si existe
- `timeline` si hay cronología
- `troubleshooting_actions` si hay acciones claras

### 6.3 Calidad de clasificación estructural — 20%

**Pregunta principal:**

- ¿La propuesta clasifica bien la información dentro del esquema canónico?

**Evaluar:**

- separación entre `timeline_entries` y `troubleshooting_actions`
- secuencia temporal
- consistencia de `event_type`
- consistencia de `action_type`
- consistencia de `action_role`

### 6.4 Prudencia semántica — 15%

**Pregunta principal:**

- ¿La extracción fue prudente y conservadora cuando había ambigüedad?

**Evaluar:**

- si deja campos vacíos cuando no hay evidencia
- si evita afirmar causa raíz no demostrada
- si evita afirmar remediación efectiva no demostrada
- si marca inferencias razonables sin sobreinterpretar

### 6.5 Calidad de metadata de extracción — 10%

**Pregunta principal:**

- ¿La metadata de extracción ayuda a entender la calidad de la propuesta?

**Evaluar:**

- `confidence_notes`
- `warnings`
- `missing_fields`
- `inferred_fields`

La metadata no debe parecer decorativa ni inventada sin sentido.

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

## 8. Regla de error crítico automático

Aunque el score general pueda parecer razonable, la propuesta debe ser `rejected` si existe al menos uno de estos errores críticos:

- causa raíz inventada o no respaldada
- solución técnica inventada
- remediación efectiva inventada
- ticket inexistente
- equipo inexistente o no respaldado
- contradicción fuerte con el SMS
- clasificación gravemente errónea que cambie el significado operativo del caso
- marcar como `troubleshooting_action` algo que claramente no es acción y alterar el razonamiento posterior
- afirmar cierre, estabilidad o resolución sin respaldo textual suficiente

Si existe error crítico:

- agregarlo a `critical_issues`
- incluirlo claramente en `feedback`
- devolver `decision = rejected`

---

## 9. Reglas específicas de evaluación

### 9.1 Sobre `incident_case`

**Evaluar si:**

- `header` es razonable
- `failure_text` representa el problema principal
- `impact_text` representa la afectación real
- `incident_status` no contradice el documento
- `pending_rca` es prudente
- `probable_cause_text` solo se llena con respaldo suficiente
- `resolution_summary` no inventa remediación
- `tickets` son reales y consistentes

## 10. Reglas de prudencia

El juez debe premiar propuestas que:

- no inventan
- no sobreinterpretan
- dejan vacíos razonables
- distinguen claramente evidencia vs inferencia

El juez debe penalizar propuestas que:

- suenan convincentes pero no están respaldadas
- agregan demasiada interpretación técnica
- presentan como hechos cosas que son solo hipótesis

---

## 11. Reglas sobre feedback

El campo `feedback` debe ser:

- explícito
- detallado
- accionable
- útil para un segundo intento del extractor o para el fallback

### 11.1 Qué debe incluir el feedback

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
- qué clasificación fue incorrecta
- qué inferencia fue débil
- qué acción correctiva se espera

### 11.3 Estilo recomendado

El feedback debe sonar como una revisión técnica útil para otro agente o intento posterior.

**Ejemplo de buen estilo:**

> “La propuesta identifica correctamente el impacto y el ticket, pero infiere una causa técnica no respaldada por el SMS. Debe dejar `probable_cause_text` vacío y mover esa interpretación a `warnings` o eliminarla.”

---

## 12. Reglas sobre `strengths`, `issues` e `improvement_actions`

### 12.1 `strengths`

Debe listar los aspectos positivos concretos de la propuesta.

**Ejemplos:**

- “Captura correctamente el ticket principal.”
- “Distingue bien las acciones operativas del timeline.”
- “Mantiene prudencia sobre la causa raíz.”

### 12.2 `issues`

Debe listar problemas concretos.

**Ejemplos:**

- “Clasifica una observación como `troubleshooting_action`.”
- “La metadata usa un `model_name` incorrecto.”
- “Omite parte relevante del impacto.”

### 12.3 `improvement_actions`

Debe proponer correcciones concretas para el siguiente intento.

**Ejemplos:**

- “Eliminar `probable_cause_text` si no existe evidencia explícita.”
- “Reclasificar la línea de monitoreo como `timeline_entry`.”
- “Ajustar `model_name` para reflejar el LLM real usado.”