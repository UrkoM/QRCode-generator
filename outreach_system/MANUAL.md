# Manual de Usuario — Sistema de Outreach Autónomo LinkedIn

## Índice

1. [Qué es este sistema](#1-qué-es-este-sistema)
2. [Requisitos previos](#2-requisitos-previos)
3. [Instalación](#3-instalación)
4. [Configuración inicial](#4-configuración-inicial)
5. [Modos de operación](#5-modos-de-operación)
6. [Primer uso paso a paso](#6-primer-uso-paso-a-paso)
7. [Comandos de referencia](#7-comandos-de-referencia)
8. [Cómo funciona el pipeline](#8-cómo-funciona-el-pipeline)
9. [Gestión del CRM (Airtable)](#9-gestión-del-crm-airtable)
10. [Modo Autónomo — gestión de personas](#10-modo-autónomo--gestión-de-personas)
11. [Ajuste de parámetros](#11-ajuste-de-parámetros)
12. [Resolución de problemas](#12-resolución-de-problemas)
13. [Límites y buenas prácticas](#13-límites-y-buenas-prácticas)
14. [Advertencias legales](#14-advertencias-legales)

---

## 1. Qué es este sistema

Un sistema de agentes de inteligencia artificial que gestiona todo el proceso de prospección B2B en LinkedIn de forma autónoma. Tú solo defines la estrategia y el perfil de cliente ideal; el sistema se encarga del resto.

**Lo que hace el sistema por ti:**

- Busca prospectos en LinkedIn que encajan con tu cliente ideal
- Califica y prioriza cada prospecto con un score de 0 a 100
- Redacta mensajes de conexión personalizados para cada persona
- Envía solicitudes de conexión con notas únicas
- Hace seguimiento automático con una secuencia de 4 mensajes
- Detecta respuestas y las clasifica (interesado, objeción, no interesado)
- Maneja objeciones y envía el link de Calendly cuando hay interés

**Lo que tú aportas:**

- Tu estrategia de posicionamiento (texto libre, un par de párrafos)
- La descripción de tu cliente ideal (cargo, sector, tamaño de empresa, etc.)
- Tus credenciales de LinkedIn y API keys

---

## 2. Requisitos previos

| Requisito | Obligatorio | Para qué |
|-----------|-------------|----------|
| Python 3.11+ | Sí | Ejecutar el sistema |
| Cuenta de Anthropic (Claude API) | Sí | Inteligencia de todos los agentes |
| Cuenta de Airtable | Sí | Base de datos / CRM visual |
| Cuenta de LinkedIn | Sí | Canal de outreach |
| Proxies residenciales | Solo Modo A | Proteger cuentas sintéticas |

---

## 3. Instalación

```bash
# 1. Entra en el directorio del sistema
cd outreach_system

# 2. Crea un entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Instala el navegador de Playwright
playwright install chromium
```

---

## 4. Configuración inicial

### 4.1 Crear el fichero `.env`

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

```env
# API de Claude (obténla en console.anthropic.com)
ANTHROPIC_API_KEY=sk-ant-...

# Airtable (ve a airtable.com/create/tokens)
AIRTABLE_API_KEY=pat...
AIRTABLE_BASE_ID=app...        # ID de tu base, en la URL de Airtable

# LinkedIn (tu cuenta real, solo para Modo B)
LINKEDIN_EMAIL=tu@email.com
LINKEDIN_PASSWORD=tu_password

# Calendly (link de tu página de reservas)
CALENDLY_LINK=https://calendly.com/tu-usuario/30min

# ID de campaña (ponle un nombre descriptivo)
CAMPAIGN_ID=campaña_saas_q1_2026
```

### 4.2 Crear las tablas en Airtable

Crea una base nueva en Airtable con tres tablas y estos campos:

**Tabla `Prospects`**

| Campo | Tipo |
|-------|------|
| name | Single line text |
| title | Single line text |
| company | Single line text |
| linkedin_url | URL |
| score | Number |
| status | Single select (ver estados abajo) |
| mode | Single select: autonomous, copilot |
| persona_id | Single line text |
| invite_sent_at | Date |
| connected_at | Date |
| last_msg_at | Date |
| next_action_at | Date |
| replied | Checkbox |
| meeting_booked | Checkbox |
| meeting_date | Date |
| notes | Long text |
| campaign_id | Single line text |

Opciones del campo `status`:
`NEW, QUALIFIED, INVITE_SENT, INVITE_EXPIRED, CONNECTED, MSG_1_SENT, MSG_2_SENT, MSG_3_SENT, BREAK_UP_SENT, REPLIED, INTERESTED, OBJECTION, NOT_INTERESTED, MEETING_SCHEDULED, DONE, ARCHIVED`

**Tabla `LinkedIn_Personas`** (solo necesaria para Modo A)

| Campo | Tipo |
|-------|------|
| persona_name | Single line text |
| persona_title | Single line text |
| persona_company | Single line text |
| account_email | Email |
| linkedin_url | URL |
| status | Single select: CREATED, WARMING, ACTIVE, RESTRICTED, BANNED |
| invites_this_week | Number |
| total_connections | Number |
| proxy_ip | Single line text |
| created_at | Date |

**Tabla `Messages_Log`**

| Campo | Tipo |
|-------|------|
| prospect_id | Single line text |
| prospect_name | Single line text |
| channel | Single line text |
| touchpoint | Number |
| message_body | Long text |
| sent_at | Date |
| replied | Checkbox |
| reply_content | Long text |
| approval_status | Single select: pending_approval, approved, rejected, auto_approved |
| submitted_at | Date |

### 4.3 Rellenar los ficheros de input

El sistema lee dos ficheros que tú escribes en texto libre:

**`input/positioning_strategy.md`** — tu propuesta de valor, diferenciación, tono que quieres transmitir, casos de éxito que puedas mencionar.

**`input/icp_description.txt`** — descripción detallada de tu cliente ideal: cargo, seniority, sector, tamaño de empresa, geografía, pain points principales, señales de compra, descalificadores.

Cuanto más detalle pongas en estos dos ficheros, mejor funcionará el sistema. El agente de estrategia los lee y genera todo el marco de campaña a partir de ellos.

---

## 5. Modos de operación

### Modo B — Co-piloto (recomendado para empezar)

Opera sobre **tu cuenta de LinkedIn real**. El sistema automatiza toda la actividad (búsquedas, invitaciones, mensajes) desde tu perfil, sin que tengas que entrar manualmente.

- Menor riesgo de restricción (cuenta con historial real)
- Límite recomendado: 30 invitaciones/día
- Requiere tus credenciales de LinkedIn en `.env`

### Modo A — Agente Autónomo

Crea y opera **cuentas de LinkedIn con identidades generadas por IA**. El sistema genera el perfil completo (nombre, cargo, foto sintética, historial laboral) y gestiona la cuenta de forma independiente.

- Opera sin necesidad de tu cuenta personal
- Escala a múltiples cuentas/personas en paralelo
- Requiere proxies residenciales (uno por cuenta)
- Límite conservador: 20 invitaciones/día por cuenta
- **Viola los ToS de LinkedIn** — ver sección de advertencias

---

## 6. Primer uso paso a paso

### Paso 1 — Rellena tu estrategia e ICP

Edita los ficheros de input con tu información real. Ejemplo mínimo:

`input/positioning_strategy.md`:
```
Ayudamos a directores de operaciones de empresas SaaS a reducir
el tiempo de incorporación de nuevos clientes de 30 días a 7,
mediante automatización del onboarding. Nos diferenciamos por
integrarnos con cualquier CRM en menos de 2 horas sin IT.
```

`input/icp_description.txt`:
```
Cargo: Director de Operaciones, VP Operations, Head of Customer Success
Seniority: Director o superior
Sector: SaaS B2B, plataformas digitales
Tamaño: 50-500 empleados
Geografía: España, México, Colombia
Pain points: onboarding lento, churn en los primeros 90 días
Descalificadores: menos de 20 empleados, sector industrial
```

### Paso 2 — Test en modo seco (sin enviar nada)

```bash
python orchestrator.py --mode copilot --dry-run
```

Esto ejecuta todo el pipeline (estrategia, búsqueda, calificación, generación de mensajes) pero **no envía ninguna comunicación**. Sirve para revisar qué prospectos encontraría y qué mensajes generaría antes de activar el envío real.

### Paso 3 — Primera ejecución real

```bash
python orchestrator.py --mode copilot
```

El sistema:
1. Lee tus ficheros de input y genera la estrategia de campaña
2. Busca prospectos en LinkedIn que encajan con tu ICP
3. Visita cada perfil, lo califica y le asigna un score
4. Genera mensajes personalizados
5. Envía las solicitudes de conexión (respetando el límite diario)
6. Registra todo en Airtable

### Paso 4 — Ejecuciones diarias

A partir del día siguiente, ejecuta el sistema una vez al día para:
- Procesar nuevas aceptaciones de conexión (envío inmediato de MSG_1)
- Enviar follow-ups programados
- Revisar el inbox y responder a prospectos interesados

```bash
python orchestrator.py --mode copilot --action followup
python orchestrator.py --mode copilot --action inbox
```

O todo de una vez:

```bash
python orchestrator.py --mode copilot
```

### Automatización diaria (opcional)

Para que corra solo, añade al cron (Linux/Mac):

```bash
crontab -e
# Añadir esta línea para ejecutar cada día a las 9:00
0 9 * * 1-5 cd /ruta/a/outreach_system && /ruta/a/venv/bin/python orchestrator.py --mode copilot >> logs/cron.log 2>&1
```

---

## 7. Comandos de referencia

```bash
# Pipeline completo (search + qualify + outreach + followup + inbox)
python orchestrator.py --mode copilot

# Solo buscar nuevos prospectos
python orchestrator.py --mode copilot --action search

# Solo calificar prospectos pendientes
python orchestrator.py --mode copilot --action qualify

# Solo enviar invitaciones a los ya calificados
python orchestrator.py --mode copilot --action outreach

# Solo procesar follow-ups programados
python orchestrator.py --mode copilot --action followup

# Solo revisar inbox y gestionar respuestas
python orchestrator.py --mode copilot --action inbox

# Modo seco (no envía nada, solo genera y registra)
python orchestrator.py --mode copilot --dry-run

# Limitar número de prospectos buscados por ejecución
python orchestrator.py --mode copilot --max-prospects 30

# Modo autónomo — crear nueva persona sintética
python orchestrator.py --mode autonomous --create-persona

# Modo autónomo — comprobar salud de todas las cuentas
python orchestrator.py --mode autonomous --health-check

# Modo autónomo — pipeline completo
python orchestrator.py --mode autonomous
```

---

## 8. Cómo funciona el pipeline

```
Tu estrategia.md + icp.txt
         │
         ▼
 [Strategy Agent]  ──►  JSON de campaña:
                         ICP detallado, keywords de búsqueda,
                         value propositions, tono, CTA
         │
         ▼
 [Search Agent]    ──►  Lista de perfiles de LinkedIn
  (Playwright)           que encajan con el ICP
         │
         ▼
 [Qualification    ──►  Score 0-100 por prospecto.
  Agent]                Descarta los que no encajan.
  (visita perfil,        Enriquece con datos del perfil.
   Claude evalúa)
         │
         ▼
 [Personalization  ──►  Nota de conexión única (≤300 chars)
  Agent]                 Secuencia de 4 DMs personalizada
  (Claude Sonnet)
         │
         ▼
 [Connection       ──►  Envía solicitud de conexión
  Agent]                 con nota personalizada.
  (Playwright)           Respeta límites diarios y delays.
         │
    (prospecto acepta)
         │
         ▼
 [Follow-up        ──►  Día 0: MSG_1 (bienvenida + valor)
  Agent]                 Día 3: MSG_2 (contenido / pregunta)
                         Día 7: MSG_3 (propuesta de reunión)
                         Día 14: MSG_4 (break-up elegante)
         │
    (prospecto responde)
         │
         ▼
 [Meeting Closer]  ──►  Clasifica la respuesta.
  Agent]                 INTERESADO → envía Calendly
  (Claude Sonnet)        OBJECIÓN → responde y reencuadra
                         NO INTERESADO → archiva
```

### Máquina de estados del prospecto

```
NEW → QUALIFIED → INVITE_SENT → CONNECTED
                      │              │
               INVITE_EXPIRED    MSG_1_SENT → MSG_2_SENT
                                              │
                                          MSG_3_SENT → BREAK_UP_SENT → ARCHIVED
                                              │
                                           REPLIED
                                              │
                              ┌───────────────┼──────────────────┐
                          INTERESTED      OBJECTION        NOT_INTERESTED
                              │               │                  │
                     MEETING_SCHEDULED   [respuesta IA]       ARCHIVED
                              │
                            DONE
```

---

## 9. Gestión del CRM (Airtable)

Airtable funciona como tu dashboard en tiempo real. Desde aquí puedes:

- **Ver el estado** de todos los prospectos en una vista Kanban (agrupa por `status`)
- **Filtrar** por campaña, score mínimo, fecha de próxima acción
- **Revisar mensajes** pendientes de aprobación (si tienes `APPROVAL_GATE_ENABLED=true`)
- **Aprobar o rechazar** mensajes: cambia el campo `approval_status` a `approved` o `rejected`
- **Ver el log** de todos los mensajes enviados en la tabla `Messages_Log`

### Vista recomendada en Airtable

1. Crea una vista **Kanban** en la tabla `Prospects` agrupada por `status`
2. Crea un **filtro** para ver solo prospectos de la campaña activa: `campaign_id = "tu_id"`
3. Crea una vista **Grid** en `Messages_Log` con filtro `replied = true` para ver todas las respuestas

### Approval Gate (revisión manual de mensajes)

Si quieres revisar cada mensaje antes de enviarlo activa esta opción en `.env`:

```env
APPROVAL_GATE_ENABLED=true
APPROVAL_TIMEOUT_HOURS=24
```

Con esto activado, antes de enviar cualquier mensaje el sistema lo escribe en `Messages_Log` con `approval_status = pending_approval`. Tienes 24 horas para:
- Cambiar a `approved` → el mensaje se envía
- Cambiar a `rejected` → el mensaje se descarta
- No hacer nada → se envía automáticamente al cumplirse el timeout

---

## 10. Modo Autónomo — gestión de personas

### Crear una nueva persona

```bash
python orchestrator.py --mode autonomous --create-persona
```

El sistema:
1. Genera una identidad completa con Claude (nombre, cargo, bio, historial laboral)
2. Descarga una foto de cara sintética
3. Asigna un proxy residencial dedicado
4. Crea la cuenta en LinkedIn con Playwright (se abre el navegador — puede necesitar resolver captcha manualmente la primera vez)
5. Rellena todo el perfil
6. Guarda las cookies de sesión y registra la persona en Airtable

### Período de calentamiento

Las cuentas nuevas pasan 2 semanas en estado `WARMING` antes de empezar a prospectar. Durante este tiempo el sistema conecta con 10-20 perfiles genéricos para que la cuenta tenga actividad real.

### Comprobar salud de cuentas

```bash
python orchestrator.py --mode autonomous --health-check
```

Verifica si cada cuenta está activa, restringida o baneada. Actualiza el estado en Airtable.

### Proxies — fichero `proxies.txt`

Crea el fichero `proxies.txt` en la raíz del proyecto, un proxy por línea:

```
usuario:contraseña@host:puerto
usuario:contraseña@host:puerto
```

Se asigna un proxy por cuenta LinkedIn. Sin proxies, todas las cuentas comparten la IP del servidor — mayor riesgo de detección.

Proveedores recomendados de proxies residenciales: Bright Data, Oxylabs, Smartproxy.

---

## 11. Ajuste de parámetros

Todos los parámetros se configuran en `.env`:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `MAX_INVITES_PER_DAY_AUTONOMOUS` | 20 | Invitaciones/día en Modo A |
| `MAX_INVITES_PER_DAY_COPILOT` | 30 | Invitaciones/día en Modo B |
| `MIN_DELAY_SECONDS` | 120 | Mínimo de espera entre acciones (2 min) |
| `MAX_DELAY_SECONDS` | 480 | Máximo de espera entre acciones (8 min) |
| `FOLLOWUP_1_DAYS` | 3 | Días hasta MSG_2 tras conectar |
| `FOLLOWUP_2_DAYS` | 7 | Días hasta MSG_3 |
| `FOLLOWUP_3_DAYS` | 14 | Días hasta break-up |
| `APPROVAL_GATE_ENABLED` | false | Revisión manual antes de enviar |
| `APPROVAL_TIMEOUT_HOURS` | 24 | Horas antes de auto-envío |
| `DRY_RUN` | false | Modo seco global |

---

## 12. Resolución de problemas

### "LinkedIn security challenge detected"

LinkedIn ha pedido verificación. Solución:
1. Abre manualmente el navegador (pon `headless=False` en `playwright_linkedin.py`)
2. Entra en linkedin.com con las credenciales de la cuenta afectada
3. Completa la verificación (email, teléfono, captcha)
4. Las cookies se guardarán automáticamente

### "No valid session found, logging in..."

La sesión ha expirado. El sistema intentará hacer login automáticamente. Si falla:

```bash
# Para Modo B, fuerza un login limpio
python -c "from agents.mode_b.session_manager import SessionManager; SessionManager().force_login()"
```

### "No active personas with capacity"

En Modo A, no hay personas sintéticas activas o han alcanzado el límite semanal. Soluciones:
- Crear una persona nueva: `--create-persona`
- Esperar al lunes (el sistema resetea los contadores semanales)
- Comprobar si hay cuentas baneadas: `--health-check`

### "Missing: input/positioning_strategy.md"

Los ficheros de input son obligatorios. Edítalos con tu información real antes de ejecutar.

### Airtable devuelve errores 422

Los campos del registro no coinciden con el schema de tu base. Revisa que los nombres de campo en Airtable coinciden exactamente con los descritos en la sección 4.2.

### Los mensajes generados son demasiado genéricos

El agente de personalización necesita más contexto. Asegúrate de que:
- `input/positioning_strategy.md` tiene detalles específicos (no texto de ejemplo)
- Los perfiles scrapeados tienen sección "About" y posts recientes (perfiles vacíos producen mensajes genéricos)

---

## 13. Límites y buenas prácticas

### Límites de LinkedIn (cuentas reales — Modo B)

| Acción | Límite seguro recomendado |
|--------|--------------------------|
| Invitaciones de conexión | 20-30 / día |
| Mensajes directos | 50 / día |
| Búsquedas de personas | 100 / día |
| Visitas de perfil | 80 / día |

Estos límites son conservadores respecto a lo que LinkedIn permite, para evitar cualquier restricción.

### Límites adicionales para Modo A

- Máx. 1 cuenta nueva por día por IP
- Período de calentamiento de 2 semanas antes de prospectar
- Usar proxies residenciales dedicados (no datacenter)
- Los delays entre acciones deben ser aleatorios (ya configurados)

### Buenas prácticas de mensajes

- El mensaje de conexión debe ser específico a la persona — no una plantilla obvia
- Los DMs deben aportar valor antes de pedir la reunión
- El break-up message siempre cierra la puerta con elegancia
- No mencionar el precio ni hacer pitch de ventas en los primeros mensajes

---

## 14. Advertencias legales

### LinkedIn Terms of Service

**Modo A (identidades sintéticas)** viola directamente el apartado §8.2 de los Términos de Servicio de LinkedIn, que prohíbe la creación de perfiles falsos y la automatización no autorizada. Consecuencias posibles:
- Restricción temporal o permanente de las cuentas sintéticas
- Restricción de tu IP o empresa
- En casos extremos (escala muy alta), acciones legales

**Modo B (cuenta real)** también viola los ToS en cuanto al uso de automatización, aunque el riesgo es significativamente menor.

### GDPR / Privacidad (Europa)

El tratamiento de datos personales de ciudadanos de la UE está regulado por el GDPR. Para outreach B2B:
- Los emails y datos de profesionales en sus perfiles corporativos tienen base legal de **interés legítimo** si el mensaje es relevante para su cargo
- Debes poder demostrar que tienes un interés legítimo documentado
- Los destinatarios pueden ejercer su derecho de supresión — respeta las solicitudes de unsubscribe / "no me contactes"

### Responsabilidad

Este sistema es una herramienta técnica. El usuario es responsable del uso que haga de ella, del cumplimiento de los ToS de las plataformas que use, y de la normativa de privacidad aplicable en su jurisdicción.
