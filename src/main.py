# main.py
import sys
from launcher import main as launcher_main
from services.cache import clear_cache


if __name__ == "__main__":
    #clear_cache()
    launcher_main()