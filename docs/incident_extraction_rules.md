# Incident Extraction Rules

## 1. Objetivo

Este documento define las reglas de extracción, clasificación y validación para convertir SMS bitácora operativos en un esquema canónico persistible por el Servicio de Memoria Operativa de Incidentes.

La extracción debe funcionar incluso cuando el SMS:
- sea redactado por personas distintas
- tenga ligeras variaciones de sintaxis
- cambie gradualmente de formato
- mezcle etiquetas, texto libre y secciones operativas

El objetivo no es preservar una plantilla exacta, sino extraer significado operativo de forma consistente.

---

## 2. Principio general

Los SMS deben tratarse como **documentos operativos semi-estructurados**.

El sistema debe:
1. leer el documento completo
2. identificar secciones y patrones útiles
3. extraer información al esquema canónico
4. validar consistencia
5. persistir sin inventar información no respaldada

---

## 3. Esquema canónico objetivo

El extractor debe intentar poblar, cuando sea posible, los siguientes conceptos:

### IncidentCase
- case_id
- source_type
- header
- failure_text
- impact_text
- solution_time
- status
- pending_rca
- raw_sms
- probable_cause_text
- resolution_summary
- component_types
- components_affected
- services_affected
- symptoms
- teams_involved
- tickets
- tags
- parser_output_json
- enrichment_json

### IncidentTimelineEntry
- case_id
- event_time
- event_text
- event_type
- team
- action_detected
- observation_detected
- sequence_order

### TroubleshootingAction
- case_id
- action_text
- action_type
- action_role
- target_component
- outcome
- was_effective
- sequence_order

---

## 4. Etiquetas o secciones que suelen aparecer

Estas etiquetas suelen mantenerse, aunque pueden variar ligeramente en redacción, orden o estilo:

- FALLA
- IMPACTO
- SOLUCIONADO
- INCIDENCIA
- AFECTACIÓN
- ACCIONES
- CAUSA
- SOLUCIÓN
- TICKET
- FECHA/H.Inicio
- FECHA/H.Fin
- HORA DE SOLUCIÓN

Estas etiquetas deben tratarse como **indicadores útiles**, no como dependencias rígidas.

---

## 5. Reglas de extracción generales

### 5.1 Header
- El encabezado suele corresponder a la primera línea significativa del mensaje.
- Puede incluir nombres de área, sistemas, ticket o título operativo.
- Debe conservarse tal como aparece, salvo limpieza básica de espacios.

### 5.2 Tickets
- Extraer identificadores como:
  - INC...
  - REQ...
  - TAS...
  - otros patrones operativos equivalentes
- Un mensaje puede contener múltiples tickets o referencias relacionadas.
- El ticket principal del incidente debe priorizarse cuando sea evidente.

### 5.3 Failure / Incidencia principal
- `failure_text` debe representar el problema principal descrito en el SMS.
- Puede venir bajo:
  - FALLA
  - INCIDENCIA
  - o una redacción libre equivalente
- Si hay varias frases, se debe sintetizar el problema principal sin inventar información.

### 5.4 Impact
- `impact_text` debe representar la afectación operativa descrita.
- Puede venir bajo:
  - IMPACTO
  - AFECTACIÓN
  - o texto equivalente
- Debe priorizarse el impacto en usuarios, transacciones, accesos, servicios o portales.

### 5.5 Cause
- `probable_cause_text` solo debe poblarse si el SMS aporta evidencia suficiente.
- Puede venir bajo:
  - CAUSA
  - diagnóstico técnico explícito
  - validación del equipo técnico
- Si la causa no está clara, no inventarla.

### 5.6 Solution / Resolution
- `resolution_summary` debe representar cómo terminó el incidente.
- Puede venir bajo:
  - SOLUCIÓN
  - SOLUCIONADO
  - o frases equivalentes de restablecimiento/cierre
- Si no hubo acción técnica explícita, debe indicarse eso de forma fiel.

---

## 6. Reglas sobre status y pending_rca

### 6.1 status
- El campo `status` representa el estado operativo del registro según el modelo vigente del sistema.
- Mientras el modelo actual no cambie, se permite usar:
  - `closed`
  - `monitoring`
  - `stabilized`
  - `open`
- En SMS bitácora ya cerrados/solucionados, normalmente el status sugerido será `closed`.

### 6.2 pending_rca
- Si el SMS menciona que el RCA está pendiente, o se deduce que falta análisis formal de causa raíz, usar:
  - `pending_rca = true`
- Si no hay evidencia de RCA pendiente, no asumir automáticamente que existe RCA.

### 6.3 Regla aprobada del proyecto
- Si el SMS contiene frases equivalentes a **“Se cierra SMS”**, el status sugerido es `closed`.
- Si el SMS indica estabilidad pero deja RCA pendiente, también puede modelarse como `closed` con `pending_rca = true`.

---

## 7. Reglas para IncidentTimelineEntry

### 7.1 Qué representa
Cada `IncidentTimelineEntry` representa un hito de la evolución temporal del incidente.

### 7.2 Qué debe incluir
- hora o referencia temporal si existe
- texto de la línea o hito
- clasificación tentativa (`event_type`) si se puede inferir
- equipo responsable o mencionado, si existe
- orden secuencial

