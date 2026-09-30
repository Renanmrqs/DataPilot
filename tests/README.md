# Testes e validação do DataPilot

Execute na raiz, com as dependências instaladas:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Os testes usam bases temporárias e respostas simuladas de provedores. Não exigem chave de IA, não chamam modelos reais e não substituem o banco local em uso.

| Arquivo | Cobertura |
|---|---|
| `test_prototype.py` | Conversão de dinheiro e datas, restrições, métricas, filtros, seleções vazias, API e arquivos estáticos |
| `test_copilot.py` | Configuração dos provedores, contexto calculado no servidor, erros, limites, novas tentativas e respostas truncadas |
| `test_analysis.py` | Planos permitidos, cálculos, rankings, histórico, mudança de categoria e preservação do painel quando a explicação falha |

## Regressões dos exemplos aprovados em 30/09/2026

- `test_margin_bikes_accessories_conversation_recalculates_each_selection`: percorre margem → bicicletas → acessórios pela API, mantendo datas e histórico e recalculando métricas. Usa valores pequenos independentes, incluindo pedido com itens de categorias diferentes. O planejador é simulado: não mede a capacidade de um modelo entender a pergunta.
- `test_partial_chartless_result_preserves_calculated_kpis`: uma falha na explicação não remove indicadores calculados quando não há gráficos. Verifica o retorno da API, não a renderização no navegador.
- Casos já existentes verificam “e por mês?”, texto histórico incorreto, rankings por unidades e filtros explícitos.

O [checkup](../docs/checkup-2026-09-30.md) registra a execução e distingue testes, consulta dos valores locais e exemplos reais relatados pelo usuário. Os totais da base de demonstração são referências dessa base, não valores esperados para futuros clientes.

## Roteiro manual

1. Abrir o portal e conferir os totais e o período de 01/07/2021 a 15/06/2024.
2. Iniciar conversa, pedir a fórmula da margem e conferir receita, custo, lucro bruto e percentual.
3. Pedir detalhes de bicicletas; verificar categoria, período, ticket dos itens selecionados e valores dos gráficos.
4. Perguntar sobre acessórios; verificar que a categoria muda e os números são recalculados.
5. Pedir “e por mês?”; conferir a seleção mantida, os valores e a identificação de junho/2024 parcial.
6. Abrir/fechar gráficos, conferir tabelas de valores e repetir em tela estreita.
7. Conferir que indicadores sem gráficos aparecem diretamente; respostas sem indicadores nem gráficos não mostram botão vazio.
8. Usar “Nova conversa”, alterar filtros e recarregar; conferir a limpeza do histórico.

Não exigir texto literal da IA. Conferir números, filtros, definições e limites das conclusões. Variação mensal não prova sazonalidade; receita baixa precisa de referência de comparação. Chamadas reais podem consumir créditos e não fazem parte da suíte automatizada.

## Testes futuros da reutilização

Ainda não há suporte QVD ou configuração por cliente para testar. Ao implementá-los, cobrir:

- Duas bases já tratadas com campos diferentes e resultados conhecidos, usando o mesmo contrato de painel.
- Mapeamentos inválidos, tipos, precisão monetária, chaves, granularidade e junções que poderiam duplicar valores.
- Paridade com medidas do aplicativo Qlik sob os mesmos filtros.
- Atualização consistente e recuperação de falha de leitura.
- Separação de dados, caches e histórico por cliente antes de uso compartilhado.
- Tempo e memória com volumes representativos; definir metas antes de escolher armazenamento.

Não remover as regressões CSV/SQLite enquanto a implementação atual depender desse caminho. PostgreSQL não é requisito de aceitação.
