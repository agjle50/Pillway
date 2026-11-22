# Pillway care assistant (Brampton AI Innovator, Challenge 5)

Pillway is a Canadian online pharmacy. This app gives patients with **type 2 diabetes and high
blood pressure** a friendly assistant, **Sarah**, who checks in, asks one question at a time and
drafts a personal care plan in Pillway's own format. **Anything urgent (like a sore on the foot)
reaches a pharmacist at once**, and the pharmacist stays in charge: they approve the plan, resolve
flags and decide. All patients are made up.

## Contents
- [Part 1: Using the app](#part-1-using-the-app)
  - [Install and run (Windows and Mac)](#install-and-run)
  - [Add your API key](#add-your-api-key)
  - [Demo mode and Reset demo](#demo-mode-and-reset-demo)
  - [Tour of every screen](#tour-of-every-screen)
  - [The 5-minute stage script](#the-5-minute-stage-script)
  - [Common settings](#common-settings)
  - [Troubleshooting](#troubleshooting)
- [Part 2: Developer guide](#part-2-developer-guide)
  - [Folder map](#folder-map) · [How it fits together](#how-it-fits-together) · [How do I…?](#how-do-i)
  - [Rules of the codebase](#rules-of-the-codebase) · [Tests](#tests) · [Git for beginners](#git-for-beginners)
  - [Glossary](#glossary) · [Where does data go?](#where-does-data-go) · [Design decisions](#design-decisions)

---

# Part 1: Using the app

## Install and run

You need **Python 3.11 or newer** (we use 3.14). The app checks this when it starts.

**Windows**
1. Install Python from <https://www.python.org/downloads/>. On the first installer screen, tick
   **"Add python.exe to PATH"**. Keep **"tcl/tk and IDLE"** ticked (that's the window toolkit).
2. Download the code: on GitHub click **Code → Download ZIP** and unzip it, or run `git clone https://github.com/agjle50/Pillway`.
3. Open **PowerShell** in the folder (Shift + right-click inside the folder → "Open PowerShell window here").
4. Run: `python -m pip install -r requirements.txt`
5. Run: `python Pillway.py`

**Mac**
1. Install Python from <https://www.python.org/downloads/> (the python.org installer includes the window toolkit).
2. Download the code (same as Windows, step 2).
3. Open **Terminal**, type `cd ` (with a space), drag the folder into the window, press Enter.
4. Run: `python3 -m pip install -r requirements.txt`
5. Run: `python3 Pillway.py`

**What you should see:** a sign-in screen with two big buttons, **"I'm a patient"** and
**"I'm a pharmacist"**. At the bottom left it says whether you're in **Demo mode** or **Live AI**.

Useful options (add them after `python Pillway.py`):

| Option | What it does |
|---|---|
| `--role patient` / `--role pharmacist` | Opens straight into one side. Run both in **two terminals** to show them side by side. |
| `--demo` | Forces demo mode for this run (no AI, no internet). |
| `--reset-demo` | Puts Maria back to a fresh, newly enrolled state. |
| `--rehearse` | Runs the stage script in the terminal and prints how long each reply took. |
| `--check-config` | Shows your settings and warns about anything unsafe. |
| `--show-ai-payload` | Shows **exactly** what the AI company would receive (for the judges' privacy question). |
| `--debug` | Prints **admin debug lines** in the terminal: when the microphone turns on/off and why, what was heard (used or ignored), Sarah's voice starting/stopping, AI reply times, the questionnaire. On by default (`debug_logs` under `[dev]` in `pillway_config.toml`). |

## Add your API key

Sarah's brain is **Google Gemini**. You need a free Gemini API key from <https://aistudio.google.com/apikey>
(it starts with `AIza`). The free tier has limits; beyond them Google bills usage.

**Easiest:** start the app (`python Pillway.py`, without `--demo`), go to **Settings → AI connection**,
paste the key and press **Save and connect**. It tests the connection for you.

**Or by hand:**
1. Copy `pillway_config.local.example.toml` and name the copy `pillway_config.local.toml`.
2. Open it and paste your key between the quotes: `api_key = "AIza..."`
3. Run `python Pillway.py --check-config` to confirm.

`pillway_config.local.toml` is in `.gitignore`, so the key never goes to GitHub. (You can also set
the environment variable `GEMINI_API_KEY`, or copy `.env.example` to `.env`.)
**Never** start the app with `--demo` if you want the real AI: that forces scripted replies.

## Demo mode and Reset demo

- **Demo mode** = Sarah uses built-in, realistic replies. No key, no internet, instant. Use it for
  rehearsals and as the safe choice on stage. Turn it on with `demo_mode = true` in the config, or `--demo`.
- If there is **no key** or the **internet drops**, the app switches to demo mode by itself and
  shows a small "Offline mode" note under that reply. It never crashes.
- **Reset demo** puts Maria back to the start: pharmacist profile menu → **Reset demo**, or
  pharmacist **Settings → Reset demo**, or `python Pillway.py --reset-demo`. Do this before every run-through.

## Tour of every screen

**Patient side (sign in as "I'm a patient": Maria Rossi)**

| Screen | What it's for | What to click |
|---|---|---|
| Header | Always shows **EN/FR**, **Talk to a pharmacist**, notifications, and an animated account menu with profile progress | Progress reflects the full profile sheet; **Manage profiles** opens the categorized account list |
| Manage profiles | Separate patient and pharmacist profile categories, each with a **Switch profile** button and an options menu | Choose **Edit profile** or **Delete profile** from the menu; add patient profiles or delete saved data |
| Edit profile | Personal, health-card, insurance, insurance-photo, and delivery-address pages | Swipe horizontally, use the page dots or section selector, then **Save changes** |
| Health questionnaire | Shown first for a **brand-new account (no chats yet)**, and kept in **Tasks** until done. Pillway's intake sheet: weight/height (optional), blood pressure, tobacco. Says up front that Sarah only keeps key medical details and shares them only with the pharmacist / care team. Sarah then builds a **health profile**: what's known, what was kept private, and "areas to explore" (guesses she checks by *asking*, never states as fact) | Fill in and **Save and continue**, or **Do this later**. Edit any time from **Tasks → Edit answers** |
| Check up | Choose how to check in | **Call** or **Chat** |
| Consent | Shown once before the first chat or call (includes the privacy note) | **I agree** |
| Chat | Sarah: summary → "any changes?" → one question at a time → wrap-up → care plan | Returning patients can ask for a recap, continue, or raise a new concern; Sarah won't expect them to remember the last chat. Type or tap quick replies. |
| Call | iPhone-style voice check-in: name, timer, green voice ring, mute, end | **Hold** the green button and talk. With no microphone (or in demo mode) tap it to "say" the next scripted line. |
| Medications | Medicines on file (entered by the pharmacist) + prescriptions the patient adds | **Add prescription** |
| Orders | Made-up orders | – |
| Tasks | Alarm-style daily tasks made from the care plan (never medication) | **Allow reminders**, then flip any toggle |
| Care plan | Pillway's format, English then French, "Draft, waiting for your pharmacist's approval" | **Save as text** |
| Settings, sidebar items | Everything is clickable; pages without content say "Coming soon" | – |

**Pharmacist side (sign in as "I'm a pharmacist")**

| Screen | What it's for | What to click |
|---|---|---|
| Dashboard | Who needs me? Summary tiles (urgent flags, plans waiting, requests, estimated hours saved) | Filters **All · ACTIVE · WATCHING**, **Sort**, **Compact view**, **+ Add patient** |
| Patient tile | Rounded square with initials and name. **Red badge (top-left)** = open flags. **Green dot + LIVE** = chatting now. New flags move the patient to the front, briefly highlighted. | Click a tile |
| Patient screen (black sidebar) | Everything about one patient, at most 2 clicks away | Sidebar sections, or **Ctrl+1…8**. **Esc** goes back. |
| Flagged messages | Like Google Docs comments: exact message, URGENT/WATCH, chat or call, matched words, AI reason, the patient's extra details. 3-line recap on top. | **✓ Resolve**, **Add note**, **Right flag / Wrong flag**, **Show context**, **Reopen** |
| Possible issues | Every "you may have…, because…" statement Sarah made | – |
| Log | Every chat and call, newest first, labelled **CHAT** / **CALL** (calls show duration); flagged lines in red/amber; updates live | – |
| Care plan | AI draft in Pillway's format; yellow = target for you to set | **Set** a target, **Edit EN/FR**, **Include** optional lines, **Undo**, **History**, **Approve**, **Request changes**, and the **Pharmacist review required** ON/OFF switch |
| Medication review | The patient's medicines (used for side-effect awareness only) | **+ Add medication**, **Edit**, **Remove** |
| Check-ins | Status, missed days, weekly summary, today's message | **Edit EN / Edit FR** |
| Bot settings | How Sarah talks to this patient | Toggles, **Edit** instructions, include/skip questions |
| Custom flag words | Extra words to watch for this patient | **+ Add a word** |
| Consultation record | Phase 2 mock-up; account and demographic notes use the selected patient's saved details | – |

## The 5-minute stage script

Before the pitch: `python Pillway.py --reset-demo`, then open two windows side by side:
`python Pillway.py --role patient` and `python Pillway.py --role pharmacist`.

| # | Click / type (patient window) | What should appear |
|---|---|---|
| 1 | **Check up → Chat → I agree**, type `hi` | Sarah's summary (type 2 diabetes, high blood pressure, 142/90, doesn't smoke, Metformin and Ramipril) and **"Are there any changes since you filled this in?"** |
| 1b | `I've been feeling dizzy and my doctor started me on a new pill` | Message turns **amber**. "Here's what I updated: new symptom: dizziness; new medicine…", "Dizziness can be a common side effect of Ramipril… I've let your pharmacist know", then the diet question. |
| 2 | Tap **I'm not sure what to eat** | Plate-method tip, then **"has a doctor ever told you to limit protein…?"** |
| 2b | Tap **No** | **"at 78 kg, aim for about 62 to 78 g of protein a day"** with food examples, then the feet question. |
| 3 | `I have a sore on my foot that won't heal and my toes feel numb` | Bubble turns **red with a flag and "Shared with your pharmacist"**. Sarah asks where, how long, getting bigger/red/warm/leaking, 1-10, and says **"A pharmacist will contact you soon. If you feel very unwell, call 911…"**. In the pharmacist window Maria's tile jumps to the front with a **red badge**. |
| 3b *(optional)* | **Back → Call**. Hold the green button and speak, or tap it in demo mode. **End**. | Green ring moves, captions appear, the call shows in the pharmacist **Log** labelled **CALL**. |
| 4 | Answer the rest quickly (or set `max_questions_per_check_in = 3` in the config to skip ahead), then `no` to **"Is there anything else…?"** | "Your care plan draft is ready…". **Care plan** tab shows English then French. **Tasks** shows the new tasks. |
| 5 | Pharmacist window: click **Maria** | Flag cards with AI reasons and the 3-line recap; **Possible issues**. In **Care plan**: **Set** A1C target to 7.0, **Edit EN** one line, see **History**, **Approve**. Back in **Flagged messages**: **✓ Resolve** a flag; the badge count drops. |

Rehearse with `python Pillway.py --rehearse` (3 times in demo mode, 3 times with your key).

## Common settings

Everything lives in **`pillway_config.toml`** (heavily commented). Save, then restart the app.

| I want to… | Edit this line |
|---|---|
| Use a cheaper model for development | `chat_model = "gemini-3.5-flash-lite"` (also `care_plan_model`, `summary_model`) |
| Change the safety-check model | `flag_model = "gemini-3.5-flash-lite"` |
| Faster or deeper replies | `thinking_level = "low"` (fastest) / `"medium"` / `"high"` |
| Change the monthly follow-up topics | edit `data/follow_up_topics.json` (one topic per follow-up call) |
| Run with no AI | `demo_mode = true` |
| Change a danger threshold | `[safety]` → `blood_sugar_low = 3.9` (all placeholders: confirm with Pillway) |
| Start in French | `[patient]` → `default_language = "fr"` |
| Make the demo shorter | `[patient]` → `max_questions_per_check_in = 3` |
| Compare with/without pharmacist review | `[pharmacist]` → `pharmacist_review_required = false` (or the switch on the Care plan screen) |
| Show more made-up patients | `[demo]` → `visible_patients = ["maria", "james", "priya", "luc"]` |
| Re-skin with Pillway's colours | `[branding]` → `red = "#ef3f3f"` etc. |

## Troubleshooting

| Problem | Fix |
|---|---|
| **"API key not found"** / always demo mode | Check `pillway_config.local.toml` exists (no `.example` in the name) and `python Pillway.py --check-config`. Also `pip install -r requirements.txt` (the `google-genai` package). |
| **Voice not working (read-aloud or microphone)** | First run **`python Pillway.py --check-voice`**. It speaks a test sentence, listens for 4 seconds, and prints **PROBLEM** lines with the fix for each one. |
| **Microphone hears nothing** | Windows: **Settings → Privacy & security → Microphone** → turn on *Microphone access* **and** *Let desktop apps access your microphone*, then restart VS Code. Mac: **System Settings → Privacy & Security → Microphone** → allow Terminal / VS Code. |
| **Speech-to-text never types anything** | The first use downloads a ~40 MB offline model (needs internet once; do it before the venue). On Windows, if that can't work, the app switches to Windows' built-in speech recognition automatically (`speech_to_text_engine = "auto"` in `pillway_config.toml`; set `"windows"` to force it). You can always tap **Switch to chat**. |
| **Sarah answers herself on a call** (hears her own voice through the speakers) | Fixed: the mic is closed while she talks and for ~1 s after. Run with the terminal visible: lines like `mic OFF (reason=Sarah is talking)` and `heard (DROPPED)` show it working. If it still happens, use headphones or raise the tail (`ECHO_TAIL_SECONDS` in `pillway/ui/patient/call_audio.py`). |
| **Read-aloud is silent** | The app uses the computer's own voice (PowerShell speech on Windows, `say` on Mac). Check the volume and the output device. `--check-voice` shows the exact error. |
| **App looks too big or small** | Resize the window; everything is drawn as vectors and scales. Windows: Settings → Display → Scale at 100–150%. |
| **Fonts look wrong on Mac** | Normal: Macs don't have Segoe UI, so the app picks SF Pro / Helvetica Neue automatically (`pillway/ui/theme.py`). |
| **Something freezes on stage** | Don't panic: close the window, run `python Pillway.py --demo --role patient`. Data is saved after every message, so nothing is lost. |
| **"tkinter is missing"** | Reinstall Python from python.org with tcl/tk ticked (Mac Homebrew: `brew install python-tk`). |

---

# Part 2: Developer guide

## Folder map

```
Pillway.py                       start here: checks Python, reads options, opens the window
pillway_config.toml              THE settings file for everyone (commented)
pillway_config.local.example.toml   copy to pillway_config.local.toml (gitignored) and paste your key
.env.example                     another way to give the key (copy to .env, gitignored)
requirements.txt                 pinned packages
config/                          the ONLY code that reads settings/.env
  schema.py                        every setting, its default and allowed values
  validation.py                    plain-English errors for typos
  loader.py                        merges the files, finds the API key, key safety net
data/                            content, never code: edit these freely
  buzzwords.json                   danger words by tier (layer 1)
  questions.json                   Sarah's questions, in order, EN + FR
  advice.json                      Sarah's offline replies (demo mode / fallback)
  care_plan_template.json          Pillway's care plan PDF as data (EN + FR)
  check_in_messages.json           weekly topics and daily messages
  french_strings.json              every patient-facing label, EN + FR
  seed_patients.json               made-up patients (Maria + 3 optional)
  sample_content.json              orders, banner, scripted call lines
docs/                            challenge PDFs, design inspiration, french_review.md
pillway/
  app.py                         the window: state, scaling, router (no business rules)
  cli.py, rehearse.py            command-line options and the stage-script rehearsal
  core/                          pure logic, no UI
    safety_rules.py                LAYER 1: buzzwords, negation, numbers
    flagging.py                    combines layer 1 + layer 2; AI can't downgrade Tier 1
    conversation_flow.py           the check-in steps, one question at a time, protein rule
    conversation_service.py        the front door for each message (save → flag → reply)
    reply_builder.py               assembles Sarah's reply; safety sentences added by code
    patient_summary.py             intake summary, change detection, side effects
    care_plan.py                   build / edit / undo / approve / export the care plan
    tasks.py, check_ins.py         auto tasks (never medication), ACTIVE/WATCHING/missed
    deidentify.py                  removes names/contacts before the AI sees anything
    output_guard.py                checks every AI reply before the patient sees it
    answer_parsing.py              understands yes/no, numbers, readings offline
    medical_robot.py, medical_guidance.py   the team's original rule-based Sarah (kept)
  ai/
    client.py                      the ONLY code that calls the AI API
    brain.py                       one interface for real AI and demo mode, with fallback
    demo_mode.py                   offline replies with the same JSON shape as the AI
    parsers.py                     checks the AI's JSON; unknown fields are dropped
    prompts/                       Sarah's instructions + worked examples (plain text)
  storage/                       saving data
    patient_store.py               ONE file per patient = one source of truth
    json_store.py, file_lock.py    safe saving shared by two windows
    audit_log.py, edit_history.py  responsible-AI proof: every decision and edit
    app_state.py, paths.py         remembered UI choices, where data lives
    chat_history.py, profile_store.py, profiles.py   accounts (Manage profiles)
  ui/                            drawing only
    theme.py, navigation.py, i18n.py, live_sync.py, login.py, canvas_helpers.py
    components/                    icons, buttons, dropdown, scroll areas
    shell/                         sidebar and header
    patient/                       check_up, chat, chat_actions, consent, call, call_audio,
                                   care_plan, tasks, medications, prescription, orders, settings, manage_profiles
    pharmacist/                    dashboard, patient_detail, flags, highlights, log,
                                   care_plan_editor, medication_review, check_ins, bot_settings,
                                   workspace_router + consult_pages (Pillway's form, static)
  voice/                         speech_input.py (offline Vosk), tts.py (read-aloud)
tests/                           safety tests first; run them before every demo
tools/generate_french_review.py  rebuilds docs/french_review.md
```

## How it fits together

```
 Patient types / speaks
        │
        ▼
 ui/patient/chat_actions.py ──(background thread)──► core/conversation_service.py
                                                     │ 1. save the message (never lost)
                                                     │ 2. LAYER 1 core/safety_rules.py  (instant, offline)
                                                     │      urgent? ──► red bubble + flag on dashboard NOW
                                                     │ 3. core/conversation_flow.py decides the next step
                                                     │ 4. ai/brain.py ──► ai/client.py ──► Gemini API  
                                                     │      (de-identified; falls back to ai/demo_mode.py)
                                                     │      • LAYER 2 flag check (Haiku)  • Sarah's paragraph (Opus)
                                                     │ 5. core/flagging.py: AI may add/raise, never clear Tier 1
                                                     │ 6. core/output_guard.py checks the AI text
                                                     │ 7. core/reply_builder.py adds safety sentences + ONE question
                                                     ▼
                                         storage/patient_store.py  (+ audit_log)
                                                     │  (file changes)
                                                     ▼
                     ui/live_sync.py redraws BOTH windows within ~1 s
                     patient: reply bubble · pharmacist: red badge, log, flag cards
```

## How do I…?

**Add a buzzword**
1. Open `data/buzzwords.json`. 2. Add the phrase to the `phrases` list of the right rule (tier1 = urgent, tier2 = watch, tier3 = context).
3. Save and restart. 4. Run `python -m unittest tests.test_safety`.

**Add or reword a question**
1. Open `data/questions.json`. 2. Edit `en` / `fr` / `quick_en` / `quick_fr`. 3. For a new question, add an entry with a new `id`
(optional: a small handler in `core/conversation_flow.py` `ANSWER_HANDLERS` and advice in `data/advice.json`). 4. Restart.

**Add a new screen or tab**
1. Create `pillway/ui/patient/my_screen.py` with a `class MyScreenMixin:` and a `draw_my_screen(self, x1, x2, y)` method.
2. Add the mixin to the class list in `pillway/app.py`. 3. Add the tab to `TABS` in `pillway/ui/navigation.py` (and labels in
`data/french_strings.json`). 4. Route it in `pillway/ui/patient/dashboard.py`.

**Add a care plan section**
1. Open `data/care_plan_template.json`. 2. Add a section `{ "id", "en", "fr", "ai_lifestyle", "lines": [...] }` in the right order.
3. Use `"kind": "target"` and `{blank}` for anything the pharmacist must set. 4. Restart; drafts made after this include it.

**Change Sarah's instructions**: edit `pillway/ai/prompts/system_prompt.md` (and the examples in `prompts/examples/`).
The hard safety rules are ALSO enforced in code, so a prompt edit can't remove them.

**Change a colour**: brand colours are in `[branding]` of `pillway_config.toml`; others in `pillway/ui/theme.py`.

**Add a made-up patient**: add an entry to `data/seed_patients.json`, then add its id to `visible_patients` in the config.

**Add a test**: create `tests/test_something.py` with `unittest.TestCase` classes; start the file with
`from tests.helpers import use_temp_settings; use_temp_settings()` so it never touches real data.

## Rules of the codebase

- **UI files draw; core files decide.** `pillway/core` never imports `pillway/ui`.
- **Only `ai/client.py` talks to the AI.** Only `config/` reads the settings files and `.env`.
- **No magic numbers or content in code**: thresholds go in the config, words/questions/messages in `data/`.
- Small files, one job each, a comment at the top saying what the file is for and who calls it.
- Names: `draw_…` draws, `…_section` is a pharmacist page, `…Mixin` is a piece of the window class.

## Tests

Run all tests: `python -m unittest discover -s tests` (Mac: `python3`). They check:
safety tiers and thresholds (`test_safety`), privacy, the output guard and prompt injection
(`test_privacy_and_guardrails`), the patient flow, the stage script, French, restart-without-data-loss and
two-window sync (`test_patient_flow`), the live-AI path with a fake API (`test_ai_live_path`), the config,
and the team's original tests (robot, chat history, profiles, speech, app data controls).

## Git for beginners

1. **Pull before you start**: `git checkout main && git pull`
2. **Make a branch**: `git checkout -b my-change`
3. **Commit**: `git add -A && git commit -m "Short description"`
4. **Push**: `git push -u origin my-change`, then open a **Pull Request** on GitHub.
5. **Merge conflict?** Git marks the file with `<<<<<<<`. Keep the right lines, delete the markers, `git add` the file, `git commit`. Ask for help if unsure.
6. **Never commit** `pillway_config.local.toml`, `.env` or anything with a key.

## Glossary

| Term | Plain meaning |
|---|---|
| Layer 1 flag | A hard-coded rule found a danger word or number. Works with no internet. Decides "urgent". |
| Layer 2 flag | The AI read the message in context: it filters false alarms and catches what words miss. |
| Tier 1 / 2 / 3 | Urgent (red, pharmacist now) / Watch (amber) / background context only (never an alert). |
| De-identify | Swap the name for "Patient A" and remove contact details before the AI sees anything. |
| Demo mode | Sarah uses built-in replies: no AI, no internet. |
| System prompt | Sarah's written instructions (`ai/prompts/system_prompt.md`). No model "training" happens. |
| Care plan | The patient's personal plan in Pillway's template: goals, A1C, blood pressure, cholesterol, medications, exercise, sensors, barriers. |
| Check-in | A short chat or call between pharmacist calls, one topic a week (fibre, foot care…). |
| CASL | Canada's Anti-Spam Law: reminders only after the patient says yes, and easy to turn off. |
| PHIPA | Ontario's health privacy law: consent, and only the people who need it see health data. |

## Where does data go?

- **Stored on this computer only**: everything about each patient (profile, messages, flags, care plan) in
  `AppData\Local\Pillway` (Windows) or `~/.local/share/Pillway` (Mac/Linux), plus an audit log. Nothing is uploaded.
- **Sent to the AI (only in live mode)**: age, sex, weight/height, conditions, medicine names and doses,
  readings, the pharmacist's settings and the last few messages, with the name replaced by "Patient A" and
  phone numbers, emails, addresses, health card numbers and dates of birth removed. Run `python Pillway.py --show-ai-payload` to see it.
- **Never sent**: name, contact details, address, health card number, date of birth.
- All patients in this demo are made up.

## Design decisions

- **Safety in code, not just in the prompt**: urgent replies, "a pharmacist will contact you", the protein rule
  and "one question at a time" are added by code, so the AI can't forget or be talked out of them.
- **Hybrid brain**: the pharmacist's question list drives the order; the AI writes the personal advice in between.
  This keeps the demo stable and makes Sarah more useful than "just Google it".
- **Two windows, one truth**: one file per patient with a lock; both windows read it every 0.7 s.
- **Older patients**: big text, 44-px buttons, quick replies, read-aloud, EN/FR always visible, red flags also
  have an icon and words (never colour alone), iPhone-style call screen, "Talk to a pharmacist" always visible.
- **Busy pharmacists**: dashboard answers who/what/next; badges count only open flags; repeat flags on the same
  topic are grouped; every action is ≤ 2 clicks; every edit is logged and can be undone.
- **From the mockups (docs/design_inspiration)**: we kept Pillway's consultation form layout, red "pillway" header style,
  tables and toggles. We changed the patient screen's sidebar to **black** (as the team asked) and put the AI
  sections (flags, possible issues, log, care plan) first, because that's what the pharmacist needs first.
