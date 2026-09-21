const $ = id => document.getElementById(id);
const number = value => new Intl.NumberFormat("pt-BR").format(value);
const money = cents => cents === null ? "—" : "$ " + new Intl.NumberFormat("pt-BR", {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(cents / 100);

const labels = {Internet: "Internet", Reseller: "Revenda", Bikes: "Bicicletas", Components: "Componentes", Clothing: "Vestuário", Accessories: "Acessórios"};
const translateLabel = value => labels[value] || value;
const formatDate = value => value.split("-").reverse().join("/");
const formatMonth = value => value.split("-").reverse().join("/");
const qualityLabels = {
  "Unique primary keys": "chaves primárias únicas",
  "Required foreign keys": "relacionamentos obrigatórios",
  "Valid source dates": "datas de origem válidas",
  "Finite monetary values in cents": "valores monetários válidos em centavos",
  "Discount range": "descontos dentro do intervalo permitido",
  "Positive quantities": "quantidades positivas",
  "Joined row count and amount reconciliation": "conferência de linhas e valores após os relacionamentos"
};
function errorMessage(error) {
  if (error instanceof TypeError) return "Não foi possível conectar ao servidor. Verifique a conexão e tente novamente.";
  if (error instanceof SyntaxError) return "O servidor retornou uma resposta inválida. Tente novamente.";
  return error.message;
}

let metadata;
let currentSnapshot = null;
let providers = [];
let aiBusy = false;
let conversation = [];
let conversationFilters = null;
let conversationVersion = 0;

function clearConversation() {
  conversation = [];
  conversationFilters = null;
  conversationVersion += 1;
  $("answers").replaceChildren();
}

$("new-conversation").addEventListener("click", () => {
  clearConversation();
  $("question").value = "";
  $("ai-status").textContent = "Nova conversa. Faça uma pergunta sobre os dados.";
  $("question").focus();
});
async function request(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Os filtros são inválidos. Revise sua seleção.");
  return data;
}
function svgElement(tag, attributes, text) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attributes).forEach(([key,value]) => element.setAttribute(key, value));
  if (text !== undefined) element.textContent = text;
  return element;
}
function renderTrend(rows) {
  $("trend").replaceChildren();
  $("monthly-table").replaceChildren();
  if (!rows.length) { $("trend").textContent = "Não há vendas nesta seleção."; return; }
  const svg = svgElement("svg", {viewBox: "0 0 660 240", role: "img", "aria-label": "Receita mensal de vendas. Os valores exatos estão disponíveis na tabela abaixo."});
  const max = Math.max(...rows.map(row => row.revenue_cents), 1);
  [0, .5, 1].forEach(fraction => {
    const y = 195 - fraction * 165;
    svg.append(svgElement("line", {x1: 85, x2: 640, y1: y, y2: y, stroke: "var(--grid)"}));
    svg.append(svgElement("text", {x: 75, y: y + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 11}, "$ " + new Intl.NumberFormat("pt-BR", {notation:"compact"}).format(max * fraction / 100)));
  });
  const points = rows.map((row, i) => [rows.length === 1 ? 360 : 90 + i * 540 / (rows.length - 1), 195 - row.revenue_cents / max * 165]);
  svg.append(svgElement("polyline", {points: points.map(point => point.join(",")).join(" "), fill:"none", stroke:"var(--chart)", "stroke-width":3}));
  points.forEach(([x,y], i) => {
    const dot = svgElement("circle", {cx:x,cy:y,r:3,fill:"var(--chart)"});
    dot.append(svgElement("title", {}, formatMonth(rows[i].month) + ": " + money(rows[i].revenue_cents)));
    svg.append(dot);
  });
  svg.append(svgElement("text", {x:90,y:225,fill:"var(--muted)","font-size":12}, formatMonth(rows[0].month)));
  if (rows.length > 1) svg.append(svgElement("text", {x:630,y:225,"text-anchor":"end",fill:"var(--muted)","font-size":12}, formatMonth(rows.at(-1).month)));
  $("trend").append(svg);
  rows.forEach(row => {
    const tr = document.createElement("tr");
    [formatMonth(row.month), money(row.revenue_cents)].forEach(value => {const td=document.createElement("td");td.textContent=value;tr.append(td);});
    $("monthly-table").append(tr);
  });
}
function renderCategories(rows) {
  $("categories").replaceChildren();
  if (!rows.length) {$("categories").textContent="Não há vendas nesta seleção.";return;}
  const max = Math.max(...rows.map(row=>row.revenue_cents),1);
  rows.forEach(row => {
    const item=document.createElement("div");item.className="bar-item";
    const label=document.createElement("div");label.className="bar-label";
    const name=document.createElement("span");name.textContent=translateLabel(row.category);
    const value=document.createElement("strong");value.textContent=money(row.revenue_cents);
    label.append(name,value);
    const track=document.createElement("div");track.className="bar-track";track.setAttribute("aria-hidden","true");
    const fill=document.createElement("div");fill.className="bar-fill";fill.style.width=Math.max(0,row.revenue_cents/max*100)+"%";
    track.append(fill);item.append(label,track);$("categories").append(item);
  });
}
async function refresh() {
  currentSnapshot=null;
  clearConversation();
  updateModels(false);
  $("apply").disabled=true;$("reset").disabled=true;
  $("results").hidden=true;$("status").className="";$("status").textContent="Atualizando resultados…";
  try {
    const parameters=new URLSearchParams();
    for (const [key,value] of new FormData($("filters"))) if(value) parameters.set(key,value);
    const data=await request("/api/dashboard?"+parameters);
    currentSnapshot=data;
    updateModels(false);
    const s=data.summary;
    $("revenue").textContent=money(s.revenue_cents);
    $("orders").textContent=number(s.orders);
    $("average").textContent=money(s.average_order_value_cents);
    $("margin").textContent=s.gross_margin_pct===null ? "—" : new Intl.NumberFormat("pt-BR", {minimumFractionDigits:1, maximumFractionDigits:1}).format(s.gross_margin_pct)+"%";
    renderTrend(data.monthly);renderCategories(data.categories);
    $("observation").textContent=s.line_count
      ? number(s.units)+" unidades em "+number(s.orders)+" pedidos geraram "+money(s.revenue_cents)+" em vendas e "+money(s.gross_profit_cents)+" de resultado bruto."+(data.categories.length ? " A categoria com maior receita nesta seleção é "+translateLabel(data.categories[0].category)+"." : "")
      : "Não há vendas para estes filtros. Tente ampliar o período ou limpar a seleção.";
    $("status").textContent=number(s.line_count)+" itens de venda · "+formatDate($("start").value)+" a "+formatDate($("end").value);
    $("results").hidden=false;
  } catch(error) {$("status").className="error";$("status").textContent=errorMessage(error);}
  finally {$("apply").disabled=false;$("reset").disabled=false;}
}
function reset() {
  $("start").value=metadata.start_date;$("end").value=metadata.end_date;
  $("channel").value="";$("category").value="";
}
$("filters").addEventListener("submit",event=>{event.preventDefault();refresh();});
$("reset").addEventListener("click",()=>{reset();refresh();});
(async()=>{
  $("apply").disabled=true;$("reset").disabled=true;
  try {
    metadata=await request("/api/metadata");
    for (const [id,values] of [["channel",metadata.channels],["category",metadata.categories]]) {
      values.forEach(value=>{const option=document.createElement("option");option.value=value;option.textContent=translateLabel(value);$(id).append(option);});
    }
    $("quality").textContent=number(metadata.quality.row_counts.sales)+" itens de venda carregados. "+number(metadata.quality.missing_ship_dates)+" datas de envio ausentes. Verificações aprovadas: "+metadata.quality.checks.map(check => qualityLabels[check] || "verificação da carga").join("; ")+".";
    reset();await refresh();
  } catch(error) {$("status").className="error";$("status").textContent=errorMessage(error);}
})();

