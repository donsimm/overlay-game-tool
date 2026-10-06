"use strict";
const $ = (s, el = document) => el.querySelector(s);
const h = (tag, props = {}, ...kids) => {
  const el = Object.assign(document.createElement(tag), props);
  el.append(...kids.filter(k => k != null));
  return el;  // textContent/append statt innerHTML: kein XSS durch Namen
};
async function api(path, method = "GET", body) {
  const r = await fetch(path, {
    method, headers: body ? {"Content-Type": "application/json"} : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.status === 204 ? null : r.json();
}
function notice(msg, isError) {
  const n = $("#notice");
  n.textContent = msg; n.className = isError ? "error" : ""; n.hidden = !msg;
}
const guard = fn => async (...a) => { try { await fn(...a); } catch (e) { notice(e.message, true); } };

/* ---------- Verbindungen ---------- */
function connectionCard(c) {
  const secret = h("input", {type: "password", placeholder: c.has_credentials ? "unverändert (gespeichert)" : "Client-Secret", autocomplete: "off"});
  const id = h("input", {value: c.client_id, placeholder: "Client-ID", autocomplete: "off"});
  const save = h("button", {textContent: "Speichern", onclick: guard(async () => {
    await api(`/api/connections/${c.key}/credentials`, "PUT", {client_id: id.value, client_secret: secret.value || null});
    notice("Zugangsdaten gespeichert."); await loadConnections();
  })});
  const card = h("div", {className: "card"},
    h("h2", {}, c.label, h("span", {className: "badge" + (c.connected ? " ok" : ""), textContent: c.connected ? "verbunden" : "nicht verbunden"})));
  if (c.connected) {
    card.append(h("div", {className: "account"},
      c.account?.avatar ? h("img", {src: c.account.avatar, alt: ""}) : null,
      h("strong", {textContent: c.account?.name || "(unbekannt)"})));
    if (c.error) card.append(h("p", {className: "err", textContent: c.error}));
    card.append(h("div", {className: "row"},
      h("button", {textContent: "Verbindung prüfen", onclick: guard(async () => {
        const r = await api(`/api/connections/${c.key}/check`, "POST");
        notice(r.error || `${c.label}: Verbindung in Ordnung.`, !!r.error); await loadConnections();
      })}),
      h("button", {className: "danger", textContent: "Trennen", onclick: guard(async () => {
        await api(`/api/connections/${c.key}/disconnect`, "POST"); notice(`${c.label} getrennt.`); await loadConnections();
      })})));
  } else {
    card.append(h("div", {className: "row"},
      h("button", {className: "primary", textContent: `Mit ${c.label} verbinden`, disabled: !c.has_credentials,
        onclick: () => { location.href = `/auth/${c.key}/login`; }}),
      c.has_credentials ? null : h("span", {className: "dim", textContent: "Zuerst Zugangsdaten speichern."})));
  }
  card.append(h("details", {open: !c.has_credentials},
    h("summary", {textContent: "Zugangsdaten (eigene App)"}),
    h("p", {className: "dim"}, "App anlegen unter ", h("a", {href: c.console_url, target: "_blank", rel: "noreferrer", textContent: c.console_url}),
      ". Als Weiterleitungs-URL eintragen:"),
    h("p", {}, h("code", {textContent: c.redirect_uri})),
    h("div", {className: "row grow"}, id, secret, save),
    h("p", {className: "dim", textContent: "Berechtigungen: " + c.scopes.join(", ")})));
  return card;
}
async function loadConnections() {
  const list = await api("/api/connections");
  $("#connections").replaceChildren(...list.map(connectionCard));
}

/* ---------- Module ---------- */
let types = [];
function moduleCard(m) {
  const url = `${location.origin}/overlay/${m.id}`;
  const name = h("input", {value: m.name, maxLength: 60});
  const w = h("input", {type: "number", value: m.width, min: 16, max: 8192});
  const hh = h("input", {type: "number", value: m.height, min: 16, max: 8192});
  const type = types.find(t => t.type === m.type);
  const label = type?.label || m.type;
  const inputs = (type?.fields || []).map(f => {
    const input = h("input", {type: f.kind === "color" ? "color" : "text", value: m.settings[f.key] ?? f.default, maxLength: 120});
    return {key: f.key, input, row: h("label", {className: "field"}, h("span", {className: "dim", textContent: f.label}), input)};
  });
  return h("div", {className: "card"},
    h("h2", {}, m.name, h("span", {className: "badge", textContent: label}),
      m.enabled ? null : h("span", {className: "badge", textContent: "deaktiviert"})),
    h("div", {className: "row"}, h("span", {className: "dim", textContent: "OBS-Browserquelle:"}), h("code", {textContent: url}),
      h("button", {textContent: "Kopieren", onclick: guard(async () => {
        await navigator.clipboard.writeText(url); notice("URL kopiert.");
      })}),
      h("a", {href: url + "?debug=1", target: "_blank", textContent: "Vorschau"})),
    h("p", {className: "dim", textContent: `In OBS Breite ${m.width} und Höhe ${m.height} einstellen.`}),
    inputs.length ? h("div", {className: "row"}, ...inputs.map(i => i.row)) : null,
    h("div", {className: "row"}, name, w, "×", hh,
      h("button", {textContent: "Speichern", onclick: guard(async () => {
        await api(`/api/modules/${m.id}`, "PATCH", {name: name.value, width: +w.value, height: +hh.value,
          settings: Object.fromEntries(inputs.map(i => [i.key, i.input.value]))});
        notice("Gespeichert."); await loadModules();
      })}),
      h("button", {textContent: m.enabled ? "Deaktivieren" : "Aktivieren", onclick: guard(async () => {
        await api(`/api/modules/${m.id}`, "PATCH", {enabled: !m.enabled}); await loadModules();
      })}),
      h("button", {className: "danger", textContent: "Löschen", onclick: guard(async () => {
        if (!confirm(`Modul «${m.name}» löschen?`)) return;
        await api(`/api/modules/${m.id}`, "DELETE"); await loadModules();
      })})));
}
async function loadModules() {
  if (!types.length) {
    types = await api("/api/module-types");
    $("#new-type").replaceChildren(...types.map(t => h("option", {value: t.type, textContent: `${t.label} – ${t.description}`})));
  }
  const list = await api("/api/modules");
  $("#modules").replaceChildren(...(list.length ? list.map(moduleCard)
    : [h("p", {className: "dim", textContent: "Noch keine Module. Oben eines erstellen."})]));
}
$("#new-module").addEventListener("submit", guard(async e => {
  e.preventDefault();
  await api("/api/modules", "POST", {type: $("#new-type").value, name: $("#new-name").value});
  $("#new-name").value = ""; await loadModules();
}));

/* ---------- Tabs ---------- */
const loaders = {connections: loadConnections, modules: loadModules};
const show = guard(async () => {
  const tab = loaders[location.hash.slice(1)] ? location.hash.slice(1) : "connections";
  for (const t of Object.keys(loaders)) {
    $(`#tab-${t}`).hidden = t !== tab;
    $(`nav [data-tab=${t}]`).classList.toggle("active", t === tab);
  }
  await loaders[tab]();
});
addEventListener("hashchange", show);
const q = new URLSearchParams(location.search);
if (q.get("error")) notice(q.get("error"), true);
else if (q.get("connected")) notice(`${q.get("connected")} erfolgreich verbunden.`);
if (location.search) history.replaceState(null, "", location.pathname + location.hash);
show();
