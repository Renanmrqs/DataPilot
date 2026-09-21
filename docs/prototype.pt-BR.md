# Guia do protótipo DataPilot

[English version](prototype.md) · [Visão geral do projeto](../readme.MD)

## O que estamos construindo

Um produto com duas partes conectadas: **um portal de análise fora do BI e um assistente para perguntas sobre o negócio**.

O portal já mostra indicadores e gráficos. No assistente, você faz uma pergunta, como “por que o ticket médio está alto?”, e a IA escolhe um conjunto de indicadores e gráficos relacionados. Você não precisa pedir um gráfico específico.

Hoje existem quatro tipos de análise: vendas, ticket médio, margem bruta e produtos. Os gráficos seguem modelos predefinidos. Ainda não há geração livre de qualquer dashboard nem memória entre perguntas.

É um protótipo local para aprendizado e portfólio. As visualizações ainda precisam de refinamento; não é uma versão pronta para clientes.

## Como iniciar

Na pasta do projeto, abra o PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.etl.build_database
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
```

- Crie a pasta `.venv` somente se ela ainda não existir.
- O segundo comando instala as dependências.
- O terceiro valida os CSVs originais e monta o banco SQLite.
- O quarto inicia o servidor.

Abra http://127.0.0.1:8000. A documentação da API fica em http://127.0.0.1:8000/docs.

Para parar, use **Ctrl+C** no terminal do servidor. Pare o servidor antes de reconstruir o banco, para evitar bloqueios de arquivo no Windows.

No uso diário, com as dependências e o banco já preparados, basta iniciar o servidor. O carregamento atual lê os CSVs originais diretamente; não depende do antigo CSV processado.

## Como configurar a IA

1. Copie `.env.example` para `.env`, se ainda não tiver esse arquivo.
2. Preencha a chave e os modelos do provedor que quer testar.
3. Reinicie o servidor.
4. Selecione o provedor e o modelo na interface.

Exemplo com valores fictícios:

```dotenv
GEMINI_API_KEY=sua_chave_aqui
GEMINI_MODELS=id_do_modelo
```

Use o identificador exato de um modelo disponível na sua conta. Para listar mais de um, separe por vírgulas. A aplicação não busca essa lista automaticamente.

Gemini, DeepSeek e OpenAI possuem endereços predefinidos. Para outro serviço compatível com Chat Completions, configure `COMPATIBLE_BASE_URL`, `COMPATIBLE_API_KEY` e `COMPATIBLE_MODELS`. Compatibilidade depende do provedor e do modelo.

A chave fica no servidor. Não coloque a chave no HTML e não envie o arquivo `.env` para o GitHub. O painel de dados funciona sem IA configurada.

Uma pergunta suportada normalmente usa duas etapas de IA: escolher o plano e explicar os resultados. Algumas falhas temporárias permitem uma nova tentativa por etapa, chegando a quatro chamadas. Respostas de limite atingido não são repetidas automaticamente. Custos e cotas dependem da sua conta.

## O que acontece depois da pergunta

1. A IA interpreta a pergunta e propõe um plano dentro das opções permitidas.
2. O servidor valida esse plano.
3. SQL e Python calculam os indicadores e os valores dos gráficos.
4. A IA recebe os resultados para escrever uma explicação.
5. A interface apresenta a resposta e o painel relacionado.

A IA não escreve nem executa SQL livremente. Se a explicação falhar, o painel calculado continua disponível e a interface avisa que a resposta ficou incompleta.

Os dados enviados ao provedor incluem a pergunta, filtros, definições e valores agregados necessários à análise. Não são enviados os CSVs completos, as chaves de API ou os documentos de planejamento.

## Como testar e comparar

- Confira os totais sem filtros.
- Mude período, canal ou categoria e confira a seleção.
- Faça uma pergunta sobre vendas, ticket, margem ou produtos.
- Confira os filtros interpretados e os valores exibidos no painel.
- Use “Ver valores” para comparar o gráfico com os números.
- Repita a mesma pergunta com outro modelo, mantendo os filtros.
- Veja se a explicação respeita os números e reconhece quando faltam dados.

Trocar filtros limpa resultados anteriores. Recarregar a página também limpa as respostas. As perguntas são independentes: o assistente ainda não acompanha uma conversa com memória.

## Como os números são calculados

| Indicador | Cálculo |
|---|---|
| Receita | Soma do valor de venda registrado na fonte |
| Pedidos | Contagem distinta dos pedidos entre os itens selecionados |
| Unidades | Soma das quantidades |
| Ticket médio | Receita selecionada / pedidos distintos selecionados |
| Lucro bruto | Receita menos custo dos produtos |
| Margem bruta | Lucro bruto / receita × 100 |

Um pedido pode ter várias linhas. Por isso, contar linhas não equivale a contar pedidos.

Ao filtrar uma categoria, o ticket considera somente os itens selecionados, não o valor completo de cada pedido. Lucro bruto não é lucro líquido: não temos todas as despesas e impostos. A fonte usa o símbolo de dólar, mas o código da moeda não foi confirmado.

Divisões por zero aparecem sem valor, representadas por um traço. Os gráficos mensais mostram meses presentes nos dados; filtros podem deixar o primeiro ou o último mês incompleto.

## Banco e validação

O caminho dos dados é: **CSVs → validação em Python → SQLite → API → interface**.

Cada linha de venda representa um item do pedido. O banco relaciona esse item a produto, cliente, revendedor, território e detalhes do pedido. SKU não é chave única na fonte. Chaves de cliente e revendedor com valor `-1` são preservadas sem inventar seu significado.

Valores monetários são armazenados em centavos inteiros. O carregamento verifica chaves, relacionamentos, datas, quantidades e totais. Se falhar, não substitui o banco anterior por um banco incompleto.

Totais de referência da base atual:

| Informação | Valor |
|---|---|
| Itens de venda | 121.253 |
| Pedidos distintos | 31.455 |
| Unidades | 274.776 |
| Receita | 109.809.274,00 |
| Custo dos produtos | 97.257.988,07 |
| Lucro bruto | 12.551.285,93 |
| Margem bruta | Aproximadamente 11,4301% |
| Período dos pedidos | 01/07/2021 a 15/06/2024 |

Há 2.113 datas de envio ausentes, preservadas. O relatório do carregamento fica no banco e pode ser consultado em `/api/metadata`.

Para executar os testes:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Os testes verificam cálculos conhecidos, filtros, restrições do banco e falhas de IA simuladas. A interface também passou por verificações no navegador, incluindo tela estreita e os quatro tipos de painel com respostas simuladas.

Uma análise real com Gemini terminou após recuperar uma falha temporária HTTP 503. Isso confirma aquele fluxo, mas não garante disponibilidade do serviço nem qualidade de toda resposta.

## Onde fica cada parte do código

| Pasta ou arquivo | Responsabilidade |
|---|---|
| `src/etl/build_database.py` | Validar e carregar os dados |
| `sql/schema.sql` | Definir tabelas e relacionamentos |
| `src/api/` | Receber as requisições e coordenar a análise |
| `src/analytics/` | Calcular métricas e montar dados dos painéis |
| `src/ai/` | Conversar com provedores e validar o plano |
| `src/web/` | Exibir interface, respostas e gráficos |
| `tests/` | Verificar comportamentos esperados |

Para entender o fluxo, comece por uma pergunta na interface e acompanhe `src/api/analysis.py`. Não precisa ler o projeto inteiro de uma vez.

## Limites e próximos passos

- A base suporta análises relacionadas a vendas, não todas as áreas da empresa.
- A IA pode interpretar a pergunta errado ou inventar uma causa. Confira a resposta com os dados.
- Não há filtros por produto nem comparação calculada com período anterior.
- Não há autenticação ou configuração para produção. O SQLite atende ao protótipo local; PostgreSQL é uma evolução planejada.
- A prioridade seguinte é melhorar legibilidade dos gráficos, rótulos, espaçamento e organização visual.
- Depois, refinar como pergunta, resposta e painel aparecem juntos e comparar modelos com perguntas representativas.

A evolução será feita em etapas pequenas, com explicação do que mudou e uma forma simples de conferir o resultado.
