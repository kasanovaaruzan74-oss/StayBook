"""Бұрынғы іске қосу командасына үйлесімді Streamlit launcher.

Негізгі интерфейс: streamlit run app/frontend/ui.py
Бұрынғы команда: streamlit run frontend/app.py
"""

from pathlib import Path
import runpy


if __name__ == "__main__":
    ui_path = Path(__file__).resolve().parents[1] / "app" / "frontend" / "ui.py"
    runpy.run_path(str(ui_path), run_name="__main__")
