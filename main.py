import tkinter as tk

from database.db import criar_tabelas
from services import user_service
from ui.login_window import LoginWindow


def main():
    criar_tabelas()

    # cria usuário admin padrão se não existir
    try:
        user_service.criar_usuario("admin", "admin123", "ADMIN")
    except Exception:
        pass

    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
