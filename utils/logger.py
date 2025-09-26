# utils/logger.py
from datetime import datetime

def log_message(log_widget, message: str):
    """
    Função centralizada para escrever mensagens no Text de log.
    Sempre inclui data e hora completa no timestamp.
    """
    # Gerar timestamp completo com data e hora
    timestamp = datetime.now().strftime("[%d/%m/%Y %H:%M:%S]")
    
    # Formatar mensagem com timestamp
    formatted_message = f"{timestamp} {message}"
    
    log_widget.insert("end", formatted_message + "\n")
    log_widget.see("end")

def log_message_with_level(log_widget, message: str, level="INFO"):
    """
    Função de log com níveis (INFO, WARNING, ERROR, SUCCESS)
    """
    level_icons = {
        "INFO": "ℹ️",
        "WARNING": "⚠️", 
        "ERROR": "❌",
        "SUCCESS": "✅",
        "DEBUG": "🔍"
    }
    
    icon = level_icons.get(level.upper(), "📝")
    timestamp = datetime.now().strftime("[%d/%m/%Y %H:%M:%S]")
    formatted_message = f"{timestamp} {icon} [{level}] {message}"
    
    log_widget.insert("end", formatted_message + "\n")
    log_widget.see("end")
