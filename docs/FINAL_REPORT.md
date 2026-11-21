# Final report: Pillway care assistant (branch `feature/ai-care-assistant`)

Plain-English summary for the team. Built on top of `main` at `31246bb "QOL changes"`, in 7 commits.

## 1. What changed, file by file

**New: settings (no code needed to change them)**
- `pillway_config.toml`: the one commented settings file: per-job AI models, thresholds, demo mode, branding…
- `pillway_config.local.example.toml`, `.env.example`: where each developer's API key goes (real files are gitignored).
- `config/schema.py`, `validation.py`, `loader.py`: read and check the settings, plain-English errors, key lookup and the "key in a shared file" safety net.
- `.gitignore`: added; the committed `__pycache__/*.pyc` files were removed.

**Refactor (no visible change: every screen compared pixel by pixel)**
- `pillway/app.py`: shrank from 909 lines to the window, state and router only.
- `pillway/views.py` (1,356 lines) was split into `pillway/ui/{shell,components,patient,pharmacist}/…`.
- Moved: `medical_robot.py`, `medical_guidance.py` → `pillway/core/`; `chat_history.py`, `profile_store.py`, `profiles.py` → `pillway/storage/`; `speech_input.py` → `pillway/voice/`; `icons.py` → `pillway/ui/components/`; colours → `pillway/ui/theme.py` (with the Windows/Mac font fallback).

**New: safety and AI**
- `pillway/core/safety_rules.py`: layer 1 rules, which work offline.
- `pillway/core/flagging.py`: combines both layers; the AI can never clear a Tier 1.
- `data/buzzwords.json`: the full section 6.3 list plus the team's `EMERGENCY_SIGNS`.
- `pillway/core/deidentify.py`, `output_guard.py`: privacy before every AI call, and a check on every reply after it.
- `pillway/ai/client.py`: the only API code.
- `pillway/ai/brain.py`: real AI or demo mode, with automatic fallback.
- `pillway/ai/demo_mode.py`, `parsers.py`.
- `pillway/ai/prompts/*.md`: Sarah's instructions, built from the existing Sarah guidance, plus 3 worked examples covering both of Maria's scenes.

**New: patient flow**
- `pillway/core/conversation_flow.py`: steps 2–8, one question at a time, and the protein rule.
- `conversation_service.py`: handles each message in the order save → flag → reply.
- `reply_builder.py`, `patient_summary.py`, `answer_parsing.py`.
- `care_plan.py`: built from `data/care_plan_template.json`, which copies the PDF.
- `tasks.py`, `check_ins.py`.
- `data/questions.json`, `advice.json`, `check_in_messages.json`, `french_strings.json`, `seed_patients.json`.

**New: storage**
- `pillway/storage/patient_store.py`: one file per patient, with a file lock. This is the single source of truth for both windows.
- `json_store.py`, `file_lock.py`, `audit_log.py`, `edit_history.py`, `app_state.py`, `paths.py`.

**New or rewritten screens**
- **Patient:** `ui/login.py` (role switch), `ui/patient/consent.py`, `chat.py` and `chat_actions.py` (rewritten), `care_plan.py`, `call.py` + `call_audio.py` (iPhone-style), `tasks.py` (plans and permission), `medications.py` (the pharmacy list).
- **Shared:** `shell/header.py` (EN/FR toggle, "Talk to a pharmacist"), `components/dropdown.py` (bug fix), `components/scroll_area.py`, `live_sync.py`, `i18n.py`.
- **Pharmacist:** `dashboard.py`, `patient_detail.py`, `flags.py`, `highlights.py`, `log.py`, `care_plan_editor.py`, `medication_review.py`, `check_ins.py`, `bot_settings.py`.
- **Kept and reachable:** Pillway's consultation-form pages (`consult_pages*.py`), under "Consultation record".
- **Removed:** `patient_picker.py` and `workspace_shell.py`. The new dashboard and patient screen replace them; the method names the tests use still exist.

