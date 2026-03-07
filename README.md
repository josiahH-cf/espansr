# 🧩 espansr

[![CI](https://github.com/josiahH-cf/espansr/actions/workflows/ci.yml/badge.svg)](https://github.com/josiahH-cf/espansr/actions/workflows/ci.yml)

**Manage your [Espanso](https://espanso.org/) text expansions with a visual GUI and powerful CLI.**

---

## ✨ What is this?

You know how you type the same emails, code snippets, and responses over and over? [Espanso](https://espanso.org/) auto-expands those for you — type a short trigger like `:greet` and it expands into a full message.

**espansr** gives you a visual template manager + CLI to organize, edit, validate, and sync your text expansion templates to Espanso. No more hand-editing YAML files.

---

## 🚀 Quick Start

### 1. Clone

```bash
git clone https://github.com/josiahH-cf/espansr.git
cd espansr
```

### 2. Install

```bash
# Linux / macOS / WSL2
./install.sh

# Windows (PowerShell)
.\install.ps1
```

### 3. Launch

```bash
espansr gui      # 🖥️  open the visual editor
espansr sync     # ⌨️  or sync from the command line
```

**That's it.** You're managing Espanso templates. 🎉

---

## 🔄 How It Works

```
┌─────────────────┐       ┌──────────┐       ┌─────────────────┐
│  Your Templates  │──────▶│  espansr  │──────▶│  Espanso Config  │
│  (JSON files)    │       │ GUI / CLI │       │  (YAML matches)  │
└─────────────────┘       └──────────┘       └─────────────────┘
                                                      │
                                                      ▼
                                              Type a trigger ➜
                                              Text auto-expands ✨
```

1. **Create/edit** templates in the GUI or as JSON files
2. **Sync** to Espanso with one click or `espansr sync`
3. **Type** your triggers anywhere — Espanso expands them instantly

---

## 🖥️ GUI + ⌨️ CLI

espansr works both ways — pick what fits your workflow:

### GUI

- Browse and search all your templates
- Edit triggers, content, and variables visually
- Live YAML preview — see exactly what Espanso will get
- Dark/light mode with system auto-detection
- One-click sync

### CLI

```bash
espansr sync             # sync templates → Espanso
espansr sync --dry-run   # preview without writing
espansr list             # list templates and triggers
espansr status           # check Espanso connection
espansr validate         # check templates for issues
espansr import file.json # import external templates
espansr doctor           # run diagnostic checks
```

📖 **Full CLI reference:** [docs/CLI.md](docs/CLI.md)

---

## 📦 Platform Support

| Platform | Install | CLI | GUI | Notes |
|----------|---------|-----|-----|-------|
| 🐧 Linux | `./install.sh` | ✅ | ✅ | Python 3.11+ |
| 🍎 macOS | `./install.sh` | ✅ | ✅ | Python 3.11+ |
| 🪟 Windows | `.\install.ps1` | ✅ | ✅ | Python 3.11+ in [PATH](https://www.python.org/downloads/) |
| 🐧 WSL2 | `./install.sh` | ✅ | ✅ | Requires Espanso installed/started on Windows; auto-detects Windows-side config |

If WSL installation reports missing Espanso config, run:

```bash
espansr wsl-install-espanso
```

---

## ⚡ Key Features

| Feature | Description |
|---------|-------------|
| 🎨 Template editor | Edit triggers, content, and variables with live preview |
| 🔄 One-click sync | Push templates to Espanso instantly |
| ✅ Validation | Catches issues before they reach Espanso |
| 📥 Import | Bring in external template files or directories |
| 🩺 Doctor | Diagnostic health checks for your setup |
| 🌙 Dark mode | Auto-detects system theme, or choose manually |
| ⌨️ Keyboard shortcuts | Ctrl+S sync, Ctrl+N new, Ctrl+I import, Ctrl+F search |
| 🔗 orchestratr | Optional integration with [orchestratr](https://github.com/josiahH-cf/orchestratr) app launcher |

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [CLI Reference](docs/CLI.md) | All commands, flags, and examples |
| [Template Format](docs/TEMPLATES.md) | JSON schema, variables, storage paths |
| [Verification Guide](docs/VERIFY.md) | Post-install checklist to confirm everything works |
| [Changelog](CHANGELOG.md) | Version history and release notes |
| [Development Guide](docs/DEVELOPMENT.md) | Setup, testing, project structure for contributors |

---

## 🛠️ Quick Template Example

```json
{
  "name": "Greeting",
  "content": "Hello, {{name}}! Thanks for reaching out.",
  "trigger": ":greet",
  "variables": [
    { "name": "name", "label": "Name", "default": "there" }
  ]
}
```

Type `:greet` anywhere → `Hello, there! Thanks for reaching out.` ✨

---

## 📄 License

[MIT](LICENSE)
