# Espansr v1.0.0 — Verification Guide

A quick walkthrough to confirm everything works after install.

---

## 1. Install

```bash
# Linux / macOS / WSL2
./install.sh

# Windows (PowerShell)
.\install.ps1
```

## 2. Verify Version

```bash
espansr --version
```

**Expected:** `espansr 1.0.0`

## 3. Check Espanso Status

```bash
espansr status
```

**Expected:** Shows the detected Espanso config path, or a helpful message with install link if Espanso isn't found.

## 4. List Templates

```bash
espansr list
```

**Expected:** At least the bundled `espansr_help` template with its trigger.

## 5. Validate Templates

```bash
espansr validate
```

**Expected:** `All templates valid.` (or specific warnings/errors if templates have issues).

## 6. Sync to Espanso

```bash
espansr sync
```

**Expected:** Prints sync summary. If Espanso is installed, the match file is updated.

## 7. Import a Template

```bash
# Create a test template
echo '{"name":"Test","content":"Hello {{who}}","trigger":":test","variables":[{"name":"who","default":"World"}]}' > /tmp/test-template.json

espansr import /tmp/test-template.json
```

**Expected:** `Imported 1 template: Test`

## 8. Launch the GUI

```bash
espansr gui
```

**Expected:** Window opens with a template browser on the left and editor on the right. Verify you can:

- [ ] Select a template from the list
- [ ] See the trigger and content fields populated
- [ ] Edit a trigger and click Save
- [ ] See the YAML preview update live
- [ ] Add/edit/delete a variable in the variable editor
- [ ] Click "Sync Now" in the toolbar
- [ ] Close and reopen — window position and last template are remembered

## 9. Run Tests (Developer)

```bash
pip install -e .[dev]
pytest
ruff check .
black --check .
```

**Expected:** All 167 tests pass, zero lint errors, zero format issues.

---

**All steps pass? You're good to go.** 🎉
