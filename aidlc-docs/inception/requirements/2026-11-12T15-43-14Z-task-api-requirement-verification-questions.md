# Verificación de requisitos — API de tareas

Run ID: `2026-11-12T15-43-14Z-task-api`

Completa cada `[Answer]:` con las letras elegidas. Si eliges `X`, describe tu respuesta después de la etiqueta. En preguntas que permiten varias opciones, se indica expresamente.

## Exploración de enfoques

Se evaluaron tres direcciones sin elegir una por el usuario:

1. **CRUD local mínimo y volátil** — viable con poca complejidad, aunque los datos desaparecerían al reiniciar.
2. **API persistente para una persona o equipo** — mayor utilidad diaria, con decisiones adicionales de almacenamiento y límites de acceso.
3. **Servicio colaborativo multiusuario** — permite separar tareas por usuario/equipo, pero exige resolver autenticación y aislamiento de datos.

La pregunta Q1 permite escoger o proponer otra dirección. Todavía no se recomienda una como definitiva.

## Preguntas

<!-- axis: Purpose, Needs -->
## Question
**Q1.** ¿Qué dirección describe mejor la API de tareas que necesitas?

A) CRUD local para una sola persona; los datos pueden ser temporales
B) API persistente para una persona o un equipo
C) Servicio multiusuario con tareas separadas por usuario o equipo
D) Otra dirección
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Purpose -->
## Question
**Q2.** ¿Qué cambio reciente hace que valga la pena construir esto ahora?

A) Usuarios ya solicitan una forma de gestionar tareas
B) Una herramienta actual dejará de estar disponible o cambiará de costo
C) Es un mandato o iniciativa concreta
D) Es principalmente un ejercicio personal o de aprendizaje
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Purpose -->
## Question
**Q3.** ¿Por qué construir una API propia en vez de reutilizar o integrar una solución existente?

A) Hace falta un modelo o flujo personalizado
B) Las soluciones disponibles no encajan con el sistema o los datos existentes
C) El objetivo principal es aprender o experimentar
D) No se han evaluado alternativas todavía
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Purpose, Limits -->
## Question
**Q4.** ¿Por qué este alcance y no uno más pequeño o más amplio?

A) Es el mínimo que aporta valor
B) Debe cubrir varias necesidades desde el primer lanzamiento
C) El alcance todavía es exploratorio y se quiere aprender antes de decidir
D) Está definido por un documento o compromiso ya aprobado
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Needs -->
## Question
**Q5.** ¿Qué operaciones son imprescindibles en la primera versión? Puedes elegir varias letras.

A) Crear tareas
B) Consultar una tarea y listar tareas
C) Editar tareas
D) Completar o reabrir tareas
E) Eliminar tareas
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Needs -->
## Question
**Q6.** ¿Qué datos debe admitir cada tarea? Puedes elegir varias letras.

A) Título y descripción
B) Estado y prioridad
C) Fecha límite
D) Responsable o equipo
E) Etiquetas o proyecto
F) Subtareas, comentarios o historial
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Needs -->
## Question
**Q7.** ¿Qué capacidades de consulta se necesitan además de crear y editar tareas? Puedes elegir varias letras.

A) Filtrar por estado, responsable, fecha o prioridad
B) Buscar texto
C) Ordenar resultados
D) Paginación
E) Operaciones en lote
F) Ninguna adicional
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Needs -->
## Question
**Q8.** ¿Qué estilo de interfaz debe ofrecer la API?

A) REST sobre HTTP
B) GraphQL
C) Interfaz Python interna, sin API HTTP
D) Aún no está decidido
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Expectations -->
## Question
**Q9.** ¿Qué carga debe soportar al inicio y qué tiempo de respuesta sería aceptable?

A) Uso local o de desarrollo, sin objetivo de rendimiento
B) Hasta 100 usuarios o 10 solicitudes por segundo; p95 menor de 500 ms
C) Hasta 10.000 usuarios o 100 solicitudes por segundo; p95 menor de 500 ms
D) Necesito definir otra combinación de carga y latencia
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Expectations -->
## Question
**Q10.** ¿Qué expectativas de compatibilidad y errores debe cumplir el contrato de la API?

