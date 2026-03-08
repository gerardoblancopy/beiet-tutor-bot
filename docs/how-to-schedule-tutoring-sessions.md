# How to Schedule Tutoring Sessions via Google Calendar

This guide walks you through configuring the Google Calendar integration and using the `/agenda` commands to check professor availability and book tutoring sessions with automatic Google Meet links.

## Prerequisites

- The bot is installed and its dependencies are in place. See [How to Set Up and Deploy BEIET](how-to-deploy.md) if you have not done this yet.
- Your `.env` file contains a valid `DISCORD_TOKEN` and `GEMINI_API_KEY`.
- You have access to a Discord server where the bot is a member.
- A registered student profile (via `/registro`). The bot will reject booking attempts from unregistered users.

---

## Step 1: Configure Google Calendar Credentials

The calendar feature requires a **Google Cloud Service Account** with access to the professor's calendar.

1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a project (or use an existing one).
2. Enable the **Google Calendar API** for the project.
3. Create a **Service Account** under *IAM & Admin > Service Accounts*.
4. Generate a JSON key file for the service account and download it.
5. Share the professor's Google Calendar with the service account email address (found in the JSON file under `client_email`). Grant **Make changes to events** permission.
6. Place the JSON key file in the project directory (e.g., `credentials/calendar_sa.json`).
7. Add the following to your `.env` file:

   ```dotenv
   GOOGLE_CALENDAR_CREDENTIALS=credentials/calendar_sa.json
   PROFESSOR_CALENDAR_ID=professor@example.com
   ```

   Replace `professor@example.com` with the actual Google Calendar ID (usually the professor's Gmail address, or a custom calendar ID from Calendar Settings).

> **Mock mode:** If these variables are left empty, the bot runs in mock mode. The `/agenda disponibilidad` command shows a simulated message, and `/agenda cita` creates a mock booking without touching Google Calendar. This is useful for local development and testing.

---

## Step 2: Start the Bot

From the root of the repository, activate your virtual environment and start the bot:

```bash
source venv/bin/activate
python -m bot.main
```

Wait for the log line confirming a successful connection:

```
INFO:beiet.main:✅ BEIET está listo como BEIET#xxxx (ID: ...)
```

If Google Calendar credentials are configured correctly, you will also see:

```
INFO:beiet.calendar:Google Calendar API service initialized successfully.
```

If credentials are missing or invalid, a warning is logged instead and the bot falls back to mock mode:

```
WARNING:beiet.calendar:Google Calendar credentials not found at '...'. Calendar features will run in mock mode.
```

---

## Step 3: Check Professor Availability

In any Discord channel where the bot is present, run:

```
/agenda disponibilidad
```

The bot queries the professor's Google Calendar for free/busy data over the next 7 days and computes available 30-minute blocks within business hours (Monday to Friday, 09:00 - 18:00, America/Santiago timezone).

The response is a Discord embed grouping available slots by date:

```
📅 Disponibilidad del Profesor BEIET

Monday 09/03/2026
`09:00` - `09:30`, `09:30` - `10:00`, `10:00` - `10:30`, ...

Tuesday 10/03/2026
`09:00` - `09:30`, `09:30` - `10:00`, ...

Bloques de 30 min · Usa /agenda cita para reservar
```

**What the results mean:**
- Only weekdays (Mon-Fri) are shown. Weekends are excluded.
- Slots already in the past (earlier today) are excluded.
- Time blocks where the professor already has events are excluded.
- If no slots are available, the embed displays: *"No hay bloques disponibles en los proximos 7 dias."*
- In mock mode, the embed displays a simulated availability message.

---

## Step 4: Book a Tutoring Session

Choose a free slot from the availability list and run:

```
/agenda cita tema: Método Simplex dia: 10 mes: 3 hora: 15:00
```

| Parameter | Description | Example |
|---|---|---|
| `tema` | Topic to review during the session | `Método Simplex` |
| `dia` | Day of the month (number) | `10` |
| `mes` | Month (number 1-12) | `3` |
| `hora` | Start time in 24-hour format (HH:MM) | `15:00` |

The bot performs the following checks before booking:

1. **Registration** — Verifies you have a student profile. If not, you are prompted to use `/registro` first.
2. **Date parsing** — Validates the date and time. If the date is in the past and the month is earlier than the current month, it rolls forward to next year.
3. **Conflict detection** — Checks the slot is within business hours (09:00-18:00, Mon-Fri) and not already occupied on the professor's calendar.
4. **Event creation** — Creates a Google Calendar event with an automatic Google Meet link.
5. **Database persistence** — Saves the meeting record to the `scheduled_meetings` table.

On success, the bot replies with a confirmation embed:

```
✅ Reunión Confirmada

Cita agendada exitosamente.
Fecha: 2026-03-10 15:00
Tema: Método Simplex
Duración: 30 minutos

🔗 Enlace de Google Meet
Estudiante: Juan Pérez
```

**Common rejection messages:**

| Message | Cause |
|---|---|
| *"Debes usar `/registro` antes de agendar una cita."* | No student profile found |
| *"La fecha solicitada esta en el pasado."* | The requested date/time has already passed |
| *"El horario solicitado no esta disponible..."* | Outside business hours, weekend, or calendar conflict |
| *"Hubo un error al agendar la reunion..."* | Google API credentials or permissions issue |

---

## Step 5: Verify the Meeting in the Database (Optional)

Open the SQLite database with any SQLite client:

```bash
sqlite3 data/beiet.db
```

Query the `scheduled_meetings` table:

```sql
SELECT
    s.name,
    sm.subject,
    sm.topic,
    sm.scheduled_at,
    sm.duration_minutes,
    sm.status,
    sm.google_event_id,
    sm.meet_link
FROM scheduled_meetings sm
JOIN students s ON s.id = sm.student_id
ORDER BY sm.created_at DESC
LIMIT 5;
```

A successful booking produces a row like:

| name | subject | topic | scheduled_at | duration_minutes | status | google_event_id | meet_link |
|---|---|---|---|---|---|---|---|
| Juan Perez | optimizacion | Metodo Simplex | 2026-03-10 15:00:00 | 30 | confirmed | abc123... | https://meet.google.com/... |

In mock mode, `google_event_id` is `mock_event_id` and `meet_link` is `NULL`.

---

## Troubleshooting

| Symptom | Likely Cause | Action |
|---|---|---|
| `/agenda disponibilidad` shows mock mode | Missing env vars | Verify `GOOGLE_CALENDAR_CREDENTIALS` and `PROFESSOR_CALENDAR_ID` in `.env` |
| "Calendar credentials not found" in logs | JSON file path is wrong | Check the path in `GOOGLE_CALENDAR_CREDENTIALS` is relative to the project root or absolute |
| No free slots despite empty calendar | Service account lacks access | Ensure the calendar is shared with the service account's `client_email` |
| Google Meet link is missing | Workspace restrictions | Google Meet auto-creation requires a Google Workspace account; personal Gmail accounts may not support `hangoutsMeet` conference creation |
| DB row not created after booking | Session error | Check bot logs for `Could not persist scheduled meeting` |
