import tkinter as tk
from tkinter import ttk, messagebox

class ComandaWindow(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Comandas")
        self.geometry("500x400")

        self.comandas = {}

        self.criar_interface()

    def criar_interface(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Número da Comanda:").pack()
        self.entry_numero = ttk.Entry(frame)
        self.entry_numero.pack()

        ttk.Button(frame, text="Abrir Comanda", command=self.abrir_comanda).pack(pady=5)

        ttk.Label(frame, text="Itens da Comanda:").pack(pady=5)

        self.lista_itens = tk.Listbox(frame)
        self.lista_itens.pack(fill="both", expand=True)

        ttk.Button(frame, text="Adicionar Item", command=self.adicionar_item).pack(pady=5)

    def abrir_comanda(self):
        numero = self.entry_numero.get()

        if not numero:
            messagebox.showwarning("Aviso", "Informe o número da comanda")
            return

        if numero not in self.comandas:
            self.comandas[numero] = []

        self.atualizar_lista(numero)

    def adicionar_item(self):
        numero = self.entry_numero.get()

        if not numero:
            messagebox.showwarning("Aviso", "Abra uma comanda primeiro")
            return

        item = "Item teste"
        self.comandas[numero].append(item)
        self.atualizar_lista(numero)

    def atualizar_lista(self, numero):
        self.lista_itens.delete(0, tk.END)

        for item in self.comandas[numero]:
            self.lista_itens.insert(tk.END, item)
