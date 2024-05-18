import os
import subprocess
import sys

def install_packages():
    """Install necessary packages listed in requirements.txt."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def run_main_script():
    """Run the main application script."""
    os.system("python3 SG.py")

if __name__ == "__main__":
    install_packages()
    run_main_script()

