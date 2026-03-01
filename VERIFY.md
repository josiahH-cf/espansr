# Espansr v1.1.0 — Verification Guide

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

**Expected:** `espansr 1.1.0`

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

## 6a. Sync Dry-Run

```bash
espansr sync --dry-run
```

**Expected:** Prints what would be synced without writing any files.

## 7. Import a Template

```bash
# Create a test template
echo '{"name":"Test","content":"Hello {{who}}","trigger":":test","variables":[{"name":"who","default":"World"}]}' > /tmp/test-template.json

espansr import /tmp/test-template.json
```

**Expected:** `Imported 1 template: Test`

## 7a. Run Doctor

```bash
espansr doctor
```

**Expected:** Prints a diagnostic report with `[ok]`, `[warn]`, or `[FAIL]` for each check (Python version, config dir, templates, Espanso config, binary, launcher, validation). Exit code 0 if no failures.

## 7b. Tab Completion

```bash
espansr completions bash
espansr completions zsh
```

**Expected:** Each prints a shell completion script containing all subcommand names and `--help`/`--version` flags.

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
- [ ] See the status bar update after sync (e.g., "Synced N template(s) to Espanso")
- [ ] See the template output preview below the YAML preview
- [ ] Switch theme via the toolbar combo (Auto/Dark/Light)
- [ ] Use keyboard shortcuts: Ctrl+S (sync), Ctrl+N (new), Ctrl+I (import), Ctrl+F (search), Delete (delete)
- [ ] Close and reopen — window position and last template are remembered

## 9. Run Tests (Developer)

```bash
pip install -e .[dev]
pytest
ruff check .
black --check .
```

**Expected:** All 298 tests pass, zero lint errors, zero format issues.

---

**All steps pass? You're good to go.** 🎉
