import tkinter as tk
from tkinter import messagebox

from services import produto_service


class ProdutoWindow:
    def __init__(self):
        self.root = tk.Toplevel()
        self.root.title("Cadastro de Produtos")
        self.root.geometry("500x400")

        self._criar_formulario()
        self._criar_lista()

    def _criar_formulario(self):
        frame = tk.Frame(self.root)
        frame.pack(pady=10)

        tk.Label(frame, text="Nome do Produto").grid(row=0, column=0, padx=5)
        self.nome_entry = tk.Entry(frame)
        self.nome_entry.grid(row=0, column=1)

        tk.Label(frame, text="Preço").grid(row=1, column=0, padx=5)
        self.preco_entry = tk.Entry(frame)
        self.preco_entry.grid(row=1, column=1)

        tk.Button(
            frame,
            text="Cadastrar Produto",
            command=self.criar_produto
        ).grid(row=2, column=0, columnspan=2, pady=10)

    def _criar_lista(self):
        self.lista = tk.Listbox(self.root, width=60)
        self.lista.pack(pady=10)

        tk.Button(
            self.root,
            text="Excluir Produto Selecionado",
            command=self.excluir_produto
        ).pack(pady=5)

        self.atualizar_lista()

    def atualizar_lista(self):
        self.lista.delete(0, tk.END)
        produtos = produto_service.listar_produtos()

        for p in produtos:
            texto = f"ID: {p.id} | {p.nome} | R$ {p.preco:.2f}"
            self.lista.insert(tk.END, texto)

    def criar_produto(self):
        try:
            nome = self.nome_entry.get()
            preco = float(self.preco_entry.get())

            if not nome:
                raise Exception("O nome do produto é obrigatório.")

            produto_service.criar_produto(nome, preco)

            self.nome_entry.delete(0, tk.END)
            self.preco_entry.delete(0, tk.END)

            self.atualizar_lista()

        except Exception as e:
            messagebox.showerror("Erro", str(e))

    def excluir_produto(self):
        selecionado = self.lista.curselection()

        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um produto.")
            return

        texto = self.lista.get(selecionado[0])
        produto_id = int(texto.split("|")[0].replace("ID:", "").strip())

        try:
            produto_service.excluir_produto(produto_id)
            self.atualizar_lista()
        except Exception as e:
            messagebox.showerror("Erro", str(e))