**Other**
- `Pillway.py`: checks the Python version and tkinter.
- `pillway/cli.py`: `--check-config`, `--show-ai-payload`, `--reset-demo`, `--role`, `--demo`, `--rehearse`.
- `pillway/rehearse.py`, `pillway/voice/tts.py` (read-aloud fallback chain).
- `README.md`, `docs/` (challenge PDFs, design inspiration, `french_review.md` with 207 strings, this report), `tools/generate_french_review.py`.
- `requirements.txt`: pinned `anthropic==2.12.0`, `python-dotenv`, `pyttsx3`, `sounddevice`, `vosk`.
- **Tests:** `test_config`, `test_safety`, `test_privacy_and_guardrails`, `test_patient_flow`, `test_ai_live_path`, plus the existing tests with updated import paths.

**UI bugs fixed**
1. **Manage profiles dropdown hidden.** Tk draws embedded widgets (like the profile list) above canvas drawings, so the dropdown was underneath them. It's now its own widget placed on top, and it closes on Esc or on a click elsewhere.
2. **Settings rows were dead clicks.** They now open a "Coming soon" page.
3. **Placeholder pages said "X will appear here".** They now show a clear "Coming soon" page.
4. **The sidebar's Medications, Orders and Tasks went to empty pages.** They now open the matching dashboard tab.
5. **Profile switching assumed "Doctor".** It's now "Pharmacist", and old saved files are migrated.
6. **Legacy chat returned the literal text "Prompt Claude".** In the new chat this is replaced by a real answer.
7. **Header said "Team AGILE".** It now shows the patient's or pharmacist's name.
8. **Long call captions overlapped the buttons.** They're now trimmed to fit.
9. **Tasks ran off the screen on small windows.** Row height now adapts.
10. **A message that was both an injection attempt and an urgent symptom got the wrong reply.** Urgent now always wins.
11. **When the AI found an urgent problem the word list missed, the reply didn't say a pharmacist would call.** It does now.

## 2. Files and links checklist (0.2b)

