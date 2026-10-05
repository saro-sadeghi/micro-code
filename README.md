# Micro Code

**A tiny, token-efficient coding agent for your terminal.**

Micro Code is a minimal, collaborative coding agent that can inspect a project, edit files, run commands, and verify changes. It aims to keep its tools, context, and architecture small.

> Use less context. Use fewer tokens. Do more.

## Requirements

- Python 3.11 or newer
- Git (recommended, for working with Git repositories)
- An API key for a supported model provider, or a compatible local OpenAI-style endpoint

## Install

### Option 1: Install directly from GitHub

```bash
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/saro-sadeghi/micro-code.git"
```

Then run:

```bash
micro
```

### Option 2: Clone the repository (for development)

```bash
git clone https://github.com/saro-sadeghi/micro-code.git
cd micro-code
python -m pip install -e .
```

Run the CLI:

```bash
micro
```

On Windows, use PowerShell or Windows Terminal. The commands above work there as well. If `micro` is not found immediately after installation, close and reopen the terminal, then try `python -m microcode` from the project directory.

### Optional: Use a virtual environment

A virtual environment keeps Micro Code's dependencies separate from other Python projects.

**Windows (PowerShell):**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
micro
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
micro
```

## First run

On first launch, Micro Code prompts you to select a provider, model, and API key. Your configuration and chat sessions are saved locally in its SQLite database. The API key is stored locally; do not share that database or commit it to Git.

Available setup choices:

- **Anthropic** — use an Anthropic API key and a model available to your account.
- **OpenAI** — use an OpenAI API key and a model available to your account.
- **Custom URL** — use an OpenAI-compatible API endpoint (for example, a local inference server). Enter the endpoint's base URL and model name when prompted.

The model list shown by the setup flow is a preset, not a guarantee of availability. If a preset is unavailable to your account, choose **Other** and enter a model identifier supported by your provider.

## Usage

Start Micro Code in the directory of the project you want it to work on:

```bash
cd path/to/your/project
micro
```

Type a task in the prompt, for example:

```text
> Find why the tests are failing and fix the smallest underlying issue.
```

Micro Code can inspect files, search source code, make edits, run commands, and review Git changes using its available tools. It asks for permission before running shell commands by default. Review commands and file changes before approving them.

### Interactive commands

| Command | Description |
|---|---|
| `/new` | Start a new session |
| `/sessions` | List recent sessions |
| `/resume <id>` | Resume a previous session |
| `/config` | Configure provider, model, and API key |
| `/model` | Change the model |
| `/permission` | Change shell command permission mode |
| `/loop` | Toggle agent-loop/tool-call details |
| `/exit` | Exit Micro Code |

## Configuration and privacy

- Configuration and session history are stored locally in SQLite under your home directory.
- The selected provider receives prompts, relevant conversation context, and tool results required to answer your task.
- Never paste API keys into source files or commit local configuration/database files.
- Shell commands can change your project or system. Keep command permission set to **ask** unless you intentionally want to allow commands automatically.

## Troubleshooting

### `micro` is not recognized

The Python Scripts directory may not be on your `PATH`, or the terminal may have been open before installation. Reopen the terminal and check:

```powershell
python -m pip show micro-code
python -c "import sys; print(sys.executable)"
python -m microcode
```

If you use multiple Python installations, install with the same interpreter that you use to run Micro Code:

```powershell
py -3.12 -m pip install "git+https://github.com/saro-sadeghi/micro-code.git"
```

### `ModuleNotFoundError: No module named 'microcode'`

Reinstall into the active Python environment:

```powershell
python -m pip install --force-reinstall "git+https://github.com/saro-sadeghi/micro-code.git"
```

For a local clone, run the command from the repository root:

```powershell
python -m pip install -e .
```

### `Could not find a version that satisfies ...`

This usually means pip cannot reach or use the configured package index, rather than that Micro Code itself is missing. Check your internet connection and pip index configuration. If your environment has no access to PyPI, install the declared dependencies from an approved package mirror before installing Micro Code. Avoid disabling build isolation as a routine installation method.

## Development

```bash
git clone https://github.com/saro-sadeghi/micro-code.git
cd micro-code
python -m venv .venv
# Activate the environment, then:
python -m pip install -e .
python -m pip install pytest
python -m pytest
```

## License

MIT ©.