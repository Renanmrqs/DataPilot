/* Authentication and allowance display. The API owns every quota decision. */
(() => {
  const element = id => document.getElementById(id);
  let state = {mode: "loading", can_ask: false};
  let token = null;
  let refreshTimer = null;
  let emailTimer = null;
  let sendingEmail = false;
  let emailWait = false;
  let refreshInProgress = null;
  let announceRefresh = false;
  let lastRefreshAt = 0;

  function changed() {
    window.dispatchEvent(new CustomEvent("demo-access-changed", {detail: state}));
  }

  function render() {
    const demo = state.mode === "demo";
    element("demo-access").hidden = !demo && state.mode !== "error";
    document.body.classList.toggle("demo-mode", demo);
    if (!demo) {
      changed();
      return;
    }
    const quota = state.quota;
    const providerLabels = {gemini: "Gemini", deepseek: "DeepSeek", openai: "OpenAI", compatible: "IA"};
    element("demo-provider").textContent = state.provider ? `· ${providerLabels[state.provider] || "IA"}` : "";
    element("demo-quota").textContent = state.authenticated && quota
      ? `${quota.remaining} de ${quota.limit} perguntas disponíveis`
      : `${state.default_limit} perguntas por conta`;
    element("demo-description").textContent = state.authenticated
      ? `Acesso confirmado: ${state.email}`
      : "Explore o painel à vontade. Para experimentar a IA, confirme seu e-mail. Sem senha.";
    element("demo-message").textContent = state.message;
    element("demo-refresh").disabled = Boolean(refreshInProgress);
    element("demo-progress").max = Math.max(quota?.limit ?? state.default_limit, 1);
    element("demo-progress").value = quota?.remaining ?? state.default_limit;
    element("demo-progress").setAttribute("aria-label", element("demo-quota").textContent);
    element("demo-login").hidden = state.authenticated;
    element("demo-logout").hidden = !state.authenticated;
    element("demo-email-submit").disabled = !state.auth_url || sendingEmail || emailWait;
    element("demo-policy").textContent = "A cota é por conta e não reinicia ao recarregar ou abrir uma nova conversa. "
      + "Perguntas enviadas à IA contam mesmo se a resposta falhar. Há também uma cota diária compartilhada.";
    if (refreshTimer) clearTimeout(refreshTimer);
    if (quota?.retry_after_seconds && state.status === "cooldown") {
      refreshTimer = setTimeout(() => refresh(), (quota.retry_after_seconds + 1) * 1000);
    }
    changed();
  }

  async function authRequest(path, options = {}) {
    const response = await fetch(state.auth_url + path, {
      ...options, credentials: "include", cache: "no-store",
    });
    if (response.status === 401 && path === "/token") return null;
    const data = await response.json();
    if (!response.ok) {
      // Do not display raw provider responses, tokens or implementation details.
      throw new Error("Não foi possível confirmar o acesso. Aguarde e tente novamente.");
    }
    return data;
  }

  async function loadAccess() {
    const previousEmail = state.email;
    let sessionMissing = false;
    if (state.mode === "demo" && state.auth_url) {
      const session = await authRequest("/token");
      token = typeof session?.token === "string" ? session.token : null;
      sessionMissing = !token;
    }
    const response = await fetch("/api/demo/access", {
      cache: "no-store", headers: token ? {Authorization: `Bearer ${token}`} : {},
    });
    if (response.status === 401 || response.status === 403) {
      const rejected = await response.json();
      token = null;
      const anonymous = await fetch("/api/demo/access", {cache: "no-store"});
      if (!anonymous.ok) throw new Error("Não foi possível consultar o acesso da demonstração.");
      state = await anonymous.json();
      state.message = typeof rejected.detail === "string" ? rejected.detail
        : "Entre novamente para confirmar seu e-mail e consultar seu saldo.";
    } else {
      if (!response.ok) throw new Error("Não foi possível consultar o acesso da demonstração.");
      state = await response.json();
    }
    if (announceRefresh && sessionMissing && !state.authenticated) {
      state.message = "O acesso ainda não foi encontrado neste navegador. Abra o link recebido aqui, "
        + "usando o mesmo endereço do site. Se já fez isso, a sessão pode estar bloqueada pelo navegador.";
    }
    if (announceRefresh && state.authenticated && state.status === "paused") {
      state.message = "Seu e-mail foi confirmado e o saldo foi consultado. O chat continua pausado para configuração.";
    }
    if (previousEmail && previousEmail !== state.email) {
      window.dispatchEvent(new Event("demo-identity-changed"));
    }
    render();
    return state;
  }

  function refresh(announce = false) {
    announceRefresh = announceRefresh || announce;
    if (refreshInProgress) return refreshInProgress;
    lastRefreshAt = Date.now();
    element("demo-refresh").disabled = true;
    if (announce) element("demo-message").textContent = "Conferindo seu acesso e o saldo…";
    refreshInProgress = loadAccess().catch(() => {
      token = null;
      state = {...state, can_ask: false, status: "unavailable"};
      if (state.mode === "loading") state.mode = "error";
      state.message = "Não foi possível consultar seu acesso. Tente atualizar o saldo.";
      element("demo-message").textContent = state.message;
      render();
      return state;
    }).finally(() => {
      refreshInProgress = null;
      announceRefresh = false;
      element("demo-refresh").disabled = false;
    });
    return refreshInProgress;
  }

  element("demo-login").addEventListener("submit", async event => {
    event.preventDefault();
    if (sendingEmail || emailWait || !state.auth_url) return;
    sendingEmail = true;
    render();
    element("demo-email-status").textContent = "Solicitando seu link de acesso…";
    try {
      await authRequest("/sign-in/magic-link", {
        method: "POST", headers: {"Content-Type": "application/json"},
        body: JSON.stringify({email: element("demo-email").value.trim()}),
      });
      element("demo-email-status").textContent = "Confira sua caixa de entrada e o spam. Abra o link e volte para a demonstração.";
      emailWait = true;
      clearTimeout(emailTimer);
      emailTimer = setTimeout(() => { emailWait = false; render(); }, 60000);
    } catch (error) {
      element("demo-email-status").textContent = "Não foi possível solicitar o link. Confira sua conexão e tente novamente mais tarde.";
    } finally {
      sendingEmail = false;
      render();
    }
  });

  element("demo-refresh").addEventListener("click", () => refresh(true));
  function restoreAccessOnReturn() {
    if (document.visibilityState === "visible" && state.mode === "demo"
        && Date.now() - lastRefreshAt > 2000) {
      refresh();
    }
  }
  window.addEventListener("focus", restoreAccessOnReturn);
  document.addEventListener("visibilitychange", restoreAccessOnReturn);
  element("demo-logout").addEventListener("click", async () => {
    element("demo-logout").disabled = true;
    try {
      await authRequest("/sign-out", {method: "POST", headers: {"Content-Type": "application/json"}, body: "{}"});
      token = null;
      element("demo-email").value = "";
      element("demo-email-status").textContent = "";
      window.dispatchEvent(new Event("demo-identity-changed"));
      await refresh();
    } catch (error) {
      element("demo-message").textContent = "Não foi possível sair. Tente novamente.";
    } finally {
      element("demo-logout").disabled = false;
    }
  });

  window.demoAccess = {
    get state() { return state; },
    refresh,
    async headers() {
      await refresh();
      if (!state.can_ask) throw new Error(state.message || "Confirme seu acesso antes de enviar a pergunta.");
      return token ? {Authorization: `Bearer ${token}`} : {};
    },
  };

  // Check once for server settings, then restore a possible Neon session.
  refresh().then(() => { if (state.mode === "demo" && state.auth_url) return refresh(); });
  const callbackError = new URL(window.location.href).searchParams.get("auth_error");
  if (callbackError) {
    element("demo-email-status").textContent = callbackError === "session_unavailable"
      ? "Não foi possível concluir seu acesso. Tente novamente mais tarde."
      : "Esse link expirou, já foi usado ou não pertence a este navegador. Solicite um novo link abaixo.";
    const cleanUrl = new URL(window.location.href);
    cleanUrl.searchParams.delete("auth_error");
    history.replaceState(history.state, "", cleanUrl.href);
  }
})();
