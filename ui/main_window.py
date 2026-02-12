import tkinter as tk
from ui.comanda_window import ComandaWindow
from ui.produto_window import ProdutoWindow


class MainWindow:
    def __init__(self, user):
        self.root = tk.Tk()
        self.root.title("Sistema Restaurante")
        self.root.geometry("400x300")

        tk.Label(
            self.root,
            text=f"Bem-vindo, {user.username} ({user.role})",
            font=("Arial", 12)
        ).pack(pady=20)

        tk.Button(
            self.root,
            text="Gerenciar Comandas",
            width=25,
            command=self.abrir_comandas
        ).pack(pady=5)

        tk.Button(
            self.root,
            text="Cadastro de Produtos",
            width=25,
            command=self.abrir_produtos
        ).pack(pady=5)

        tk.Button(
            self.root,
            text="Sair",
            width=25,
            command=self.root.quit
        ).pack(pady=20)

        self.root.mainloop()

    def abrir_comandas(self):
        ComandaWindow()

    def abrir_produtos(self):
        ProdutoWindow()
