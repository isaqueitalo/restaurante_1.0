"""Menu principal do sistema do restaurante.

Execute com ``python -m ui.main`` ou diretamente pelo caminho completo do
arquivo. Este módulo centraliza a navegação entre PDV, relatórios, controle de
caixa e cadastro de produtos usando as estruturas em memória compartilhadas.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import ttk, scrolledtext

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from models import Produto


from services.caixa_service import CaixaService, CaixaError

from services.database import MemoryDB, SQLiteDB
from services.pdv_service import PdvService

class MainMenu:
    """Menu principal com atalhos para módulos do sistema."""

    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Restaurante - Sistema")
        self.db = SQLiteDB()
        if not self.db.produtos:
            self.db.carregar_dados_demo()
        self.service = PdvService(self.db)
        self.caixa_service = CaixaService(self.db)

        self._construir_layout()

    def _construir_layout(self) -> None:
        titulo = tk.Label(self.master, text="Sistema do Restaurante", font=("Arial", 16, "bold"))
        titulo.pack(pady=12)

        descricao = tk.Label(
            self.master,
            text=(
                "Escolha um módulo. O PDV usa as mesmas tabelas em memória (produtos,"
                " mesas, comandas, caixa, perdas)."
            ),
            wraplength=420,
            justify="center",
        )
        descricao.pack(padx=12, pady=(0, 12))

        botoes_frame = tk.Frame(self.master)
        botoes_frame.pack(pady=8)

        tk.Button(botoes_frame, text="PDV", width=20, command=self._abrir_pdv).grid(row=0, column=0, padx=6, pady=6)
        tk.Button(botoes_frame, text="Relatórios", width=20, command=self._abrir_relatorios).grid(row=0, column=1, padx=6, pady=6)
        tk.Button(botoes_frame, text="Controle de Caixa", width=20, command=self._abrir_caixa).grid(
            row=1, column=0, padx=6, pady=6
        )
        tk.Button(botoes_frame, text="Cadastro de Produtos", width=20, command=self._abrir_cadastro).grid(
            row=1, column=1, padx=6, pady=6
        )

    def _abrir_pdv(self) -> None:
        janela = tk.Toplevel(self.master)
        janela.title("PDV")
        try:
            import importlib
            import sys as _sys

            # evita reuso de módulo parcialmente inicializado
            _sys.modules.pop("ui.pdv", None)
            pdv_mod = importlib.import_module("ui.pdv")
            pdv_cls = getattr(pdv_mod, "PdvApp")
        except Exception as exc:
            messagebox.showerror("PDV", f"Não foi possível abrir o PDV:\n{exc}")
            janela.destroy()
            return
        pdv_cls(janela, service=self.service, db=self.db)

    def _abrir_relatorios(self) -> None:
        janela = tk.Toplevel(self.master)
        janela.title("Relatórios")
        RelatoriosWindow(janela, self.service, self.caixa_service)

    def _abrir_caixa(self) -> None:
        janela = tk.Toplevel(self.master)
        janela.title("Controle de Caixa")
        CaixaControleWindow(janela, self.caixa_service)

    def _abrir_cadastro(self) -> None:
        janela = tk.Toplevel(self.master)
        janela.title("Cadastro de Produtos")
        CadastroProdutos(janela, self.db)


class CadastroProdutos:
    """Janela para gerenciar produtos em memória."""

    def __init__(self, master: tk.Toplevel, db: MemoryDB):
        from models import Produto

        self.master = master
        self.db = db
        self.produtos = db.produtos

        self._construir_layout()
        self._popular_lista()

    def _construir_layout(self) -> None:
        form = tk.Frame(self.master)
        form.pack(padx=12, pady=12, fill="x")

        tk.Label(form, text="Código (auto)").grid(row=0, column=0, sticky="w")
        self.codigo_entry = tk.Entry(form, width=10, state="readonly")
        self.codigo_entry.grid(row=1, column=0, padx=(0, 8))

        tk.Label(form, text="Descrição").grid(row=0, column=1, sticky="w")
        self.descricao_entry = tk.Entry(form, width=30)
        self.descricao_entry.grid(row=1, column=1, padx=(0, 8))

        tk.Label(form, text="Preço (R$)").grid(row=0, column=2, sticky="w")
        self.preco_entry = tk.Entry(form, width=10)
        self.preco_entry.grid(row=1, column=2, padx=(0, 8))

        self.por_quilo_var = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text="Vendido por quilo", variable=self.por_quilo_var).grid(row=1, column=3, padx=(0, 8))

        botoes_form = tk.Frame(form)
        botoes_form.grid(row=1, column=4, padx=(0, 8))
        tk.Button(botoes_form, text="Salvar", width=8, command=self._salvar).pack(side=tk.LEFT, padx=2)
        tk.Button(botoes_form, text="Editar", width=8, command=self._editar).pack(side=tk.LEFT, padx=2)
        tk.Button(botoes_form, text="Apagar", width=8, command=self._apagar).pack(side=tk.LEFT, padx=2)

        self.lista = tk.Listbox(self.master, width=80)
        self.lista.pack(padx=12, pady=(0, 12))
        self.lista.bind("<<ListboxSelect>>", lambda _e: self._preencher_form())
        self._definir_codigo_display("auto")

    def _popular_lista(self) -> None:
        self.lista.delete(0, tk.END)
        for produto in sorted(self.produtos.values(), key=lambda p: p.codigo):
            self.lista.insert(
                tk.END,
                f"{produto.codigo} - {produto.descricao} | R$ {produto.preco:.2f} | "
                f"{'por quilo' if produto.por_quilo else 'unitário'}",
            )

    def _salvar(self) -> None:
        descricao = self.descricao_entry.get().strip()
        preco_texto = self.preco_entry.get().replace(",", ".")
        por_quilo = self.por_quilo_var.get()

        if not descricao:
            messagebox.showwarning("Campos obrigatórios", "Informe a descrição do produto.")
            return

        try:
            preco = float(preco_texto)
        except ValueError:
            messagebox.showerror("Preço inválido", "Use apenas números para o preço.")
            return

        from models import Produto

        codigo = self._proximo_codigo()
        while codigo in self.produtos:
            codigo = self._proximo_codigo()

        self.produtos[codigo] = Produto(codigo=codigo, descricao=descricao, preco=preco, por_quilo=por_quilo)
        self.db.persist()
        self._popular_lista()

        self._limpar_form()

    def _preencher_form(self) -> None:
        codigo = self._codigo_selecionado()
        if not codigo:
            return
        produto = self.produtos.get(codigo)
        if not produto:
            return
        self._definir_codigo_display(produto.codigo)
        self.descricao_entry.delete(0, tk.END)
        self.descricao_entry.insert(0, produto.descricao)
        self.preco_entry.delete(0, tk.END)
        self.preco_entry.insert(0, f"{produto.preco:.2f}")
        self.por_quilo_var.set(produto.por_quilo)

    def _editar(self) -> None:
        codigo = self._codigo_selecionado()
        if not codigo:
            messagebox.showinfo("Selecione", "Escolha um produto para editar.")
            return
        descricao = self.descricao_entry.get().strip()
        preco_texto = self.preco_entry.get().replace(",", ".")
        por_quilo = self.por_quilo_var.get()
        if not descricao:
            messagebox.showwarning("Campos obrigatórios", "Informe a descrição.")
            return
        try:
            preco = float(preco_texto)
        except ValueError:
            messagebox.showerror("Preço inválido", "Use apenas números para o preço.")
            return
        produto_antigo = self.produtos[codigo]
        self.produtos[codigo] = Produto(
            codigo=codigo,
            descricao=descricao,
            preco=preco,
            por_quilo=por_quilo,
            estoque=produto_antigo.estoque,
        )
        self.db.persist()
        self._popular_lista()
        self._limpar_form()

    def _apagar(self) -> None:
        codigo = self._codigo_selecionado()
        if not codigo:
            messagebox.showinfo("Selecione", "Escolha um produto para apagar.")
            return
        if messagebox.askyesno("Confirmar", f"Apagar produto {codigo}?"):
            self.produtos.pop(codigo, None)
            self.db.persist()
            self._popular_lista()
            self._limpar_form()

    def _codigo_selecionado(self) -> str | None:
        selecao = self.lista.curselection()
        if not selecao:
            return None
        linha = self.lista.get(selecao[0])
        return linha.split(" - ")[0].strip()

    def _limpar_form(self) -> None:
        self.lista.selection_clear(0, tk.END)
        self.descricao_entry.delete(0, tk.END)
        self.preco_entry.delete(0, tk.END)
        self.por_quilo_var.set(False)
        self._definir_codigo_display("auto")
        self.codigo_entry.focus_set()

    def _definir_codigo_display(self, codigo: str) -> None:
        self.codigo_entry.configure(state="normal")
        self.codigo_entry.delete(0, tk.END)
        self.codigo_entry.insert(0, codigo)
        self.codigo_entry.configure(state="readonly")

    def _proximo_codigo(self) -> str:
        return str(self.db.next_id())


class RelatoriosWindow:
    """Relatórios simples de vendas, descontos, perdas e caixa."""

    def __init__(self, master: tk.Toplevel, pdv_service: PdvService, caixa_service: CaixaService):
        self.master = master
        self.pdv_service = pdv_service
        self.caixa_service = caixa_service

        self._construir_layout()
        self._popular_relatorios()

    def _construir_layout(self) -> None:
        self.texto = tk.Text(self.master, width=90, height=28)
        self.texto.pack(fill="both", expand=True, padx=12, pady=12)
        self.texto.configure(state="disabled")

    def _popular_relatorios(self) -> None:
        vendas = self.pdv_service.relatorio_vendas()
        descontos = self.pdv_service.relatorio_descontos()
        perdas = self.pdv_service.relatorio_perdas()
        caixas = self.pdv_service.relatorio_caixa()
        caixa_aberto = self.caixa_service.db.caixa_aberto()

        self.texto.configure(state="normal")
        self.texto.delete("1.0", tk.END)
        self.texto.insert(tk.END, "Vendas\n")
        self.texto.insert(tk.END, f"Total bruto: R$ {vendas['total_bruto']:.2f}\n")
        self.texto.insert(tk.END, f"Total descontos: R$ {vendas['total_descontos']:.2f}\n")
        self.texto.insert(tk.END, f"Total líquido: R$ {vendas['total_liquido']:.2f}\n")
        self.texto.insert(tk.END, "Por forma de pagamento:\n")
        for forma, valor in vendas["por_forma"].items():
            self.texto.insert(tk.END, f"- {forma or 'N/I'}: R$ {valor:.2f}\n")

        self.texto.insert(tk.END, "\nDescontos por motivo:\n")
        for motivo, valor in descontos["por_motivo"].items():
            self.texto.insert(tk.END, f"- Motivo {motivo}: R$ {valor:.2f}\n")

        self.texto.insert(tk.END, "\nPerdas:\n")
        self.texto.insert(tk.END, f"Total: R$ {perdas['total']:.2f}\n")
        for prod, valor in perdas["por_produto"].items():
            self.texto.insert(tk.END, f"- Produto {prod}: R$ {valor:.2f}\n")

        self.texto.insert(tk.END, "\nCaixas:\n")
        for linha in caixas["caixas"]:
            self.texto.insert(
                tk.END,
                f"Caixa {linha['id']} aberto por {linha['aberto_por']} em {linha['aberto_em']} | "
                f"fechado por {linha.get('fechado_por')} | dif: {linha.get('diferenca', 0):.2f}\n",
            )

        if caixa_aberto:
            saldo = self.caixa_service.calcular_saldo_dinheiro(caixa_aberto.id)
            self.texto.insert(tk.END, f"\nCaixa em aberto: {caixa_aberto.id} | saldo dinheiro R$ {saldo:.2f}\n")

        self.texto.configure(state="disabled")


class CaixaControleWindow:
    """Interface simples para controlar abertura, movimentações e fechamento do caixa."""

    def __init__(self, master: tk.Toplevel, service: CaixaService):
        self.master = master
        self.service = service

        self._construir_layout()
        self._atualizar_status()
        self._mostrar_movimento_dia()

    def _construir_layout(self) -> None:
        self.status_var = tk.StringVar()
        tk.Label(self.master, textvariable=self.status_var, font=("Arial", 11, "bold")).pack(pady=(8, 4))

        botoes = tk.Frame(self.master)
        botoes.pack(padx=12, pady=6, fill="x")

        tk.Button(botoes, text="Abrir caixa", command=self._abrir).pack(fill="x", pady=2)
        tk.Button(botoes, text="Registrar venda", command=self._registrar_venda).pack(fill="x", pady=2)
        tk.Button(botoes, text="Suprimento", command=self._suprimento).pack(fill="x", pady=2)
        tk.Button(botoes, text="Sangria", command=self._sangria).pack(fill="x", pady=2)
        tk.Button(botoes, text="Fechar caixa", command=self._fechar).pack(fill="x", pady=2)
        tk.Button(botoes, text="Último fechamento", command=self._mostrar_ultimo_fechamento).pack(fill="x", pady=2)

        filtro = tk.Frame(self.master)
        filtro.pack(padx=12, pady=(6, 2), fill="x")
        tk.Label(filtro, text="Data (AAAA-MM-DD)").pack(side="left")
        self.data_entry = tk.Entry(filtro, width=12)
        self.data_entry.pack(side="left", padx=(4, 8))
        self.data_entry.insert(0, datetime.now().date().isoformat())
        tk.Button(filtro, text="Ver movimento do dia", command=self._mostrar_movimento_dia).pack(side="left")
        tk.Button(filtro, text="Fechamento do dia", command=self._mostrar_fechamento_dia).pack(side="left", padx=(6, 0))

        colunas = ("hora", "tipo", "valor", "impacto", "descricao")
        self.mov_tree = ttk.Treeview(self.master, columns=colunas, show="headings", height=8)
        for col, titulo in zip(colunas, ["Hora", "Tipo", "Valor", "Impacto", "Descrição"]):
            self.mov_tree.heading(col, text=titulo)
            largura = 80 if col != "descricao" else 240
            self.mov_tree.column(col, width=largura, anchor="center")
        self.mov_tree.pack(padx=12, pady=(0, 6), fill="both", expand=True)

        self.resumo_label = tk.Label(self.master, text="", justify="left", anchor="w")
        self.resumo_label.pack(padx=12, pady=(0, 8), fill="x")

        self.log = tk.Text(self.master, width=60, height=8, state="disabled")
        self.log.pack(padx=12, pady=(0, 10), fill="both", expand=True)

    # --- ações ---------------------------------------------------------
    def _abrir(self) -> None:
        valor = self._solicitar_valor("Saldo inicial do caixa")
        if valor is None:
            return
        try:
            caixa = self.service.abrir_caixa(valor)
        except CaixaError as exc:
            messagebox.showerror("Caixa", str(exc))
            return
        self._registrar_log(f"Caixa {caixa.id} aberto com R$ {valor:.2f}")
        self._atualizar_status()

    def _registrar_venda(self) -> None:
        tipo = simpledialog.askstring("Tipo de pagamento", "DINHEIRO, DEBITO, CREDITO ou PIX")
        if not tipo:
            return
        total = self._solicitar_valor("Valor total da venda")
        if total is None:
            return
        recebido = None
        if tipo.strip().upper() == "DINHEIRO":
            recebido = self._solicitar_valor("Valor recebido em dinheiro")
            if recebido is None:
                return
        try:
            mov = self.service.registrar_venda(total, tipo, recebido)
        except CaixaError as exc:
            messagebox.showerror("Venda", str(exc))
            return
        self._registrar_log(f"Venda registrada ({mov.tipo.value}) R$ {mov.valor:.2f}")
        self._atualizar_status()

    def _suprimento(self) -> None:
        valor = self._solicitar_valor("Valor do suprimento")
        if valor is None:
            return
        try:
            mov = self.service.registrar_suprimento(valor)
        except CaixaError as exc:
            messagebox.showerror("Suprimento", str(exc))
            return
        self._registrar_log(f"Suprimento R$ {mov.valor:.2f}")
        self._atualizar_status()

    def _sangria(self) -> None:
        valor = self._solicitar_valor("Valor da sangria")
        if valor is None:
            return
        try:
            mov = self.service.registrar_sangria(valor)
        except CaixaError as exc:
            messagebox.showerror("Sangria", str(exc))
            return
        self._registrar_log(f"Sangria R$ {mov.valor:.2f}")
        self._atualizar_status()

    def _fechar(self) -> None:
        contado = self._solicitar_valor("Valor contado em dinheiro")
        if contado is None:
            return
        try:
            caixa = self.service.fechar_caixa(contado)
        except CaixaError as exc:
            messagebox.showerror("Caixa", str(exc))
            return
        mensagem = self._formatar_resumo_fechamento(self.service.resumo_fechamento(caixa.id))
        messagebox.showinfo("Resumo de fechamento", mensagem)
        self._registrar_log(mensagem.replace("\n", " | "))
        self._atualizar_status()

    def _mostrar_movimento_dia(self) -> None:
        texto_data = self.data_entry.get().strip()
        try:
            data_ref = datetime.strptime(texto_data, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Data inválida", "Use o formato AAAA-MM-DD.")
            return

        resultado = self.service.movimentos_do_dia(data_ref)
        self.mov_tree.delete(*self.mov_tree.get_children())
        for mov in resultado["movimentos"]:
            hora = mov.criado_em.strftime("%H:%M:%S") if mov.criado_em else ""
            self.mov_tree.insert(
                "",
                tk.END,
                values=(
                    hora,
                    mov.tipo.value,
                    f"R$ {mov.valor:.2f}",
                    f"{mov.valor_dinheiro_impacto:+.2f}",
                    mov.descricao,
                ),
            )

        resumo = (
            f"Total de movimentos: R$ {resultado['total_valor']:.2f}\n"
            f"Impactos positivos: {resultado['total_dinheiro_positivo']:+.2f}  |  "
            f"Impactos negativos: {resultado['total_dinheiro_negativo']:+.2f}"
        )
        self.resumo_label.config(text=resumo)

    def _formatar_resumo_fechamento(self, resumo: dict) -> str:
        pagamentos = resumo.get("pagamentos", {})
        linhas_pagamento = ["Forma               Valor (R$)", "------------------------------"]
        for chave in ("DINHEIRO", "DEBITO", "CREDITO", "PIX"):
            linhas_pagamento.append(f"{chave:<18} R$ {pagamentos.get(chave, 0.0):>10.2f}")

        inicial = resumo.get("valor_inicial", 0.0)
        entradas = resumo.get("total_movimentos_positivos", 0.0)
        saidas = abs(resumo.get("total_movimentos_negativos", 0.0))
        fluxo_liquido = entradas - saidas
        esperado = resumo.get("esperado_dinheiro", 0.0)
        contado = resumo.get("valor_contado", 0.0)
        diferenca = resumo.get("diferenca", 0.0)
        status_diff = "SOBRA" if diferenca > 0 else "FALTA" if diferenca < 0 else "OK"

        formula = [
            "Cálculo do esperado (ajuda de conferência)",
            f"  Inicial..............: R$ {inicial:>10.2f}",
            f"+ Entradas (+).........: R$ {entradas:>10.2f}",
            f"- Saídas (-)...........: R$ {saidas:>10.2f}",
            f"= Esperado em dinheiro : R$ {esperado:>10.2f}",
            f"  Contado em dinheiro  : R$ {contado:>10.2f}",
            f"  Diferença (+/-)......: R$ {diferenca:>10.2f} ({status_diff})",
        ]

        linhas = [
            f"CAIXA {resumo.get('caixa_id')} - FECHAMENTO",
            f"Abertura:   {resumo.get('abertura')}",
            f"Fechamento: {resumo.get('fechamento')}",
            "" + "-" * 70,
            "Movimentos em dinheiro (impacto na gaveta)",
            f"  Inicial..............: R$ {inicial:>10.2f}",
            f"  Entradas (+).........: R$ {entradas:>10.2f}",
            f"  Saídas (-)...........: R$ {saidas:>10.2f}",
            f"  Saldo parcial........: R$ {(inicial + fluxo_liquido):>10.2f}",
            f"  Esperado em dinheiro : R$ {esperado:>10.2f}",
            f"  Contado em dinheiro  : R$ {contado:>10.2f}",
            f"  Diferença (+/-)......: R$ {diferenca:>10.2f} ({status_diff})",
            "",
            *formula,
            "",
            "Totais por pagamento",
            *linhas_pagamento,
            "",
            "Outros totais",
            f"  Descontos............: R$ {resumo.get('descontos', 0.0):>10.2f}",
            f"  Suprimentos..........: R$ {resumo.get('suprimentos', 0.0):>10.2f}",
            f"  Sangrias.............: R$ {resumo.get('sangrias', 0.0):>10.2f}",
        ]
        return "\n".join(linhas)

    def _mostrar_ultimo_fechamento(self) -> None:
        try:
            resumo = self.service.resumo_ultimo_fechamento()
        except CaixaError as exc:
            messagebox.showerror("Fechamento", str(exc))
            return
        self._mostrar_relatorio_em_texto("Último fechamento", [self._formatar_resumo_fechamento(resumo)])

    def _mostrar_fechamento_dia(self) -> None:
        texto_data = self.data_entry.get().strip()
        try:
            data_ref = datetime.strptime(texto_data, "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Data inválida", "Use o formato AAAA-MM-DD.")
            return

        fechamentos = self.service.fechamentos_por_data(data_ref)
        if not fechamentos:
            messagebox.showinfo("Fechamento", "Nenhum fechamento encontrado para a data informada.")
            return

        mensagens = [self._formatar_resumo_fechamento(res) for res in fechamentos]
        self._mostrar_relatorio_em_texto("Fechamento do dia", mensagens)

    def _mostrar_relatorio_em_texto(self, titulo: str, blocos: list[str]) -> None:
        janela = tk.Toplevel(self.master)
        janela.title(titulo)
        area = scrolledtext.ScrolledText(janela, width=100, height=35)
        area.pack(fill="both", expand=True, padx=10, pady=10)
        area.insert(tk.END, "\n\n".join(blocos))
        area.configure(state="disabled")
        area.focus_set()

    # --- helpers -------------------------------------------------------
    def _solicitar_valor(self, titulo: str) -> float | None:
        texto = simpledialog.askstring(titulo, "Valor")
        if texto is None:
            return None
        try:
            return float(texto.replace(",", "."))
        except ValueError:
            messagebox.showerror("Valor inválido", "Use apenas números.")
            return None

    def _atualizar_status(self) -> None:
        caixa = self.service.db.caixa_aberto()
        if caixa:
            saldo = self.service.calcular_saldo_dinheiro(caixa.id)
            self.status_var.set(f"Caixa {caixa.id} ABERTO | saldo dinheiro R$ {saldo:.2f}")
        else:
            self.status_var.set("Nenhum caixa aberto")

    def _registrar_log(self, linha: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(tk.END, linha + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    MainMenu(root)
    root.mainloop()


if __name__ == "__main__":
    main()