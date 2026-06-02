#!/usr/bin/env bash
set -e

echo "Starting Erdstall Admin GUI setup..."

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Project folder: $SCRIPT_DIR"

#Installing Homebrew if missing
if command -v brew >/dev/null 2>&1; then
  echo "Homebrew already installed. Skipping."
else
  echo "Homebrew not found. Installing Homebrew..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

if [ -x "/opt/homebrew/bin/brew" ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
elif [ -x "/usr/local/bin/brew" ]; then
    eval "$(/usr/local/bin/brew shellenv)"
fi

# Check again after loading shellenv
if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew was installed but brew is still not available in PATH."
    echo "Close Terminal, reopen it, and run this script again."
    exit 1
fi

echo "Using Homebrew: $(brew --version | head -n 1)"

#Installing Python 3.11
if brew list python@3.11 >/dev/null 2>&1; then
  echo "Python 3.11 already installed. Skipping"
else
  echo "Installing Python 3.11..."
  brew install python@3.11
fi

#Installing OpenJDK 17
if brew list openjdk@17 >/dev/null 2>&1; then
  echo "OpenJDK 17 already installed. Skipping."
else
  echo "Installing OpenJDK 17.."
  brew install openjdk@17
fi

export JAVA_HOME="$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
export PATH="$JAVA_HOME/bin:$PATH"

echo "Using Java: $(java -version 2>&1 | head -n 1)"

# Installing Node.js
if brew list node >/dev/null 2>&1; then
  echo "Node.js already installed. Skipping."
else
  echo "Installing Node.js..."
  brew install node
fi

echo "Using Node: $(node --version)"
echo "Using npm: $(npm --version)"

if [ -f "package.json" ]; then
  echo "package.json found. Running npm install..."
  npm install
else
  echo "No package.json found in project root."
fi

#Creating venv

PYTHON_311="$(brew --prefix python@3.11)/bin/python3.11"

if [ ! -x "$PYTHON_311" ]; then
  echo "ERROR: Python 3.11 executable not found at: $PYTHON_311"
  exit 1
fi

if [ -d ".venv" ]; then
  echo "Virtual environment already exists. Skipping creation."
else
  echo "Creating Python virtual environment..."
  "$PYTHON_311" -m venv .venv
fi

echo "Activating virtual environment"
source .venv/bin/activate

echo "Upgrading pip..."
python -m pip install --upgrade pip

#Installing requirements
if [ -f "requirements.txt" ]; then
  echo "Installing Python requirements from requirements.txt"
  python -m pip install -r requirements.txt
else
  echo "No requirements.txt found. Skipping..."
fi

echo "Starting GUI..."
python -m erdstall_admin_gui.main
