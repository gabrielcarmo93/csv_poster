# logger.py

def log_message(log_widget, message):
    """
    Escreve uma mensagem no widget de log (Text) e garante que o scroll acompanhe a última linha.
    """
    log_widget.insert("end", message + "\n")
    log_widget.see("end")
