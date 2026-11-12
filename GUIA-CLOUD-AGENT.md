# aidlc-factory en el agente en la nube de GitHub Copilot

Guía de instalación y uso, con el estado actual de las pruebas. Documento vivo: se ampliará a medida que avancen las pruebas.

> **Estado:** prueba de concepto. El flujo arrancó en la nube y avanzó hasta la etapa `requirements-questions`. Las etapas posteriores **no se han probado todavía**.

---

## 1. Objetivo

Comprobar si `aidlc-factory` (el harness AIDLC preparado para Copilot) se puede usar con el **agente en la nube de GitHub Copilot** ("Copilot in the cloud", antes "Copilot coding agent"), y detectar los problemas que tendríamos como empresa.

## 2. Requisitos

| Requisito | Detalle |
|---|---|
| Licencia de Copilot | Plan de pago (Pro, Pro+, Business o Enterprise). El plan Free no incluye el agente en la nube. |
| Repositorio en GitHub | El agente trabaja sobre un repo de GitHub. Hace falta permiso de escritura. |
| Quién lanza la tarea | La cuenta que lanza la tarea es la que consume los *premium requests*. Debe tener licencia de pago y acceso de escritura al repo. |
| VS Code | Versión reciente, con la extensión **GitHub Copilot Chat**. |
| Git | Para subir el harness al repo. |

> Si la licencia viene de una organización (Business/Enterprise), un administrador debe activar el agente en la nube y es probable que solo funcione en repos de esa organización. Esto hay que confirmarlo con la administración de GitHub de la empresa.

## 3. Instalación paso a paso

### 3.1 Crear el repositorio
1. En GitHub, crear un repositorio **privado** con la cuenta que tiene la licencia de pago (o en la organización).
2. Añadir como colaborador, con rol **Write**, a la persona que va a subir el harness (Settings → Collaborators). Esa persona debe aceptar la invitación.

### 3.2 Subir el harness
En la carpeta del harness:

```powershell
git init -b main
git remote add origin https://github.com/<propietario>/<repositorio>.git
git fetch origin
git add .
git commit -m "chore: add AIDLC harness"
git pull origin main --allow-unrelated-histories
git push -u origin main
```

Antes de `git add .`, comprobar con `git status` que **no se sube** nada local ni sensible: `.venv`, `.engram`, `.codegraph`, `.aidlc-env` y cualquier clave o token. Revisar `.gitignore`.

Si Git abre un editor para el mensaje del merge: en Vim, `Esc`, luego `:wq` y `Enter`.

Si el push da `403`: el usuario no tiene permiso de escritura en el repo, o Windows guarda credenciales de otra cuenta (Administrador de credenciales → borrar las entradas `git:https://github.com`).

### 3.3 Comprobar que el agente está activo
En el repo: **Settings → Copilot → Cloud**. Debe mostrar las opciones del agente (tamaño del sandbox, políticas, herramientas de validación). Solo los administradores del repo ven *Settings*.

Otras secciones del mismo menú:
- **MCP servers:** configuración de MCP para el agente.
- **Internet access:** firewall y dominios permitidos.
- **Memory:** memoria del agente.

## 4. Cómo usarlo

### Opción A: desde VS Code
1. Abrir la carpeta del harness en VS Code.
2. Iniciar sesión con la cuenta que tiene la licencia de Copilot de pago.
3. Abrir Copilot Chat (`Ctrl+Alt+I`).
4. En el selector del tipo de sesión, elegir **Cloud** (delegar al agente en la nube).
5. Si hay selector de agente, elegir `orchestrator`.
6. Escribir la petición y enviarla; aceptar la delegación.
7. El agente trabaja en una rama `copilot/...` y abre un **Pull Request**. Se sigue desde la vista *Agent Sessions* de VS Code o en GitHub → Pull requests → **View session**.

### Opción B: desde GitHub con un issue
1. Crear un issue con la petición.
2. Asignarlo a **Copilot** (campo Assignees).
3. Esperar el PR y revisar la sesión.

El issue deja la petición registrada y trazable.

