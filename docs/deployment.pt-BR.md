# Demo na Vercel

## Passo a passo atualizado — 21/10/2026

Login por e-mail e análise pela Groq foram confirmados localmente pelo usuário. Gemini ainda apresentou falha no navegador. A seleção Groq/Gemini foi conferida no Chrome sem consumir perguntas. O deploy remoto ainda precisa ser validado.

1. Na conta pessoal Hobby da Vercel, escolha **Add New → Project** e importe `Renanmrqs/DataPilot`, branch `main`.
2. Mantenha **Root Directory** na raiz (`./`). Use o preset **FastAPI**, se oferecido pela detecção. Não selecione React/Vite.
3. Mantenha os comandos automáticos. O `pyproject.toml` aponta para `src.api.main:app` e executa `python -m src.etl.build_database` no build. Se precisar preencher **Build Command**, use esse comando. Não configure uma saída `dist`.
4. Preencha as variáveis abaixo em **Environment Variables → Production**, antes de clicar em **Deploy**. Copie os valores privados diretamente do `.env` local; não os publique em prints, mensagens ou commits.

| Nome | Valor/origem |
| --- | --- |
| `NEON_AUTH_BASE_URL` | Mesmo valor do `.env` local |
| `NEON_DATABASE_URL` | Mesma conexão PostgreSQL do `.env` local |
| `DEEPSEEK_BASE_URL` | Mesmo endpoint local da Groq |
| `DEEPSEEK_API_KEY` | Mesma chave privada da Groq |
| `DEEPSEEK_MODELS` | Mesmo identificador Qwen do `.env` local |
| `DEMO_PROVIDER` | `deepseek` (identificador interno; aparece como Groq) |
| `DEMO_MODEL` | Identificador Qwen incluído em `DEEPSEEK_MODELS` |
| `DEMO_QUESTIONS_PER_USER` | `4` |
| `DEMO_DAILY_QUESTIONS` | `20` |
| `DEMO_COOLDOWN_SECONDS` | `15` |
| `DEMO_AI_ENABLED` | `true` |

Para também oferecer Gemini, adicione `GEMINI_API_KEY` com a chave local, `GEMINI_MODELS=gemini-2.5-flash`, `DEMO_ALTERNATE_PROVIDER=gemini` e `DEMO_ALTERNATE_MODEL=gemini-2.5-flash`. Ambos compartilham as cotas; trocar de provedor não renova perguntas.

`VERCEL=1` é fornecida pela plataforma e obriga o modo protegido. Não precisa copiar senha SMTP: ela continua configurada no Neon Auth. O SQLite é gerado durante o build e consultado somente para leitura; os usuários e saldos continuam persistentes no Neon.

### Depois do deploy

1. Copie a URL de produção, como `https://seu-projeto.vercel.app`.
2. No Neon, abra **Settings → Better Auth → Domains** e adicione essa origem HTTPS exata, sem `/api/auth/callback` ou `/#assistant`.
3. Abra o site publicado. Confira painel, filtros e seletores na seção Assistente.
4. Solicite um link de acesso pelo site publicado e abra no mesmo navegador. A sessão local não é transferida para o domínio publicado.
5. Confira o saldo, envie uma pergunta e recarregue para confirmar a persistência. A pergunta real consome saldo.

Não precisa comprar domínio. URLs de preview são origens diferentes e não estão automaticamente autorizadas no Neon. Após alterar variáveis, faça um novo deploy.

Se o build falhar, confira **Build Logs**. Se `/api/metadata` retornar 503, precisamos verificar a inclusão do SQLite no pacote remoto. Para falhas de login/IA, confira **Runtime Logs** e compartilhe apenas status e categorias seguras, sem tokens ou credenciais.

O plano Hobby atende projetos pessoais não comerciais e tem limites. As franquias da Vercel, Neon e provedores são independentes. Ainda falta validar o build e o fluxo completo no domínio publicado antes de divulgar a demo.

Referências oficiais: [FastAPI](https://vercel.com/docs/frameworks/backend/fastapi), [guia de publicação](https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel), [limites de Functions](https://vercel.com/docs/functions/limitations) e [Hobby](https://vercel.com/docs/plans/hobby).

## Registro anterior (histórico)

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
