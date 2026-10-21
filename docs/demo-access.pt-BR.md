# Entendendo o acesso e as quatro perguntas da demo

**Estado final da sessão:** o usuário confirmou o login, mas relatou que a IA ainda não funciona. A tentativa real de diagnóstico do planejamento não valida o fluxo completo. Retome pelo [checkpoint de 20/10/2026](checkpoint-2026-10-20.md), que registra o problema em aberto e o próximo passo.

## Resultado desta etapa

A interface de acesso por e-mail, o saldo de perguntas e o controle por usuário foram implementados. O Neon já tem as tabelas de cotas. O login real ainda precisa ser conferido com o envio de e-mail configurado; o deploy da Vercel também continua pendente. A IA pública permanece pausada por padrão.

Na interface, usamos **perguntas disponíveis**, não tokens. Tokens são unidades de texto processadas pelo modelo. Uma pergunta pode consumir duas chamadas: planejamento e explicação. Tentativas extras do adaptador podem aumentar isso para quatro chamadas.

## Como abrir e conferir o visual

Pare o servidor local com Ctrl+C se ele estiver usando a porta 8000. Na raiz do projeto:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.run_demo
```

Abra http://127.0.0.1:8000/#assistant . Esse comando ativa o modo demo somente naquele processo. Não altera seu `.env`. Se quiser manter o servidor anterior, use `-m scripts.run_demo --port 8001` e abra a porta 8001.

O saldo inicial aparece como “4 perguntas por conta”. Depois de confirmar o e-mail e consultar o banco, a tela passa a mostrar o saldo real, por exemplo “3 de 4 perguntas disponíveis”. O botão de envio só é liberado quando o servidor confirma todas as condições.

O modo local anterior continua disponível com o comando normal do Uvicorn. Na Vercel, a proteção é obrigatória, independentemente de `DEMO_MODE=false`.

## Caminho completo de uma pergunta

1. `demo-access.js` consulta `/api/demo/access`, que informa o modo, a rota local `/api/auth`, o modelo público e o limite padrão. A senha do banco e as chaves de IA nunca fazem parte dessa resposta.
2. Para entrar, o visitante informa o e-mail. O navegador chama nossa API, que pede ao Neon Auth um magic link. O cookie de desafio é guardado no domínio do DataPilot, com `HttpOnly` e `SameSite=Lax`.
3. O visitante abre o link recebido. O Neon verifica o link e retorna um código temporário para `/api/auth/callback`. Nossa API envia esse código e o desafio original a `/get-session` no Neon. Essa troca é necessária para concluir a sessão. O cookie resultante fica no domínio do DataPilot; o navegador é redirecionado para `/#assistant`, sem o código na URL.
4. O navegador consulta `/api/auth/token`. Nossa API encaminha o cookie de sessão ao Neon e retorna somente o JWT necessário para identificar o usuário. Nosso JavaScript o mantém apenas em memória, sem `localStorage`. O cookie opaco da sessão é `HttpOnly`, não fica disponível ao JavaScript e só é enviado às rotas `/api/auth`.
5. Ao consultar o saldo ou fazer uma análise, o navegador envia essa credencial no cabeçalho `Authorization: Bearer ...`.
6. `src/demo/auth.py` verifica assinatura, validade, emissor, destinatário e confirmação de e-mail. O identificador da conta vem do token validado; o navegador não escolhe um `user_id` no corpo da requisição.
7. O servidor valida pergunta, filtros e modelo. Antes da primeira chamada à IA, reserva uma pergunta no PostgreSQL.
8. Só depois da reserva o fluxo anterior de planejamento, cálculo e explicação é executado.
9. Ao terminar ou receber erro, a interface consulta o saldo novamente. Ela não tenta manter uma contagem própria.

Ao voltar de outra aba, a página também consulta a sessão automaticamente. O botão de atualização indica a consulta e avisa quando não encontra a sessão nesse navegador. Todas as chamadas de autenticação feitas pelo JavaScript ficam no domínio da aplicação.

