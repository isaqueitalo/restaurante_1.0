# Restaurante

Sistema simples de restaurante com camadas de `models`, `services`, `core` e `ui`.

## Executando o PDV (tkinter)
1. Instale dependências padrão do Python 3 (apenas sqlite3/tkinter já inclusos).
2. Rode o PDV com:
   ```bash
   python -m ui.pdv
   ```
   Atalhos principais: F1 seleciona mesa, F2–F5 filtram categorias, Enter adiciona item e F9 fecha comanda.

Por padrão, o banco SQLite fica em `~/.restaurante/restaurante.db` (fora do diretório do projeto para não gerar binários no repositório).
Se quiser usar outro caminho, defina as variáveis `RESTAURANTE_DB_PATH`, `RESTAURANTE_DB_DIR` ou `RESTAURANTE_DB_NAME` antes de executar.

## Testes
Execute os testes de regras de negócio com:
```bash
pytest
```

## Limpando arquivos binários locais
Use a verificação auxiliar para garantir que nenhum binário será enviado no PR:
```bash
python tools/check_binaries.py
```
Se o script apontar arquivos rastreados ou não rastreados, siga a orientação exibida para removê-los ou movê-los para fora do repositório.

Se um banco SQLite ou cache local já tiver sido adicionado ao git acidentalmente, remova-o do índice antes de criar o PR (mesmo que tenha ficado dentro do diretório do projeto em execuções anteriores):
```bash
git rm --cached *.db *.sqlite* *.wal *.shm
```
Depois, confirme a remoção para evitar o aviso "Arquivos binários não são compatíveis" nas revisões.