| Item | Result |
|---|---|
| Full brief, one-page summary, materials PDF | Opened, every page read |
| **Diabetes care plan PDF (9 pages)** | **Yes, read in full** (text and page images). The care plan follows its sections, order and wording. |
| Intake questionnaire (Google Sheet) | **Partly**: about 10 of ~14 rows loaded. **Please send a CSV export.** |
| diabetes.ca full guidelines + tools & resources + protein, hypoglycemia and foot-care pages | Opened |
| GitHub repo | Cloned and read (read-only: **I couldn't push**) |
| DASHBOARD_INSPIRATIONS.zip (images 3–14) | All 12 viewed. The layout was used for the consultation pages; the patient screen's sidebar was changed to black. |

**Challenge requirements covered:**
- ✅ Working first version on a made-up patient
- ✅ Protein question asked before any protein advice, with the 0.8–1.0 g/kg target
- ✅ Care plan in everyday language, in Pillway's format, EN + FR
- ✅ Foot sores, numbness or wounds reach a pharmacist at once
- ✅ Medication questions always go to the pharmacist
- ✅ Pharmacist review on/off switch, so Pillway can compare both modes
- ✅ Patients can tick off care plan actions (Tasks)
- ✅ Check-ins with one topic a week
- ✅ Consent, privacy and CASL handled
- ✅ More useful than "just Google it": answers use her own weight, readings, medicines and barriers

## 3. How to run
See README "Install and run". In short:
1. `pip install -r requirements.txt`
2. Copy `pillway_config.local.example.toml` → `pillway_config.local.toml` and paste your key.
3. Run `python Pillway.py`.

Use `--demo` for no AI, and `--reset-demo` before every run-through.

## 4. Where to change things
- **Models:** `[ai]` in `pillway_config.toml`, one line per job (`chat_model`, `flag_model`, `care_plan_model`, `summary_model`).
- **Thresholds:** `[safety]`.
- **API key:** each developer's own `pillway_config.local.toml`.

**Measured reply times**
- **Demo mode:** instant (under 0.1 s per reply, 13-message script).
- **Live AI:** **not measured.** My workspace can't reach the API. Run `python Pillway.py --rehearse` with your key; it prints the average and slowest reply time. Expect about 3–6 s with Opus. If that feels slow on stage, set `chat_model = "claude-sonnet-5-5"`.

**What the AI sees** (from `--show-ai-payload`): age 58, sex, weight, height, conditions, diagnosis month, last BP and A1C, smoker yes/no, allergies, medicine names and doses, the pharmacist's settings, and recent messages. The patient's own message `Hi, it's Maria Rossi (416-555-0198). I have a sore…` is sent as `Hi, it's Patient A [phone]. I have a sore…`.

## 5. Real vs demo vs Phase 2
- **Real:**
  - Layer 1 safety, flags, the audit log, the full check-in flow
  - Care plan (build, edit, undo, approve), tasks, two-window live sync, consent, EN/FR, read-aloud
  - The live AI path: tested with a fake API that simulates good replies, broken replies, outages and unsafe replies
- **Demo mode:** Sarah's built-in replies (realistic, rule-based) and the scripted call lines.
- **Not tested here:**
  - The real Anthropic API, real microphone and real speakers. My workspace has no internet API access and no sound.
  - **The real tkinter window.** My workspace has no tkinter. I checked every screen with a headless stand-in that draws screenshots, but please click through on Windows and Mac before the pitch.
- **Phase 2:**
  - Email/SMS alerts, voice typing in chat, the consultation-record pages (static)
  - Step and watch data, reordering or writing new questions per patient
  - A real login and a real scheduler for reminder notifications

## 6. Stage script
See README "The 5-minute stage script". Rehearse with `python Pillway.py --rehearse` (it passed 3/3 here in demo mode).

## 7. Pitch talking points
- **Two-layer safety:** hard rules decide "urgent" instantly and offline. The AI adds context, can raise a flag or filter a false alarm, but can never clear an urgent flag. Every decision is in an audit log.
- **The pharmacist is in charge:** the AI drafts, the pharmacist approves. Medical targets stay blank for the pharmacist. Medication questions always go to the pharmacist.
- **Consent and privacy:** consent screen first (AI and PHIPA). De-identified before the AI (PIPEDA spirit). Data stays on the device. Reminders are opt-in (CASL). Sarah never claims to be a pharmacist (college standards) and never diagnoses or advises on medication (Health Canada software rules).
- **Pillway's own care plan format**, English then French, with a French review list.
- **Time saved (estimate):** 100 plans × 6 follow-ups × 10–15 min = **100–150 pharmacist hours a month**.

## 8. Likely judge questions
- **Where does the data go?** It stays on the device. The AI sees only de-identified facts, and we can show `--show-ai-payload` live.
- **What if the AI is wrong?** Urgent words are caught by rules, not the AI. The AI can't downgrade them. Every AI line is labelled, guarded and approved by a pharmacist. Pharmacists mark each flag as right or wrong.
- **Why still a pharmacist?** Clinical judgment and medication stay with the pharmacy. We remove the routine calls, not the pharmacist.
- **What does it cost?** About US$0.50 per full demo conversation with Opus (estimate from `--check-config`). Cheaper models can be set per job.

## 9. Open questions for Pillway
- What counts as urgent beyond foot problems?
- What are the exact blood sugar and blood pressure thresholds? (Placeholders now: below 3.9, at or above 14 / 20 mmol/L, 180/110.)
- How should the pharmacist be alerted?
- Should we focus on type 2 or gestational diabetes?
- What are your brand colours?
- Is "Time in range **below** 70%" in the template a typo?
- Is "Target BMI 18.9–24.9" a typo for 18.5?
- The template mentions "Lumino Health / LHP / LifestyleRx": what pharmacy name and LibreView code should patients see?
- Can you send the full intake questionnaire as a CSV?