O painel de vendas continua consultando SQLite. O PostgreSQL do Neon guarda o acesso e as cotas, não uma cópia das vendas.

## O que cada arquivo faz

| Arquivo | Responsabilidade e motivo |
|---|---|
| `src/web/demo-access.js` | Solicitar link, restaurar sessão, consultar saldo, sair e atualizar a interface. Separado de `app.js` para não misturar autenticação com gráficos. |
| `src/web/demo-access.css` | Estilo do cartão de acesso, barra de saldo e adaptação para celular e temas. |
| `src/web/index.html` | Elementos visíveis de e-mail, saldo, avisos e ações. Os scripts novos carregam antes de `app.js`. |
| `src/web/app.js` | Enviar a credencial com a pergunta e consultar o saldo após a tentativa, inclusive em falhas. |
| `src/api/demo.py` | Rota de consulta de acesso e saldo; respostas pessoais usam `Cache-Control: no-store`. |
| `src/api/auth.py` | Solicita o link, conclui a troca de retorno e encaminha token/logout ao Neon com cookies no domínio do DataPilot. Verifica a origem dos POSTs, fixa a URL de retorno e remove códigos temporários dos logs de acesso. |
| `src/api/deployment.py` | Verificação comum às duas rotas de IA, pausa global, identidade e seleção de modelo público. Substitui o bloqueio temporário absoluto da primeira etapa. |
| `src/api/analysis.py` | Reserva uma pergunta depois de validar filtros e antes de planejar com IA. |
| `src/api/main.py` | Registra a rota de acesso, restringe o catálogo público e protege também `/api/copilot`, a rota antiga. |
| `src/demo/config.py` | Lê configurações do servidor e rejeita limites inválidos. |
| `src/demo/auth.py` | Valida a identidade por JWT usando as chaves públicas do Neon, com cache das chaves. |
| `src/demo/quota.py` | Consulta e reserva saldos em transações curtas no PostgreSQL. |
| `sql/demo_schema.sql` | Define contas e consumo diário em um schema separado das tabelas de autenticação. |
| `src/demo/setup_database.py` | Cria as tabelas explicitamente; não roda em cada visita. É seguro repetir a criação prevista no script. |
| `scripts/run_demo.py` | Inicia o modo demo local sem alterar o perfil anterior. |
| `scripts/check_demo_ui.py` | Testa o navegador com login, e-mail e respostas de IA simulados. |
| `scripts/check_auth_flow.py` | Testa navegador, API real local, cookies reais, troca obrigatória do retorno e JWT assinado, usando somente o serviço Neon simulado. |
| `requirements.txt` | Registra o driver PostgreSQL e a biblioteca de validação JWT com criptografia. |
| `.env.example` | Lista as configurações sem incluir segredos. |
| `pyproject.toml` | Configuração anterior de entrada FastAPI e geração do SQLite durante o build da Vercel. |

## Por que a contagem é feita numa transação

Imagine que o usuário tem uma pergunta restante e envia duas requisições quase ao mesmo tempo. Se ambas apenas lessem o saldo e depois o atualizassem, poderiam passar juntas.

`reserve()` bloqueia primeiro a linha do dia e depois a linha da conta com `SELECT ... FOR UPDATE`. A segunda requisição espera a primeira terminar. Então enxerga o saldo atualizado e é rejeitada. Os contadores da conta e do dia são atualizados juntos: se algo falha antes do commit, as mudanças são revertidas.

A transação termina **antes** da chamada ao modelo. Não seguramos o banco bloqueado enquanto esperamos a IA.

O pool do Neon não aceita `search_path` entre as opções de abertura da conexão. Por isso, usamos `SET LOCAL` dentro da transação para escolher nosso schema e definir tempos máximos de consulta e espera. Essas opções terminam com a transação e não passam para o próximo usuário da conexão em pool.

## Regras de consumo escolhidas

O limite foi aumentado de duas para quatro perguntas por solicitação do usuário. A configuração local está usando Gemini (`gemini-3.8-flash`) com a IA habilitada para testes. O consumo existente foi preservado: uma tentativa já registrada deixa três perguntas restantes. O cartão agora identifica o provedor para evitar dúvida sobre qual IA está em uso.

