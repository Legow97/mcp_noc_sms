# External Research Policy

La tool `external_research` solo puede consultar fuentes externas si el sistema
lo permite por feature flag y si la policy estructurada lo autoriza.

Reglas conversacionales:
- Prioriza siempre histórico interno y contexto ya disponible.
- Usa research externo cuando el usuario lo pida explícitamente o cuando el
  histórico no alcance para responder una pregunta de documentación o guía oficial.
- Todo contexto enviado hacia afuera debe pasar por sanitización obligatoria.
- Distingue con claridad lo que proviene de histórico interno, conocimiento general
  del modelo y evidencia externa.
- Las fuentes en whitelist son preferidas.
- Las fuentes en blacklist están prohibidas.
- Las fuentes no listadas solo se usan con cautela si el manifest lo permite.
- Nunca trates evidencia externa como confirmación operativa del estado interno.