function updateModels(rebuild=true) {
  const provider=providers.find(item=>item.id===$("provider").value);
  if(rebuild) {
    $("model").replaceChildren();
    (provider?.models || []).forEach(model=>{
      const option=document.createElement("option");option.value=model;option.textContent=model;$("model").append(option);
    });
  }
  $("ask").disabled=aiBusy || !currentSnapshot || !provider?.configured || !$("model").value;
  if(!aiBusy) $("ai-status").textContent=provider?.configured
    ? "Pronto. As respostas podem conter erros; confira os indicadores."
    : "Este provedor não está configurado. Adicione a chave e os identificadores dos modelos ao arquivo .env local e reinicie o servidor.";
}
$("provider").addEventListener("change",()=>updateModels());
$("copilot-form").addEventListener("submit",async event=>{
  event.preventDefault();
  if(!currentSnapshot || aiBusy) return;
  const snapshot=currentSnapshot;
  const turnVersion=conversationVersion;
  const question=$("question").value.trim();
  if(!question) {$("ai-status").textContent="Digite uma pergunta.";return;}
  aiBusy=true;$("ask").disabled=true;$("ai-status").textContent="Entendendo a pergunta e preparando a análise…";
  try {
    const response=await fetch("/api/analysis",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({provider:$("provider").value,model:$("model").value,question,...snapshot.filters,history:conversation,analysis_filters:conversationFilters})
    });
    const data=await response.json();
    if(!response.ok) throw new Error(typeof data.detail==="string" ? data.detail : "Revise a pergunta e o modelo selecionado.");
    if(currentSnapshot!==snapshot || turnVersion!==conversationVersion) return;
    const card=document.createElement("article");card.className="answer";
    const title=document.createElement("h3");title.textContent=(providers.find(provider=>provider.id===data.provider)?.label || "Provedor")+" · "+data.model;
    const timing=document.createElement("small");timing.textContent=new Intl.NumberFormat("pt-BR", {minimumFractionDigits:1, maximumFractionDigits:1}).format(data.elapsed_ms/1000)+" s"+(data.context_id ? " · Contexto "+data.context_id : "");
    const asked=document.createElement("p");asked.className="asked";asked.textContent=question;
    const answer=document.createElement("p");answer.className="answer-text";answer.textContent=data.answer;
    const notice=document.createElement("small");notice.textContent=data.notice+(data.truncated ? " A resposta atingiu o limite de tamanho." : "");
    card.append(title, timing, asked, answer, notice);
    if (data.panel) {
      card.append(window.renderOptionalAnalysisPanel(data.panel));
    }
    $("answers").append(card);
    conversation.push(
      {role: "user", content: question},
      {role: "assistant", content: data.answer.slice(0, 4000)},
    );
    conversation = conversation.slice(-8);
    if (data.panel) conversationFilters = data.panel.filters;
    $("question").value = "";
    card.scrollIntoView({block: "nearest", behavior: "smooth"});
    $("ai-status").textContent = data.status === "partial"
      ? "Painel calculado; a explicação da IA não ficou disponível."
      : "Análise recebida. Você pode fazer outra pergunta ou comparar com outro modelo.";
  } catch(error) {if(currentSnapshot===snapshot && turnVersion===conversationVersion) $("ai-status").textContent=errorMessage(error);}
  finally {aiBusy=false;$("ask").disabled=!currentSnapshot || !providers.find(item=>item.id===$("provider").value)?.configured;}
});
(async()=>{
  try {
    const data=await request("/api/providers");providers=data.providers;
    providers.forEach(provider=>{
      const option=document.createElement("option");option.value=provider.id;
      option.textContent=provider.label+(provider.configured ? "" : " · não configurado");
      $("provider").append(option);
    });
    const available=providers.find(provider=>provider.configured);
    if(available) $("provider").value=available.id;
    updateModels();
  } catch(error) {$("ai-status").textContent="Não foi possível carregar a configuração dos provedores: "+errorMessage(error);}
})();
