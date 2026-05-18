# launcher.py
"""
Launcher del Asistente IMSS.
Permite seleccionar entre modalidad TI o M40 con opción de recordar preferencia.
"""
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, 
    QLabel, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from config import DATA_DIR
from services.cache import save_preference, load_preference


class Launcher(QWidget):
    """Ventana de selección de modalidad (TI o M40)."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente IMSS - Seleccionar Modalidad")
        self.setFixedSize(500, 300)
        self.setup_ui()
        
    def setup_ui(self):
        """Configura la interfaz del launcher."""
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Título
        title = QLabel("Selecciona la modalidad de trabajo:")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Botón TI
        self.btn_ti = QPushButton("Trabajadores Independientes (TI)")
        self.btn_ti.setMinimumHeight(60)
        self.btn_ti.clicked.connect(lambda: self.launch_mode("ti"))
        layout.addWidget(self.btn_ti)
        
        # Botón M40
        self.btn_m40 = QPushButton("Modalidad 40 (M40)")
        self.btn_m40.setMinimumHeight(60)
        self.btn_m40.clicked.connect(lambda: self.launch_mode("m40"))
        layout.addWidget(self.btn_m40)
        
        layout.addSpacing(10)
        
        # Checkbox "Recordar"
        self.check_remember = QCheckBox("Recordar mi elección")
        self.check_remember.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.check_remember, alignment=Qt.AlignCenter)
        
        layout.addStretch()
        
        self.setLayout(layout)
    
    def launch_mode(self, mode: str):
        """
        Lanza la aplicación en la modalidad seleccionada.
        
        Args:
            mode: "ti" o "m40"
        """
        # Guardar preferencia si está marcado
        if self.check_remember.isChecked():
            save_preference("mode", mode)
        
        # Cerrar launcher y ejecutar main con modalidad
        self.close()
        
        # Importar aquí para evitar dependencias circulares
        if mode == "ti":
            from interfaz.ti import InterfazTI
            self.main_window = InterfazTI()
            self.main_window.show()
        elif mode == "m40":
            from interfaz.m40 import InterfazM40
            self.main_window = InterfazM40()
            self.main_window.show()


def main():
    """Entry point del launcher."""
    app = QApplication(sys.argv)
    
    # Verificar si hay preferencia guardada
    saved_mode = load_preference("mode")
    
    if saved_mode:
        # Lanzar directamente en la modalidad guardada
        if saved_mode == "ti":
            from interfaz.ti import InterfazTI
            window = InterfazTI()
            window.show()
        elif saved_mode == "m40":
            from interfaz.m40 import InterfazM40
            window = InterfazM40()
            window.show()
        else:
            # Preferencia inválida, mostrar selector
            window = Launcher()
            window.show()
    else:
        # Mostrar selector
        window = Launcher()
        window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()