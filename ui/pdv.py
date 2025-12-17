"""PDV completo com navegação por teclado e camadas separadas.

Execute ``python -m ui.pdv`` para abrir o PDV diretamente.
"""
from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
# Garantimos que a raiz do projeto está no PYTHONPATH mesmo quando o arquivo é
# executado diretamente (ex.: ``python c:/.../ui/pdv.py``).
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:  # execução como script direto
    from models import Comanda, ItemComanda, Produto
    from services.caixa_service import CaixaError, CaixaService
    from services.database import MemoryDB, SQLiteDB
    from services.pdv_service import PdvService
except ImportError:  # fallback caso o Python ignore o sys.path anterior
    sys.path.insert(0, str(ROOT_DIR))
    from models import Comanda, ItemComanda, Produto
    from services.caixa_service import CaixaError, CaixaService
    from services.database import MemoryDB, SQLiteDB
    from services.pdv_service import PdvService


class PdvApp:
    def __init__(
        self,
        master: tk.Tk,
        service: Optional[PdvService] = None,
        db: Optional[MemoryDB] = None,
        caixa_service: Optional[CaixaService] = None,
    ):
        self.master = master
        self.db = db or SQLiteDB()
        if not self.db.produtos:
            self.db.carregar_dados_demo()
        self.service = service or PdvService(self.db)
        self.caixa_service = caixa_service or CaixaService(self.db)

        self.mesa_selecionada: Optional[int] = 1
        self.mapa_itens_visiveis: List[int] = []

        self.master.title("PDV - Restaurante")
        self._construir_layout()
        self._bind_atalhos()
        self._garantir_comanda_atual(criar=False)
        self._atualizar_status_mesas()
        self._atualizar_lista_itens()
        self._atualizar_sugestoes()

    # --- Layout ---
    def _construir_layout(self) -> None:
        painel_mesas = tk.Frame(self.master)
        painel_mesas.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=8, pady=8)
        tk.Label(painel_mesas, text="Mesas/Balcão", font=("Arial", 11, "bold")).pack(anchor="w")
        self.lista_mesas = tk.Listbox(painel_mesas, height=22, exportselection=False)
        self.lista_mesas.pack(fill="y", expand=True)
        self.lista_mesas.bind("<<ListboxSelect>>", lambda _e: self._trocar_mesa())

        painel_itens = tk.Frame(self.master)
        painel_itens.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        self.master.grid_columnconfigure(1, weight=3)
        self.master.grid_rowconfigure(0, weight=1)

        barra_busca = tk.Frame(painel_itens)
        barra_busca.pack(fill="x")
        tk.Label(barra_busca, text="Buscar (código ou descrição)").grid(row=0, column=0, sticky="w")
        self.busca_entry = tk.Entry(barra_busca)
        self.busca_entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.busca_entry.bind("<KeyRelease>", self._atualizar_sugestoes)
        self.busca_entry.bind("<Return>", lambda _e: self._adicionar_produto())
        barra_busca.grid_columnconfigure(0, weight=1)
        self.busca_entry.focus_set()

        self.sugestoes_box = tk.Listbox(barra_busca, height=5, exportselection=False)
        self.sugestoes_box.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self.sugestoes_box.bind("<Return>", lambda _e: self._confirmar_sugestao())
        self.sugestoes_box.bind("<Double-Button-1>", lambda _e: self._confirmar_sugestao())

        tk.Label(painel_itens, text="Itens da comanda", font=("Arial", 11, "bold")).pack(anchor="w", pady=(8, 0))
        self.lista_itens = tk.Listbox(painel_itens, height=12, exportselection=False)
        self.lista_itens.pack(fill="both", expand=True, pady=(4, 0))

        self.total_label = tk.Label(painel_itens, text="Total: R$ 0,00", font=("Arial", 12, "bold"))
        self.total_label.pack(anchor="e", pady=(4, 0))

        painel_acoes = tk.Frame(self.master)
        painel_acoes.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)
        self.master.grid_columnconfigure(2, weight=1)

        tk.Label(painel_acoes, text="Atalhos", font=("Arial", 11, "bold")).pack(anchor="w")
        botoes = [
            ("F1 Abrir Mesa", self._abrir_mesa),
            ("F2 Adicionar Item", self._adicionar_produto),
            ("F3 Desc. Item", self._desconto_item),
            ("F4 Desc. Comanda", self._desconto_comanda),
            ("F5 Cancelar Item", self._cancelar_item),
            ("F6 Registrar Perda", self._registrar_perda),
            ("F7 Caixa", self._abrir_caixa),
            ("F8 Relatórios", self._mostrar_relatorios),
            ("F9 Fechar Comanda", self._fechar_comanda),
        ]
        for texto, func in botoes:
            tk.Button(painel_acoes, text=texto, width=20, command=func).pack(fill="x", pady=2)

        tk.Label(painel_acoes, text="Logs", font=("Arial", 11, "bold")).pack(anchor="w", pady=(8, 0))
        self.log_box = tk.Listbox(painel_acoes, height=12)
        self.log_box.pack(fill="both", expand=True)

    def _bind_atalhos(self) -> None:
        self.master.bind("<F1>", lambda _e: self._abrir_mesa())
        self.master.bind("<F2>", lambda _e: self._adicionar_produto())
        self.master.bind("<F3>", lambda _e: self._desconto_item())
        self.master.bind("<F4>", lambda _e: self._desconto_comanda())
        self.master.bind("<F5>", lambda _e: self._cancelar_item())
        self.master.bind("<F6>", lambda _e: self._registrar_perda())
        self.master.bind("<F7>", lambda _e: self._abrir_caixa())
        self.master.bind("<F8>", lambda _e: self._mostrar_relatorios())
        self.master.bind("<F9>", lambda _e: self._fechar_comanda())
        self.master.bind("<Escape>", lambda _e: self.busca_entry.focus_set())
        self.busca_entry.bind("<Down>", lambda e: self._navegar_sugestoes(1, e))
        self.busca_entry.bind("<Up>", lambda e: self._navegar_sugestoes(-1, e))
        self.sugestoes_box.bind("<Down>", lambda e: self._navegar_sugestoes(1, e))
        self.sugestoes_box.bind("<Up>", lambda e: self._navegar_sugestoes(-1, e))

    # --- Mesa/Comanda ---
    def _garantir_comanda_atual(self, criar: bool = True) -> Optional[Comanda]:
        if self.mesa_selecionada is None:
            self.mesa_selecionada = 1
        mesa_idx = self.mesa_selecionada
        if mesa_idx == 0:
            if not hasattr(self, "balcao_comanda_id"):
                if not criar:
                    return None
                comanda = self.service.abrir_comanda(None)
                self.balcao_comanda_id = comanda.id
            return self.db.comandas.get(self.balcao_comanda_id)
        mesa = self.db.mesas[mesa_idx - 1]
        if mesa.comanda_id is None:
            if not criar:
                return None
            comanda = self.service.abrir_comanda(mesa.numero)
            mesa.comanda_id = comanda.id
        return self.db.comandas.get(mesa.comanda_id)

    def _trocar_mesa(self) -> None:
        selecao = self.lista_mesas.curselection()
        if not selecao:
            return
        self.mesa_selecionada = selecao[0]
        self._atualizar_lista_itens()
        self._atualizar_status_mesas()

    def _abrir_mesa(self) -> None:
        self._garantir_comanda_atual()
        self._atualizar_status_mesas()

    # --- Produtos ---
    def _navegar_sugestoes(self, delta: int, event=None) -> str | None:
        """Permite navegar com setas mantendo a seleção visível."""

        moved = self._mover_sugestao(delta)
        if moved:
            self.sugestoes_box.focus_set()
            return "break" if event else None
        return None

    def _mover_sugestao(self, delta: int) -> bool:
        if not self.sugestoes_box.size():
            return False
        sel = self.sugestoes_box.curselection()
        idx = sel[0] if sel else 0
        idx = max(0, min(self.sugestoes_box.size() - 1, idx + delta))
        self.sugestoes_box.selection_clear(0, tk.END)
        self.sugestoes_box.selection_set(idx)
        self.sugestoes_box.see(idx)
        return True

    def _produto_selecionado(self) -> Optional[Produto]:
        sel = self.sugestoes_box.curselection()
        if sel:
            codigo = self.sugestoes_box.get(sel[0]).split(" - ")[0]
            return self.db.produtos.get(codigo)
        texto = self.busca_entry.get().strip()
        if texto and texto in self.db.produtos:
            return self.db.produtos[texto]
        return None

    def _confirmar_sugestao(self) -> None:
        prod = self._produto_selecionado()
        if prod:
            self.busca_entry.delete(0, tk.END)
            self.busca_entry.insert(0, prod.codigo)
            self._adicionar_produto()

    def _adicionar_produto(self) -> None:
        comanda = self._garantir_comanda_atual()
        produto = self._produto_selecionado()
        if not produto:
            messagebox.showwarning("Produto não encontrado", "Selecione um produto válido.")
            return
        quantidade = 1.0
        if produto.por_quilo:
            peso_str = simpledialog.askstring("Peso", "Informe o peso em gramas", parent=self.master)
            if not peso_str:
                return
            try:
                quantidade = float(peso_str) / 1000
            except ValueError:
                messagebox.showerror("Peso inválido", "Use apenas números.")
                return
        self.service.adicionar_item(comanda.id, produto.codigo, quantidade)
        self._atualizar_lista_itens()
        self._atualizar_status_mesas()
        self.busca_entry.delete(0, tk.END)
        self.busca_entry.focus_set()

    def _atualizar_sugestoes(self, _event=None) -> None:
        termo = self.busca_entry.get().lower().strip()
        sugestoes = [p for p in self.db.produtos.values() if termo in p.codigo.lower() or termo in p.descricao.lower()]
        sugestoes.sort(key=lambda p: p.codigo)
        self.sugestoes_box.delete(0, tk.END)
        for prod in sugestoes:
            texto = f"{prod.codigo} - {prod.descricao} (R$ {prod.preco:.2f})"
            if prod.por_quilo:
                texto += " - kg"
            self.sugestoes_box.insert(tk.END, texto)
        if sugestoes:
            self.sugestoes_box.selection_set(0)

    # --- Itens / descontos ---
    def _item_selecionado(self) -> Optional[ItemComanda]:
        sel = self.lista_itens.curselection()
        if not sel:
            return None
        item_id = self.mapa_itens_visiveis[sel[0]]
        return next((i for i in self.db.itens if i.id == item_id), None)

    def _desconto_item(self) -> None:
        item = self._item_selecionado()
        if not item:
            messagebox.showinfo("Selecione um item", "Escolha um item antes de aplicar desconto.")
            return
        motivo = self._escolher_motivo_desconto()
        if motivo is None:
            return
        valor = self._solicitar_valor("Desconto no item")
        if valor is None:
            return
        self.service.aplicar_desconto_item(item.comanda_id, item.id, valor, motivo)
        self._atualizar_lista_itens()

    def _desconto_comanda(self) -> None:
        comanda = self._garantir_comanda_atual(criar=False)
        if not comanda:
            messagebox.showinfo("Comanda", "Abra a mesa antes de aplicar desconto.")
            return
        motivo = self._escolher_motivo_desconto()
        if motivo is None:
            return
        valor = self._solicitar_valor("Desconto na comanda")
        if valor is None:
            return
        self.service.aplicar_desconto_comanda(comanda.id, valor, motivo)
        self._atualizar_lista_itens()
        self._atualizar_status_mesas()

    def _cancelar_item(self) -> None:
        item = self._item_selecionado()
        if not item:
            messagebox.showinfo("Selecione um item", "Escolha um item para cancelar.")
            return
        motivo = simpledialog.askstring("Motivo", "Informe o motivo do cancelamento", parent=self.master)
        if not motivo:
            return
        self.service.cancelar_item(item.id, motivo)
        self._atualizar_lista_itens()
        self._atualizar_status_mesas()

    # --- Perdas / estoque ---
    def _registrar_perda(self) -> None:
        prod = self._produto_selecionado() or self._dialogo_produto()
        if not prod:
            return
        motivo = self._escolher_motivo_perda()
        if motivo is None:
            return
        quantidade = self._solicitar_quantidade_perda(prod)
        if quantidade is None:
            return
        valor_sugerido = quantidade * prod.preco
        valor_informado = self._solicitar_valor(
            "Valor da perda (edite se necessário)",
            valor_inicial=f"{valor_sugerido:.2f}",
        )
        if valor_informado is None:
            return
        valor = self.service.registrar_perda(prod.codigo, quantidade, motivo, valor_total=valor_informado)
        messagebox.showinfo(
            "Perda registrada",
            f"Qtd: {quantidade:.3f} | Valor informado: R$ {valor_informado:.2f}",
        )
        self._atualizar_logs()

    def _dialogo_produto(self) -> Optional[Produto]:
        codigo = simpledialog.askstring("Produto", "Informe o código do produto", parent=self.master)
        if not codigo:
            return None
        return self.db.produtos.get(codigo)

    # --- Caixa ---
    def _abrir_caixa(self) -> None:
        try:
            if self.db.caixa_aberto():
                messagebox.showinfo("Caixa", f"Caixa {self.db.caixa_aberto().id} já está aberto.")
                return
            saldo = self._solicitar_valor("Saldo inicial do caixa")
            if saldo is None:
                return
            caixa = self.caixa_service.abrir_caixa(saldo)
            messagebox.showinfo("Caixa", f"Caixa {caixa.id} aberto.")
            self._atualizar_logs()
        except CaixaError as exc:
            messagebox.showerror("Caixa", str(exc))

    def registrar_pagamento(
        self, valor: float, forma_pagamento: str, valor_recebido: float | None = None, comanda_id: int | None = None
    ) -> None:
        if not self.db.caixa_aberto():
            self._abrir_caixa()
        caixa_atual = self.db.caixa_aberto()
        if not caixa_atual:
            return
        forma_norm = forma_pagamento.lower()
        try:
            if forma_norm == "dinheiro":
                troco = (valor_recebido or valor) - valor
                mov = self.caixa_service.registrar_venda(
                    valor_total_venda=valor,
                    tipo_pagamento="DINHEIRO",
                    valor_recebido_em_dinheiro=valor_recebido,
                )
                if troco > 0:
                    messagebox.showinfo("Pagamento", f"Troco: R$ {troco:.2f}")
            else:
                mov = self.caixa_service.registrar_venda(
                    valor_total_venda=valor,
                    tipo_pagamento=forma_norm.upper(),
                )
            comanda_ref = comanda_id
            if comanda_ref is None:
                comanda_atual = self._garantir_comanda_atual(criar=False)
                comanda_ref = comanda_atual.id if comanda_atual else "desconhecida"
            self.db.log("venda", f"Comanda {comanda_ref} paga em {mov.forma_pagamento}", "pdv")
        except Exception as exc:
            messagebox.showerror("Pagamento", str(exc))
            return

    # --- Relatórios ---
    def _mostrar_relatorios(self) -> None:
        janela = tk.Toplevel(self.master)
        janela.title("Relatórios")
        vendas = self.service.relatorio_vendas()
        descontos = self.service.relatorio_descontos()
        perdas = self.service.relatorio_perdas()
        caixa = self.service.relatorio_caixa()

        texto = tk.Text(janela, width=80, height=30)
        texto.pack(fill="both", expand=True)
        texto.insert(tk.END, "Vendas\n")
        texto.insert(tk.END, f"Total bruto: R$ {vendas['total_bruto']:.2f}\n")
        texto.insert(tk.END, f"Total descontos: R$ {vendas['total_descontos']:.2f}\n")
        texto.insert(tk.END, f"Total líquido: R$ {vendas['total_liquido']:.2f}\n")
        texto.insert(tk.END, "Por forma de pagamento:\n")
        for forma, valor in vendas["por_forma"].items():
            texto.insert(tk.END, f"- {forma or 'N/I'}: R$ {valor:.2f}\n")
        texto.insert(tk.END, "\nDescontos por motivo:\n")
        for motivo, valor in descontos["por_motivo"].items():
            texto.insert(tk.END, f"- Motivo {motivo}: R$ {valor:.2f}\n")
        texto.insert(tk.END, "\nPerdas:\n")
        texto.insert(tk.END, f"Total: R$ {perdas['total']:.2f}\n")
        for prod, valor in perdas["por_produto"].items():
            texto.insert(tk.END, f"- Produto {prod}: R$ {valor:.2f}\n")
        texto.insert(tk.END, "\nCaixas:\n")
        for linha in caixa["caixas"]:
            texto.insert(
                tk.END,
                f"Caixa {linha['id']} aberto por {linha['aberto_por']} em {linha['aberto_em']}"
                f" | fechado por {linha.get('fechado_por')} | dif: {linha.get('diferenca', 0):.2f}\n",
            )
        texto.config(state="disabled")

    # --- Fechamento ---
    def _fechar_comanda(self) -> None:
        comanda = self._garantir_comanda_atual(criar=False)
        if not comanda:
            messagebox.showwarning("Comanda", "Selecione uma comanda aberta para fechar.")
            return
        total = comanda.total_liquido(self.db.itens)
        opcoes = {
            "1": "dinheiro",
            "2": "debito",
            "3": "credito",
            "4": "pix",
        }
        escolha = simpledialog.askstring(
            "Pagamento",
            "1-Dinheiro\n2-Débito\n3-Crédito\n4-PIX",
            parent=self.master,
        )
        if not escolha or escolha.strip() not in opcoes:
            messagebox.showwarning("Pagamento", "Selecione uma opção numérica válida (1 a 4).")
            return
        forma = opcoes[escolha.strip()]
        valor_recebido = None
        if forma == "dinheiro":
            valor_recebido = self._solicitar_valor("Valor pago em dinheiro")
            if valor_recebido is None:
                return
            if valor_recebido < total:
                messagebox.showerror("Pagamento", "Valor recebido menor que o total da comanda.")
                return
        self.registrar_pagamento(total, forma, valor_recebido, comanda_id=comanda.id)
        self.service.fechar_comanda(comanda.id)
        self._atualizar_status_mesas()
        self._atualizar_lista_itens()

    # --- Helpers ---
    def _solicitar_valor(self, titulo: str, valor_inicial: Optional[str] = None) -> Optional[float]:
        texto = simpledialog.askstring(titulo, "Valor", parent=self.master, initialvalue=valor_inicial)
        if texto is None:
            return None
        try:
            return float(texto.replace(",", "."))
        except ValueError:
            messagebox.showerror("Valor inválido", "Use apenas números.")
            return None

    def _solicitar_quantidade_perda(self, produto: Produto) -> Optional[float]:
        if produto.por_quilo:
            peso = simpledialog.askstring(
                "Peso perdido", "Informe o peso perdido em gramas", parent=self.master
            )
            if peso is None:
                return None
            try:
                return float(peso.replace(",", ".")) / 1000
            except ValueError:
                messagebox.showerror("Peso inválido", "Use apenas números.")
                return None
        quantidade = simpledialog.askstring(
            "Quantidade perdida", "Informe a quantidade perdida", parent=self.master
        )
        if quantidade is None:
            return None
        try:
            return float(quantidade.replace(",", "."))
        except ValueError:
            messagebox.showerror("Quantidade inválida", "Use apenas números.")
            return None

    def _escolher_motivo_desconto(self) -> Optional[int]:
        motivos = self.db.motivos_desconto
        escolhas = [f"{m.id} - {m.descricao}" for m in motivos]
        escolha = simpledialog.askstring("Motivo do desconto", "\n".join(escolhas), parent=self.master)
        if not escolha:
            return None
        try:
            motivo_id = int(escolha.split(" ")[0])
        except ValueError:
            return None
        return motivo_id

    def _escolher_motivo_perda(self) -> Optional[int]:
        motivos = self.db.motivos_perda
        escolhas = [f"{m.id} - {m.descricao}" for m in motivos]
        escolha = simpledialog.askstring("Motivo da perda", "\n".join(escolhas), parent=self.master)
        if not escolha:
            return None
        try:
            motivo_id = int(escolha.split(" ")[0])
        except ValueError:
            return None
        return motivo_id

    def _atualizar_lista_itens(self) -> None:
        comanda = self._garantir_comanda_atual(criar=False)
        self.lista_itens.delete(0, tk.END)
        self.mapa_itens_visiveis = []
        if not comanda:
            self.total_label.config(text="Total: R$ 0.00")
            self._atualizar_logs()
            return
        for item in self.db.itens:
            if item.comanda_id != comanda.id:
                continue
            produto = self.db.produtos.get(item.produto_codigo)
            nome = f"{item.produto_codigo} - {produto.descricao}" if produto else item.produto_codigo
            texto = (
                f"{nome} | {item.quantidade:.3f} x R$ {item.preco_unitario:.2f}"
                f" = R$ {item.total_liquido:.2f}"
            )
            if item.desconto:
                texto += f" (desc R$ {item.desconto:.2f})"
            if item.cancelado:
                texto += " [CANCELADO]"
            self.lista_itens.insert(tk.END, texto)
            self.mapa_itens_visiveis.append(item.id)
        total = comanda.total_liquido(self.db.itens)
        self.total_label.config(text=f"Total: R$ {total:.2f}")
        self._atualizar_logs()

    def _atualizar_status_mesas(self) -> None:
        self.lista_mesas.delete(0, tk.END)

        linhas: list[tuple[str, str]] = []
        if hasattr(self, "balcao_comanda_id") and self.balcao_comanda_id in self.db.comandas:
            comanda = self.db.comandas[self.balcao_comanda_id]
            total = comanda.total_liquido(self.db.itens)
            linhas.append((f"Balcão | {comanda.status.value} | R$ {total:.2f}", comanda.status.value))
        else:
            linhas.append(("Balcão | livre", "livre"))

        for mesa in self.db.mesas:
            if mesa.comanda_id:
                comanda = self.db.comandas[mesa.comanda_id]
                total = comanda.total_liquido(self.db.itens)
                linhas.append((f"Mesa {mesa.numero:02d} | {comanda.status.value} | R$ {total:.2f}", comanda.status.value))
            else:
                linhas.append((f"Mesa {mesa.numero:02d} | livre", "livre"))

        for idx, (texto, status) in enumerate(linhas):
            self.lista_mesas.insert(tk.END, texto)
            bg, fg = self._cores_status(status)
            try:
                self.lista_mesas.itemconfigure(idx, background=bg, foreground=fg)
            except tk.TclError:
                # itemconfigure may not be supported on some Tk variants; ignore coloring silently
                pass

        idx = self.mesa_selecionada or 0
        self.lista_mesas.selection_set(idx)
        self.lista_mesas.see(idx)

    def _cores_status(self, status: str) -> tuple[str, str]:
        cores = {
            "livre": ("#f2f2f2", "#000000"),
            "aberta": ("#d4f4d7", "#0f5132"),
            "fechada": ("#dbeafe", "#0b3c5d"),
        }
        return cores.get(status.lower(), ("#ffffff", "#000000"))

    def _atualizar_logs(self) -> None:
        self.log_box.delete(0, tk.END)
        for log in self.db.logs[-50:]:
            self.log_box.insert(tk.END, f"{log.criado_em:%H:%M} {log.acao}: {log.detalhes}")


def carregar_produtos() -> Dict[str, Produto]:
    db = MemoryDB()
    db.carregar_dados_demo()
    return db.produtos


def main() -> None:
    root = tk.Tk()
    db = MemoryDB()
    db.carregar_dados_demo()
    service = PdvService(db)
    PdvApp(root, service=service, db=db)
    root.mainloop()


if __name__ == "__main__":
    main()