> Los cambios del agente NO aparecen en `main` hasta que se apruebe y se haga merge del PR. Se ven en la rama del agente.

## 5. Qué hemos observado en la prueba

**Verificado:**
- El agente en la nube se lanzó desde VS Code y funcionó con el repo tal cual, **sin añadir `AGENTS.md`** y **sin configurar MCP**.
- El flujo AIDLC arrancó y avanzó hasta la etapa **`requirements-questions`**.

**Por verificar** (a completar en las próximas pruebas):
- Qué instrucciones y agentes leyó realmente (`.github/copilot-instructions.md`, `.github/agents/orchestrator.agent.md` y subagentes). Revisar el log de la sesión.
- Si las etapas posteriores a `requirements-questions` funcionan (user stories, planificación, generación de código, build/test, revisión, ship).
- Si los scripts de `aidlc-scripts/` se ejecutan correctamente en el entorno del agente (Python, dependencias de `requirements.txt`).
- Si los MCP del harness (`context7`, `engram`, `chrome-devtools`, `ai-architecture-cookbook`, `codegraph`) se usan o se ignoran. En la prueba no los configuramos.
- Cómo se comportan las aprobaciones humanas (`needs_human`) en un flujo asíncrono: ¿el agente se detiene en las preguntas, y cómo se responden? (Esto es lo siguiente a probar: la etapa `requirements-questions` es justo una parada para responder.)

## 6. Riesgos y puntos de atención para la empresa

1. **Los comandos `/factory-*` son archivos de prompt de IDE.** Hay que confirmar cómo se invoca el flujo en la nube y documentarlo.
2. **Aprobaciones humanas.** El orquestador usa gates y hace commit solo tras aprobación explícita. El agente en la nube es asíncrono y entrega un PR. Hay que definir dónde y cómo se responde a las preguntas.
3. **Entorno efímero.** Cada sesión empieza de cero. Lo que dependa de herramientas instaladas en local (binarios de MCP, `.venv`) necesita un paso de preparación en el repo (workflow `copilot-setup-steps.yml`). Pendiente de evaluar.
4. **Red.** El agente tiene el acceso a internet limitado (sección *Internet access*). Dominios externos pueden requerir allowlist.
5. **Datos y seguridad.** El código y el contexto se procesan en infraestructura de GitHub. Confirmar que cumple la política de la empresa antes de usar código real.
6. **Coste.** Cada sesión consume *premium requests* de la cuenta que la lanza y minutos de GitHub Actions del dueño del repo.
7. **Licencias y propiedad.** Evitar usar cuentas personales con código de la empresa. Lo recomendable es una organización de la empresa con Copilot Business o Enterprise y asientos asignados.
8. **Windows y Linux.** El harness tiene lanzadores para Windows (`.cmd`, `.ps1`) y shell (`.sh`). El agente corre en Linux, hay que verificar que los scripts funcionan allí.

## 7. Resolución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| No se ve Settings en el repo | No eres administrador | Pedir al propietario, o que te dé rol Admin |
| No aparece la opción Cloud en VS Code | VS Code desactualizado o sesión incorrecta | Actualizar y volver a iniciar sesión |
| `403` al hacer push | Sin permiso de escritura o credenciales de otra cuenta | Invitar como colaborador; limpiar el Administrador de credenciales |
| No veo los commits del agente en `main` | Están en la rama `copilot/...` del PR | `git fetch origin` y `git branch -r`; mirar el PR |
| Copilot no aparece en Assignees | Agente no disponible para esa cuenta o repo | Revisar licencia y políticas |

## 8. Siguientes pasos

- [ ] Responder las preguntas de `requirements-questions` y ver si el flujo continúa.
- [ ] Revisar el log de la sesión y rellenar la sección "Por verificar".
- [ ] Probar etapas posteriores hasta el final del flujo.
- [ ] Evaluar si hace falta `AGENTS.md`, `copilot-setup-steps.yml` y MCP configurados en el repo.
- [ ] Decidir la ubicación definitiva (organización de la empresa) y la licencia.
- [ ] Documentar la respuesta a la pregunta: *¿podemos usar aidlc-factory en el harness remoto?*