Uma chamada real de diagnóstico produziu um plano válido de ticket médio, após uma falha temporária do serviço e a nova tentativa já prevista no adaptador. A resposta inválida anterior não foi reproduzida. Acrescentamos ao log somente as categorias de erro de validação e a indicação de truncamento, sem registrar pergunta, resposta ou credenciais, para investigar uma eventual repetição.

- O padrão é **quatro perguntas por conta, no total**, não quatro por dia.
- Nova conversa, reload, trocar filtros, sair e entrar não reiniciam a cota.
- O teto global inicial é **20 perguntas reservadas por dia UTC**, compartilhado entre os usuários. É uma configuração inicial, não uma estimativa da sua cota nos provedores.
- Há um intervalo de **15 segundos por conta** entre reservas.
- Perguntas que chegam à etapa de IA contam mesmo quando a explicação falha, o provedor recusa ou a pergunta exige esclarecimento. Pode já ter ocorrido consumo externo; não há reembolso automático.
- Erros de validação de filtros, modelo público inválido e solicitações sem identidade válida são rejeitados antes da reserva.
- Se o banco não conseguir confirmar ou reservar o saldo, a API não chama o provedor.
- Uma reserva concluída também pode ser consumida se o processo cair antes de chamar o modelo. A escolha conservadora protege a cota; não é um sistema de cobrança financeira.
- A rota antiga `/api/copilot` compartilha a mesma cota.

## Configuração do servidor

Acrescente estes nomes ao `.env` conforme o exemplo versionado. Preserve as credenciais já preenchidas:

```dotenv
DEMO_MODE=false
DEMO_AI_ENABLED=false
DEMO_QUESTIONS_PER_USER=4
DEMO_DAILY_QUESTIONS=20
DEMO_COOLDOWN_SECONDS=15
DEMO_PROVIDER=gemini
DEMO_MODEL=identificador_exato_configurado_na_sua_conta
```

`DEMO_PROVIDER` deve ser um dos adaptadores existentes: `gemini`, `deepseek`, `openai` ou `compatible`. `DEMO_MODEL` precisa estar na lista de modelos do mesmo provedor. Na demo, o usuário não escolhe um modelo privado diferente; na API essa seleção também é verificada.

Nesta sessão, os valores ausentes foram acrescentados ao `.env` local, sem substituir configurações existentes. O provedor/modelo público foi escolhido entre os já configurados, priorizando Gemini. A IA continua desativada na demo; nenhuma chamada real foi feita para avaliar esse modelo nesta etapa.

`DEMO_AI_ENABLED=false` é a chave para pausar o chat. No perfil de demonstração, ela prevalece mesmo com credenciais válidas. Deixe assim até testar o login real e os limites. As variáveis `NEON_AUTH_BASE_URL` e `NEON_DATABASE_URL` já estão configuradas localmente; não publique seus valores.

Para repetir a preparação do schema em outro banco:

```powershell
.\.venv\Scripts\python.exe -B -m src.demo.setup_database
```

Essa etapa já foi executada no Neon configurado nesta sessão. Não altera as tabelas gerenciadas pelo Neon Auth.

## Ajustar um usuário específico

O padrão vem de `DEMO_QUESTIONS_PER_USER`. A coluna opcional `question_limit` substitui esse valor somente para aquela conta. Não existe endpoint público para alterar isso.

No SQL Editor do Neon, veja os identificadores e o consumo:

```sql
SELECT user_id, used_questions, question_limit, last_question_at
FROM datapilot_demo.accounts;
```

Exemplo para conceder cinco perguntas totais a uma conta que já usou duas: ela passa a ter três restantes.

```sql
UPDATE datapilot_demo.accounts
SET question_limit = 5
WHERE user_id = 'identificador_real_da_conta';
```

Use `NULL` para voltar ao limite padrão ou `0` para bloquear novas perguntas da conta. O limite global continua valendo. As linhas são criadas na primeira reserva, não simplesmente ao digitar um e-mail.