A) Contrato sencillo; los cambios pueden ser incompatibles durante el desarrollo
B) Versionado explícito y formato de error estable
C) Documentación OpenAPI y errores estables, pero sin política formal de versiones
D) Debe integrarse con un contrato existente
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Limits -->
## Question
**Q11.** ¿Qué funciones cercanas deben quedar fuera de esta versión? Puedes elegir varias letras.

A) Inicio de sesión y gestión de cuentas
B) Notificaciones o recordatorios
C) Archivos adjuntos
D) Tareas recurrentes o seguimiento de tiempo
E) Ninguna de las anteriores
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Limits -->
## Question
**Q12.** ¿Qué límite aplica a la gestión de tareas?

A) Solo tareas personales; sin proyectos ni equipos
B) Tareas de un equipo; sin jerarquías ni subtareas
C) Proyectos, subtareas y asignaciones entre miembros
D) No debe existir ninguna restricción de este tipo
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Context -->
## Question
**Q13.** Python está indicado. ¿Qué framework o estilo prefieres?

A) FastAPI
B) Flask
C) Django REST Framework
D) Biblioteca estándar, sin framework web
E) No tengo preferencia; que se recomiende durante Arquitectura
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Context -->
## Question
**Q14.** ¿Dónde se ejecutará la API y qué persistencia se espera?

A) Localmente para desarrollo; no hace falta conservar datos
B) Localmente o en un servidor, con persistencia en archivo
C) Servidor o contenedor, con base de datos persistente
D) Debe integrarse con una plataforma o almacén de datos existente
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Risks -->
## Question
**Q15.** ¿Qué tolerancia hay a perder o duplicar cambios de tareas?

A) Es un prototipo; se puede perder información
B) Se permite perder cambios recientes, pero no tareas ya guardadas
C) No se deben perder ni duplicar tareas confirmadas
D) Se necesita una política específica de copias de seguridad y recuperación
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Risks -->
## Question
**Q16.** ¿Qué amenazas o controles de acceso son relevantes?

A) Solo acceso local de confianza
B) Usuarios autenticados deben acceder únicamente a sus propias tareas
C) Los miembros de un equipo comparten tareas con roles diferentes
D) Deben mitigarse además abuso automatizado y solicitudes excesivas
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Acceptance -->
## Question
**Q17.** ¿Qué recorrido demostraría que la API cumple su objetivo?

A) Crear una tarea, consultarla, actualizarla y completar su estado
B) Lo anterior, además de conservarla tras reiniciar el servicio
C) Lo anterior, además de aislar correctamente tareas entre usuarios o equipos
D) Debe demostrarse otro recorrido principal
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Acceptance -->
## Question
**Q18.** ¿Qué evidencia de calidad debe estar presente para considerar terminado el trabajo?

A) Pruebas automatizadas de las operaciones principales
B) Pruebas unitarias y de integración de la API
C) Lo anterior, más documentación OpenAPI y una verificación reproducible
D) Debe cumplirse una herramienta o umbral de cobertura existente
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Unknowns -->
## Question
**Q19.** ¿Qué decisiones siguen sin resolverse y deberían quedar registradas para más adelante? Puedes elegir varias letras.

A) Modelo de autenticación
B) Almacenamiento y despliegue
C) Escala y objetivos de disponibilidad
D) Funciones avanzadas como notificaciones o tareas recurrentes
E) Ninguna; las decisiones principales están tomadas
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Needs, Limits, Expectations, Context, Risks -->
## Question
**Q20.** La solicitud implica estas suposiciones. Marca las que sean INCORRECTAS; puedes elegir varias letras.

A) La API atenderá a una sola persona o equipo
B) Los datos deben persistir después de reiniciar el servicio
C) No se necesita autenticación ni separación de datos
D) REST sobre HTTP es aceptable
E) No hacen falta integraciones externas
F) El servicio se ejecutará en un solo entorno
G) Un conjunto básico de tareas es suficiente para la primera versión
H) No se necesita versionado ni compatibilidad hacia atrás del contrato
I) Las opciones anteriores son correctas
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Risks -->
## Question: Security Extensions
**Q21.** Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
X) Other (please describe after [Answer]: tag below)

[Answer]:

<!-- axis: Expectations, Acceptance -->
## Question: Property-Based Testing Extension
**Q22.** Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)
B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)
C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)
X) Other (please describe after [Answer]: tag below)

[Answer]:
