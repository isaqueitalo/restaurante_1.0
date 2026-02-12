import tkinter as tk
from tkinter import messagebox

from services import user_service
from ui.main_window import MainWindow


class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Login - Restaurante")
        self.root.geometry("300x200")

        tk.Label(root, text="Usuário").pack(pady=5)
        self.username_entry = tk.Entry(root)
        self.username_entry.pack()

        tk.Label(root, text="Senha").pack(pady=5)
        self.password_entry = tk.Entry(root, show="*")
        self.password_entry.pack()

        tk.Button(root, text="Entrar", command=self.login).pack(pady=15)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        try:
            user = user_service.autenticar(username, password)
            self.root.destroy()
            MainWindow(user)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