## Configurar e testar e-mail quando voltar

1. Use uma conta de e-mail dedicada ao projeto, se possível. Com Gmail, habilite verificação em duas etapas e procure a opção de senha de app; a disponibilidade depende das configurações da conta.
2. No Neon, em Settings → Better Auth → Custom SMTP, configure `smtp.gmail.com`, porta `465` com SSL, usuário igual ao endereço completo e senha de app. O remetente deve ser o mesmo endereço. Não use a senha normal nem envie essa credencial para o código ou GitHub.
3. Configure o nome DataPilot, Magic Link, cadastro de novos usuários e os endereços permitidos de desenvolvimento no Neon. Use sempre o mesmo host durante o teste: `localhost` e `127.0.0.1` são origens diferentes.
4. Abra o modo demo, informe seu e-mail e solicite um link. Confira também o spam. Esta etapa é manual: nenhum e-mail real foi enviado pelos testes. Após a correção do callback, solicite um link novo: os antigos apontam para o retorno anterior e não têm o novo cookie de desafio na aplicação.
5. Abra o link, volte ao site e clique em “Já confirmei / atualizar saldo” caso necessário. A tela precisa mostrar a conta confirmada e o saldo retornado pela API. Não basta receber o e-mail.
6. Só depois configure o modelo público e habilite `DEMO_AI_ENABLED=true` para uma avaliação controlada. Reinicie o servidor após mudar o `.env`.
7. Na Vercel, adicione o endereço exato `https://seu-projeto.vercel.app` como origem confiável no Neon. Cadastre as variáveis no ambiente da Vercel. Teste a versão hospedada antes de divulgar.

O endereço gratuito `vercel.app` pode ser usado pelo site. Não precisamos comprar domínio para testar com um remetente Gmail. A conta de envio tem seus próprios limites e a entrega precisa ser validada.

## Limites que ainda precisam de avaliação real

- A integração foi corrigida para manter as chamadas de autenticação e os cookies no domínio da aplicação. Em HTTPS, os cookies têm `Secure`; a exceção sem `Secure` existe para o servidor HTTP local. Não é necessário habilitar cookies de terceiros para esse fluxo.
- Duas contas de e-mail podem pertencer à mesma pessoa. O teto global reduz o consumo máximo da demo, mas alguém ainda pode esgotar a parcela diária disponibilizada.
- O intervalo de reenvio de e-mail na interface melhora a experiência, mas não é uma proteção de servidor contra automação. É necessário conferir os limites do próprio Auth/SMTP e configurar a proteção de tráfego no ambiente público antes de divulgar.
- Não há limitação própria por IP, CAPTCHA ou sistema de detecção de fraude implementado. Esses mecanismos não devem ser confundidos com o controle de cotas por conta.
- O JWT precisa ser renovado pelo Neon. A aplicação valida assinatura e expiração; revogação de sessão pode levar até a expiração de uma credencial JWT já emitida.
- As novas tabelas não guardam perguntas, respostas ou e-mails; guardam identificador, consumo e datas. O serviço de autenticação gerencia os dados de login.
- O teto mede perguntas, não tokens nem chamadas reais. A franquia gratuita pode acabar por limites de tokens, minuto ou dia do provedor antes do teto da demo.
- O usuário confirmou o recebimento real do e-mail. O deploy remoto e o login real após a correção do callback ainda precisam ser homologados.

## Como verificar e o que a evidência significa

Suíte padrão, sem e-mails ou chamadas reais a modelos:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

`test_demo.py` testa credenciais assinadas, expiração, emissor, destinatário, e-mail confirmado, modo pausado, erro de banco, seleção de modelo e proteção das duas rotas.

`test_demo_postgres.py` é opt-in e usa um schema exclusivo, removido no final. Verifica duas reservas e bloqueio da terceira, persistência entre conexões, concorrência pela última pergunta, teto diário, intervalo, override individual e rollback. Não usa contas reais nem altera cotas reais.

