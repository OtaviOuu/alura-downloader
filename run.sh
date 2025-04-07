clear 

VENV_DIR="venv"
REQUIREMENTS_FILE="requirements.txt"
SCRIPT="main.py"

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r "$REQUIREMENTS_FILE"

python "$SCRIPT"
