# How to Verify the Quiz → RA Progress Loop

This guide walks you through verifying that the pedagogical feedback loop is working correctly: when a student answers a quiz question, their progress on the corresponding **Resultado de Aprendizaje (RA)** must be updated in the database.

## Prerequisites

- The bot is installed and its dependencies are in place. See [How to Set Up and Deploy BEIET](how-to-deploy.md) if you have not done this yet.
- Your `.env` file contains a valid `DISCORD_TOKEN` and `GEMINI_API_KEY`.
- You have access to a Discord server where the bot is a member.

---

## Step 1: Start the Bot

From the root of the repository, activate your virtual environment and start the bot:

```bash
source venv/bin/activate
python -m bot.main
```

Wait for the log line confirming a successful connection:

```
INFO:beiet.main:✅ BEIET está listo como BEIET#xxxx (ID: ...)
```

---

## Step 2: Register a Test Student

In any Discord channel where the bot is present, run the registration command as the student you want to test with:

```
/registro nombre: Test Student rut: 12345678-9 asignatura: optimizacion
```

You only need to do this once per Discord account.

---

## Step 3: Trigger an Interactive Quiz

Use the `/quiz simulacro` command with any topic from the course:

```
/quiz simulacro tema: programación lineal
```

The bot will reply with an embed containing a multiple-choice question and four clickable buttons labeled **A)**, **B)**, **C)**, and **D)**.

---

## Step 4: Answer the Question

Click any of the four answer buttons. Within a few seconds, you should see two changes to the message:

1. **Immediate response** — The buttons are disabled and the embed updates to show whether your answer was correct or incorrect, along with the tutor's pedagogical feedback.
2. **Footer update** — Once the database write completes (typically under one second), the embed footer updates to confirm the RA was recorded:

   ```
   Progreso actualizado · RA1 ✅
   ```

   If your answer was incorrect, the footer will show:

   ```
   Progreso actualizado · RA1 ❌
   ```

   > **Note:** If Gemini did not assign a valid RA code to the generated question (e.g., it returned an unrecognised code), the footer will not appear. A warning is logged server-side: `LLM returned unknown lo_code '...' for subject '...'`.

---

## Step 5: Verify Progress via Discord

Check that the student's RA record was created or updated by running the progress command:

```
/progreso
```

You should see a progress bar for the RA that was just tested. For a correct answer, the score bar will be non-zero. For a first-time incorrect answer, the score will be `0%` but the attempt counter will be `1`.

---

## Step 6: Verify Progress via SQLite (Optional)

For a direct database inspection, open the SQLite database with any SQLite client:

```bash
sqlite3 data/beiet.db
```

Query the `lo_progress` table for your test student:

```sql
SELECT
    s.name,
    lp.subject,
    lp.lo_code,
    ROUND(lp.score * 100, 1) AS score_pct,
    lp.attempts,
    lp.correct_count,
    lp.last_assessed
FROM lo_progress lp
JOIN students s ON s.id = lp.student_id
WHERE s.name = 'Test Student'
ORDER BY lp.lo_code;
```

A successful loop produces a row like:

| name | subject | lo_code | score_pct | attempts | correct_count | last_assessed |
|---|---|---|---|---|---|---|
| Test Student | optimizacion | RA1 | 100.0 | 1 | 1 | 2026-03-07 … |

You can also inspect the `quiz_results` table to confirm the raw attempt was saved:

```sql
SELECT subject, lo_codes, score, total_questions, correct_answers, created_at
FROM quiz_results
ORDER BY created_at DESC
LIMIT 5;
```

---

## Troubleshooting

| Symptom | Likely Cause | Action |
|---|---|---|
| Footer never appears | DB write failed | Check bot logs for `Could not persist quiz result` |
| Footer shows but `/progreso` is empty | RA code was invalid | Check logs for `LLM returned unknown lo_code` |
| `score_pct` stays at 0 after correct answer | Score calculation bug | Verify `update_lo_progress` in `bot/core/student_tracker.py` |
| `"This interaction failed"` in Discord | Bot timed out before responding | Confirm `interaction.response.edit_message` is called before DB writes in `bot/cogs/quiz.py` |