```powershell
$env:DATAPILOT_TEST_NEON = "1"
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_demo_postgres.py -v
Remove-Item Env:DATAPILOT_TEST_NEON
```

Com o servidor local iniciado, o teste de interface usa Playwright e o Chrome instalado. Playwright é uma ferramenta opcional de desenvolvimento, não uma dependência do servidor publicado:

```powershell
.\.venv\Scripts\python.exe -B scripts/check_demo_ui.py
```

Ele simula login e IA, confere saldo, falha de chamada, reload, nova conversa, pausa, teto diário, erro de saldo, logout e largura de celular. As capturas ficam na pasta temporária `datapilot-demo-preview`. Essa simulação não comprova entrega de e-mail, cookies reais ou disponibilidade do modelo.

Resultados após a correção do callback: 60 testes da suíte padrão passaram, com três testes de PostgreSQL ignorados por serem opt-in. Os três testes de PostgreSQL foram executados separadamente na etapa de cotas e passaram; a correção de autenticação não alterou essa lógica. A verificação automatizada da interface passou em desktop, celular e tema escuro. As capturas usam uma conta e respostas simuladas.

Para testar o ciclo completo de autenticação, sem enviar e-mails reais:

```powershell
.\.venv\Scripts\python.exe -B -m scripts.check_auth_flow
```

Esse teste inicia e encerra seu próprio servidor temporário. O navegador usa cookies reais da aplicação; o Neon simulado só emite sessão se receber o código de retorno junto do desafio original. Um JWT assinado é validado pela API antes de mostrar a conta e o saldo. O teste também verifica persistência após reload, logout e rejeição do mesmo código após uso.

## Correção do retorno do e-mail

O primeiro fluxo ignorava `neon_auth_session_verifier`, o código temporário devolvido pelo Neon. A página chamava `/token` antes de concluir a troca em `/get-session`. Assim, o e-mail podia ser confirmado no Neon e a aplicação continuar tratando o navegador como visitante. Os primeiros testes de interface simulavam uma sessão pronta e não detectaram essa etapa ausente.

A correção acrescentou o retorno em `/api/auth/callback` e o encaminhamento de autenticação pela API. Os cookies do Neon são remapeados para cookies da aplicação, sem o atributo `Partitioned` e sem domínio externo. O serviço continua validando o desafio e a sessão; a aplicação não inventa um usuário nem aceita e-mail como prova de identidade. POSTs de outra origem e destinos arbitrários de retorno são rejeitados. Códigos de retorno não são gravados nos logs padrão de acesso do Uvicorn.

## Roteiro para entender o código em ordem

1. Abra `demo-access.js` e acompanhe `refresh()` → `loadAccess()` → `render()`. Veja qual parte consulta o servidor e qual apenas escreve na tela.
2. Veja `/api/demo/access` em `src/api/demo.py`. Compare a resposta anônima com os estados `ready`, `paused` e `exhausted`.
3. Veja `verified_user()` em `src/demo/auth.py`. Identifique por que apenas ler o texto de um JWT sem verificar assinatura seria insuficiente.
4. Em `src/api/analysis.py`, localize `access.reserve(...)` antes de `select_analysis(...)`. Esse posicionamento protege sua cota.
5. Em `QuotaStore.reserve()`, acompanhe a ordem: bloquear dia → bloquear conta → validar limites → incrementar ambos → commit.
6. Compare com os testes e escolha um caso: duas requisições pela última pergunta. A regra correta é uma aceita e as demais rejeitadas, com consumo final igual ao limite.

## Fontes técnicas

- [Neon: Magic Link](https://neon.com/docs/auth/guides/plugins/magic-link)
- [Neon: JWT e verificação de assinatura](https://neon.com/docs/auth/guides/plugins/jwt)
- [Neon: preparação para produção e SMTP](https://neon.com/docs/auth/production-checklist)
- [Google: senhas de app](https://support.google.com/accounts/answer/185833)
- [Vercel: FastAPI](https://vercel.com/docs/frameworks/backend/fastapi)
