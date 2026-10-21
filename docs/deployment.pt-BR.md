# Demo na Vercel

Status: configuração de hospedagem e controle de cotas implementados; deploy na Vercel e login real por e-mail ainda não validados. Veja o [guia completo de acesso, configuração e aprendizado](demo-access.pt-BR.md).

## O que mudou

- `pyproject.toml` aponta a Vercel para `src.api.main:app`, a aplicação usada localmente.
- O build executa `python -m src.etl.build_database` para gerar o SQLite a partir dos CSVs versionados, antes de servir requisições.
- O SQLite continua somente leitura. As cotas ficam no PostgreSQL do Neon.
- `src/api/deployment.py` exige identidade confirmada e reserva de saldo nas duas rotas de IA. `DEMO_AI_ENABLED=false` mantém a IA pausada mesmo com credenciais.
- O painel permanece disponível. A interface apresenta login por e-mail, saldo e estados de limite, pausa e falha.

## Como conferir

Execute `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v`. Os testes de deploy simulam a variável da Vercel e verificam o bloqueio antes de consultar dados ou chamar provedores.

A configuração segue https://vercel.com/docs/frameworks/backend/fastapi . O build remoto ainda precisa confirmar inclusão do SQLite e dos arquivos estáticos, instalação das dependências e funcionamento dos endpoints.

## Próximo incremento

Configurar e testar o envio real de e-mails, conferir a sessão nos navegadores, preparar variáveis na Vercel e validar o build remoto. Duas perguntas não equivalem necessariamente a duas chamadas de IA: há planejamento, explicação e possíveis novas tentativas.
