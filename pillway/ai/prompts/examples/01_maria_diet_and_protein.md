# Example 1: Maria is unsure about diet (the "smart question" scene)

Patient A: newly diagnosed type 2 diabetes, high blood pressure, 78 kg, Metformin 500 mg, Ramipril 5 mg.

**Task:** Answer to the "diet" question. Patient said: "I'm not sure what to eat"
```json
{"advice": "That's very common when diabetes is new, so you're not alone. A simple start is the plate method: half your plate vegetables, a quarter protein, a quarter whole grains. To give you the right protein advice, I need to check one thing first.",
 "possible_issues": [], "summary_updates": [], "medication_question": false, "needs_pharmacist": false}
```
(The app then asks: "Has a doctor ever told you to limit protein, for example because of your kidneys?")

**Task:** Answer to "protein_limit". Patient said "No". App computed: 78 kg -> 62 to 78 g a day.
```json
{"advice": "Thanks. Since no doctor has asked you to limit protein, your personal target is about 62 to 78 g of protein a day. Two eggs at breakfast (12 g), Greek yogurt as a snack (17 g) and a palm-sized piece of chicken or fish at dinner (25 g) gets you most of the way. Spreading protein over your meals helps keep your blood sugar steadier.",
 "possible_issues": [], "summary_updates": [], "medication_question": false, "needs_pharmacist": false}
```
