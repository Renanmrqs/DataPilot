// Render only server-calculated values. Model-generated HTML is never executed.
(() => {
  const labels = {
    Internet: "Internet",
    Reseller: "Revenda",
    Bikes: "Bicicletas",
    Components: "Componentes",
    Clothing: "Vestuário",
    Accessories: "Acessórios",
    "United States": "Estados Unidos",
    "United Kingdom": "Reino Unido",
    Canada: "Canadá",
    France: "França",
    Germany: "Alemanha",
    Australia: "Austrália",
  };

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function formatValue(value, format) {
    if (value === null) return "—";
    const decimals = format === "money" ? 2 : format === "number" ? 0 : 1;
    const number = new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(format === "money" ? value / 100 : value);
    return (format === "money" ? "$ " : "") + number + (format === "percent" ? "%" : "");
  }

  function pointLabel(value, dimension) {
    if (dimension === "month") return value.split("-").reverse().join("/");
    return labels[value] || value;
  }

  function svgElement(tag, attributes, text) {
    const node = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function lineChart(chart) {
    const points = chart.points;
    const values = points.map(point => point.value).filter(value => value !== null);
    const svg = svgElement("svg", {
      viewBox: "0 0 620 220",
      role: "img",
      "aria-label": chart.title + ". Os valores estão na tabela abaixo.",
    });
    const min = Math.min(0, ...values);
    const max = Math.max(0, ...values);
    const range = max - min || 1;
    const y = value => 175 - (value - min) / range * 140;
    const x = index => points.length === 1 ? 345 : 105 + index * 490 / (points.length - 1);

    [min, (max + min) / 2, max].forEach(value => {
      svg.append(svgElement("line", {
        x1: 100, x2: 600, y1: y(value), y2: y(value), stroke: "var(--border)",
      }));
      const short = new Intl.NumberFormat("pt-BR", {
        notation: "compact", maximumFractionDigits: 1,
      }).format(chart.format === "money" ? value / 100 : value);
      const label = (chart.format === "money" ? "$ " : "") + short + (chart.format === "percent" ? "%" : "");
      svg.append(svgElement("text", {
        x: 90, y: y(value) + 4, "text-anchor": "end", fill: "var(--muted)", "font-size": 12,
      }, label));
    });

    // Separate segments at undefined ratios instead of drawing a misleading zero.
    let segment = [];
    function flushSegment() {
      if (segment.length) {
        svg.append(svgElement("polyline", {
          points: segment.join(" "), fill: "none", stroke: "var(--chart)", "stroke-width": 3,
        }));
      }
      segment = [];
    }
    points.forEach((point, index) => {
      if (point.value === null) {
        flushSegment();
        return;
      }
      segment.push(x(index) + "," + y(point.value));
    });
    flushSegment();

    points.forEach((point, index) => {
      if (point.value === null) return;
      const dot = svgElement("circle", {
        cx: x(index), cy: y(point.value), r: 3, fill: "var(--chart)",
      });
      dot.append(svgElement("title", {}, pointLabel(point.label, chart.dimension) + ": " + formatValue(point.value, chart.format)));
      svg.append(dot);
    });
    if (points.length) {
      svg.append(svgElement("text", {x: 100, y: 205, fill: "var(--muted)", "font-size": 12},
        pointLabel(points[0].label, chart.dimension)));
      if (points.length > 1) {
        svg.append(svgElement("text", {x: 600, y: 205, "text-anchor": "end", fill: "var(--muted)", "font-size": 12},
          pointLabel(points.at(-1).label, chart.dimension)));
      }
    }
    return svg;
  }

  function barChart(chart) {
    const container = element("div", "analysis-bars");
    const values = chart.points.map(point => point.value).filter(value => value !== null);
    const min = Math.min(0, ...values);
    const max = Math.max(0, ...values);
    const range = max - min || 1;
    const zero = -min / range * 100;

    chart.points.forEach(point => {
      const row = element("div", "analysis-bar");
      const header = element("div", "analysis-bar-label");
      header.append(
        element("span", "", pointLabel(point.label, chart.dimension)),
        element("strong", "", formatValue(point.value, chart.format)),
      );
      const track = element("div", "analysis-bar-track");
      track.setAttribute("aria-hidden", "true");
      const baseline = element("span", "analysis-zero");
      baseline.style.left = zero + "%";
      track.append(baseline);
      if (point.value !== null) {
        const fill = element("span", point.value < 0 ? "analysis-fill negative" : "analysis-fill");
        fill.style.left = Math.min(zero, (point.value - min) / range * 100) + "%";
        fill.style.width = Math.abs(point.value) / range * 100 + "%";
        track.append(fill);
      }
      row.append(header, track);
      container.append(row);
    });
    return container;
  }

  function valuesTable(chart) {
    const details = element("details", "analysis-values");
    details.append(element("summary", "", "Ver valores"));
    const table = element("table");
    const head = element("thead");
    const headings = element("tr");
    headings.append(element("th", "", "Grupo"), element("th", "", chart.metric_label));
    head.append(headings);
    const body = element("tbody");
    chart.points.forEach(point => {
      const row = element("tr");
      row.append(
        element("td", "", pointLabel(point.label, chart.dimension)),
        element("td", "", formatValue(point.value, chart.format)),
      );
      body.append(row);
    });
    table.append(head, body);
    details.append(table);
    return details;
  }

  function renderPanel(panel) {
    const container = element("section", "analysis-panel");
    container.append(element("h3", "", panel.title));
    container.append(renderScope(panel));

    const cards = element("div", "analysis-kpis");
    panel.kpis.forEach(kpi => {
      const card = element("article", "analysis-kpi");
      card.append(element("p", "", kpi.label), element("strong", "", formatValue(kpi.value, kpi.format)));
      cards.append(card);
    });
    container.append(cards);

    if (panel.empty) {
      container.append(element("p", "", "Não há vendas nesta seleção."));
    } else {
      const charts = element("div", "analysis-charts");
      panel.charts.forEach(chart => {
        const section = element("section", "analysis-chart");
        section.append(element("h4", "", chart.title));
        if (chart.points.some(point => point.value !== null)) {
          section.append(chart.kind === "line" ? lineChart(chart) : barChart(chart));
        } else {
          section.append(element("p", "", "Não há valores disponíveis para este indicador."));
        }
        section.append(valuesTable(chart));
        charts.append(section);
      });
      container.append(charts);
    }

    const details = element("details", "analysis-notes");
    details.append(element("summary", "", "Como interpretar esta análise"));
    const list = element("ul");
    panel.notes.forEach(note => list.append(element("li", "", note)));
    details.append(list);
    container.append(details);
    return container;
  }


  function renderScope(panel) {
    const filters = panel.filters;
    const date = value => value ? value.split("-").reverse().join("/") : "sem data";
    const scope = [
      date(filters.start_date) + " a " + date(filters.end_date),
      filters.channel ? labels[filters.channel] || filters.channel : "Todos os canais",
      filters.category ? labels[filters.category] || filters.category : "Todas as categorias",
      filters.country ? labels[filters.country] || filters.country : "Todos os países",
    ];
    return element("p", "analysis-scope", "Seleção analisada: " + scope.join(" · "));

  }

  let panelSequence = 0;

  function renderOptionalPanel(panel) {
    const container = element("div", "optional-analysis");
    // Keep interpreted filters visible even when the charts are collapsed.
    container.append(renderScope(panel));
    if (panel.empty || !panel.charts.length) return container;

    const toggle = element("button", "secondary", "Ver gráficos desta análise");
    toggle.type = "button";
    toggle.setAttribute("aria-expanded", "false");
    const content = element("div");
    content.id = "optional-panel-" + (++panelSequence);
    content.hidden = true;
    toggle.setAttribute("aria-controls", content.id);
    let rendered = false;

    toggle.addEventListener("click", () => {
      if (!rendered) {
        content.append(renderPanel(panel));
        rendered = true;
      }
      content.hidden = !content.hidden;
      toggle.setAttribute("aria-expanded", String(!content.hidden));
      toggle.textContent = content.hidden ? "Ver gráficos desta análise" : "Ocultar gráficos";
    });
    container.append(toggle, content);
    return container;
  }

  window.renderAnalysisPanel = renderPanel;
  window.renderOptionalAnalysisPanel = renderOptionalPanel;
})();
