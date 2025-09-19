# utils/logger.py

def log_message(log_widget, message: str):
    """
    Função centralizada para escrever mensagens no Text de log.
    Mantém o cursor no final para sempre mostrar a última linha.
    """
    log_widget.insert("end", message + "\n")
    log_widget.see("end")