### 7.3 Cuándo crear timeline entries
Crear entradas cuando existan:
- líneas cronológicas con hora
- pasos secuenciales
- acciones narradas en orden temporal
- bloque SOLUCIONADO o ACCIONES
- lista operativa de revisión/desarrollo

### 7.4 Qué no hacer
No perder el texto original del hito.
La clasificación debe complementar, no reemplazar, la evidencia textual.

---

## 8. Reglas para TroubleshootingAction

### 8.1 Qué representa
`TroubleshootingAction` representa una **acción operativa ejecutada**, no cualquier línea del timeline.

### 8.2 Solo convertir en action cuando haya acción explícita
Ejemplos válidos:
- se reporta a DBA
- se apertura sala
- se revisan logs
- se deriva a otro equipo
- se solicita rollback
- se autoriza rollback
- se ejecuta rollback
- se mantiene en monitoreo
- se cierra SMS
- se finaliza sala

### 8.3 No convertir automáticamente en action
No convertir si la línea solo expresa:
- síntoma
- observación
- confirmación de estado
- diagnóstico sin acción
- resultado pasivo

### 8.4 action_type
Describe qué se hizo.
Ejemplos:
- escalation
- monitoring
- derivation
- rollback
- validation
- closure

### 8.5 action_role
Describe el papel operativo.
Ejemplos:
- coordination
- monitoring
- remediation
- validation
- administrative_closure

### 8.6 was_effective
- `true` solo si el SMS da evidencia de efectividad
- `false` si hay evidencia de que no funcionó
- `null` si no se puede afirmar

### 8.7 Regla crítica
Nunca asumir que una acción resolvió el incidente solo porque ocurrió antes del cierre.

---

## 9. Regla crítica sobre remediación real

Existen incidentes donde la bitácora no muestra una remediación técnica explícita.
En esos casos, el sistema debe distinguir entre:

- acción ejecutada
- resultado observado
- resolución o estabilización

Ejemplo:
- reportar a DBA
- monitorear
- derivar a otro equipo
- esperar que la carga baje
- confirmar estabilidad

Eso no implica automáticamente que hubo una acción correctiva efectiva.

---

## 10. Reglas de no inferencia

El extractor/agente NO debe inventar:

- causa raíz si no está respaldada
- solución técnica si no está explícita
- remediación efectiva si solo hubo coordinación o monitoreo
- impacto adicional no mencionado
- equipos no citados
- tickets no presentes
- componentes no sugeridos por evidencia razonable

---

## 11. Reglas de inferencia permitida

Se permite inferir con prudencia:

- clasificación de un hito como timeline entry
- clasificación de una línea como troubleshooting action
- tipo de acción (`action_type`)
- rol de la acción (`action_role`)
- tags operativos razonables
- componentes probables si el texto lo sugiere claramente

Toda inferencia debe:
- ser consistente con el SMS
- evitar contradicciones
- marcarse como inferencia si el sistema lleva trazabilidad de confianza

---

## 12. Preprocesamiento mínimo permitido

Antes de la extracción semántica, se permite:

- limpiar espacios
- normalizar saltos de línea
- detectar tickets
- detectar horas y fechas
- detectar IPs, dominios, URLs
- detectar bloques por encabezados comunes
- separar líneas cronológicas

Esto no debe reemplazar la interpretación semántica.

---

## 13. Seguridad y redacción

Si el SMS o sus derivados fueran a salir a fuentes externas, se debe redactar información sensible como:

- IPs
- dominios internos
- hostnames
- correos
- rutas internas
- secretos
- identificadores sensibles

La extracción interna puede conservar evidencia original en `raw_sms`, pero la salida a terceros debe protegerla.

---

## 14. Observaciones del proyecto ya aprobadas

### 14.1 Sobre status
- Si el SMS incluye “Se cierra SMS” o equivalente, el status sugerido es `closed`.
- Si indica estabilidad pero RCA pendiente, también se maneja como `closed` con `pending_rca = true`.

### 14.2 Sobre timeline
El modelo temporal debe representar la evolución de la bitácora en el tiempo.  
Por eso se renombró a:
- `IncidentTimelineEntryModel`

### 14.3 Sobre troubleshooting actions
`TroubleshootingActionModel` debe capturar acciones operativas reales y no copiar el timeline completo.

---

## 15. Ejemplos de interpretación

### Caso donde sí hay remediación explícita
- rollback autorizado
- rollback ejecutado
- validación posterior de acceso
- conformidad del usuario

Aquí sí puede existir:
- `action_role = remediation`
- `was_effective = true` para la acción correcta

### Caso donde no hay remediación explícita
- se reporta a DBA
- se monitorea
- la carga baja sola
- se confirma estabilidad
- RCA queda pendiente

Aquí no debe inferirse una solución técnica directa si no está demostrada.

---

## 16. Criterio de evolución

Este documento puede crecer con:
- nuevos formatos observados
- nuevos ejemplos reales
- nuevas reglas de clasificación
- excepciones operativas detectadas
- reglas específicas para agentes de extracción y validación