(function () {
  "use strict";

  const POLL_MS = 3000;
  const MAX_TEXTAREA_HEIGHT = 120;

  function qs(root, selector) {
    return root.querySelector(selector);
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function initials(name) {
    return String(name || "")
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join("") || "US";
  }

  function photoUrl(fileName) {
    return fileName ? `/uploads/${encodeURIComponent(fileName)}` : "/img/default-avatar.png";
  }

  function avatarHtml(contact) {
    const name = escapeHtml(contact.nombre || "Usuario");
    if (contact.fotoPerfil) {
      return `<div class="chat-avatar-circle"><img src="${photoUrl(contact.fotoPerfil)}" alt="${name}" onerror="this.remove();this.parentElement.insertAdjacentText('afterbegin','${initials(contact.nombre)}');"><span class="chat-online-dot"></span></div>`;
    }
    return `<div class="chat-avatar-circle">${escapeHtml(initials(contact.nombre))}<span class="chat-online-dot"></span></div>`;
  }

  function parseDate(value) {
    if (!value) return null;
    const normalized = String(value).replace(" ", "T");
    const date = new Date(normalized);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function dateKey(value) {
    const date = parseDate(value);
    if (!date) return "";
    return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
  }

  function sameDay(a, b) {
    return a && b &&
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate();
  }

  function formatDateDivider(value) {
    const date = parseDate(value);
    if (!date) return "";

    const today = new Date();
    const yesterday = new Date();
    yesterday.setDate(today.getDate() - 1);

    if (sameDay(date, today)) return "Hoy";
    if (sameDay(date, yesterday)) return "Ayer";

    return date.toLocaleDateString("es-CO", {
      day: "numeric",
      month: "long",
    });
  }

  function formatTime(value) {
    const date = parseDate(value);
    if (!date) return "";
    return date.toLocaleTimeString("es-CO", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function contactSubtitle(contact, mode) {
    if (mode === "patient") {
      const parts = [];
      if (contact.edad) parts.push(`${contact.edad} años`);
      if (contact.genero) parts.push(contact.genero);
      return parts.join(" - ") || "Paciente";
    }
    return contact.especialidad || "Profesional";
  }

  function initDirectChat(root) {
    const listEndpoint = root.dataset.listEndpoint;
    const listKey = root.dataset.listKey;
    const messagesEndpoint = root.dataset.messagesEndpoint || "/api/chat/mensajes";
    const sendEndpoint = root.dataset.sendEndpoint || "/api/chat/enviar";
    const requiredRole = root.dataset.requiredRole || "";
    const fallbackEndpoint = root.dataset.fallbackEndpoint || "";
    const fallbackKey = root.dataset.fallbackKey || listKey;
    const contactMode = root.dataset.contactMode || "professional";
    const emptyText = root.dataset.emptyText || "Selecciona una conversacion";

    const sidebar = qs(root, ".chat-sidebar");
    const panel = qs(root, ".chat-panel");
    const list = qs(root, ".chat-list");
    const search = qs(root, ".chat-search-input");
    const placeholder = qs(root, ".chat-panel-placeholder");
    const activeView = qs(root, ".chat-active-view");
    const headerAvatar = qs(root, ".chat-active-avatar");
    const headerName = qs(root, ".chat-active-name");
    const headerStatus = qs(root, ".chat-active-status");
    const messagesArea = qs(root, ".chat-messages-area");
    const textarea = qs(root, ".chat-message-input");
    const sendButton = qs(root, ".chat-send-btn");
    const backButton = qs(root, ".chat-back-btn");

    let contacts = [];
    let activeContact = null;
    let lastMessageId = 0;
    let lastRenderedDateKey = "";
    let seenMessageIds = new Set();
    let pollTimer = null;
    let contactPollTimer = null;
    let loadingContacts = false;

    function renderAuthState(icon, text) {
      list.innerHTML = `
        <div class="chat-empty-state">
          <i class="${icon}"></i>
          <div>${escapeHtml(text)}</div>
        </div>
      `;
    }

    async function getSessionUser() {
      try {
        const response = await fetch("/api/session", {
          credentials: "include",
          cache: "no-store",
        });
        if (!response.ok) return null;

        const data = await response.json();
        return data.logged_in ? (data.usuario || null) : null;
      } catch (error) {
        console.error("No se pudo verificar la sesion del chat:", error);
        return null;
      }
    }

    async function ensureAllowedSession() {
      if (!requiredRole) return true;

      renderAuthState("fas fa-circle-notch fa-spin", "Verificando sesion...");
      const user = await getSessionUser();

      if (!user) {
        renderAuthState("fas fa-lock", "Redirigiendo al inicio de sesion...");
        return false;
      }

      if (user.rol !== requiredRole) {
        renderAuthState("fas fa-user-lock", "Esta vista pertenece a otro rol.");
        return false;
      }

      return true;
    }

    function clearPolling() {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
      if (contactPollTimer) {
        clearInterval(contactPollTimer);
        contactPollTimer = null;
      }
    }

    function startPolling() {
      if (pollTimer) {
        clearInterval(pollTimer);
      }
      pollTimer = setInterval(() => {
        if (activeContact) {
          loadMessages(true);
        }
      }, POLL_MS);
    }

    function startContactPolling() {
      if (contactPollTimer) {
        clearInterval(contactPollTimer);
      }
      contactPollTimer = setInterval(() => {
        loadContacts(false);
      }, POLL_MS);
    }

    function renderSkeleton() {
      list.innerHTML = Array.from({ length: 5 }).map(() => `
        <div class="chat-skeleton-item">
          <div class="chat-skeleton-avatar"></div>
          <div class="chat-skeleton-lines">
            <div class="chat-skeleton-line"></div>
            <div class="chat-skeleton-line s"></div>
          </div>
        </div>
      `).join("");
    }

    function renderContacts() {
      const term = search.value.trim().toLowerCase();
      const orderedContacts = sortContacts(contacts);
      const visible = orderedContacts.filter((contact) => {
        const haystack = `${contact.nombre || ""} ${contact.especialidad || ""} ${contact.genero || ""}`.toLowerCase();
        return haystack.includes(term);
      });

      if (!visible.length && contacts.length) {
        list.innerHTML = `
          <div class="chat-empty-state">
            <i class="fas fa-search"></i>
            <div>No hay resultados para tu busqueda</div>
          </div>
        `;
        return;
      }

      if (!visible.length) {
        list.innerHTML = `
          <div class="chat-empty-state">
            <i class="fas fa-comments"></i>
            <div>No hay usuarios registrados para mostrar</div>
          </div>
        `;
        return;
      }

      list.innerHTML = visible.map((contact) => {
        const active = activeContact && activeContact.idUsuario === contact.idUsuario ? " active" : "";
        const preview = contact.ultimoMensaje || contactSubtitle(contact, contactMode);
        const unread = Number(contact.noLeidos || 0);
        const unreadClass = unread > 0 ? " has-unread" : "";
        return `
          <button type="button" class="chat-item${active}${unreadClass}" data-contact-id="${contact.idUsuario}">
            ${avatarHtml(contact)}
            <span class="chat-item-info">
              <span class="chat-item-name">${escapeHtml(contact.nombre)}</span>
              <span class="chat-item-preview">${escapeHtml(preview)}</span>
            </span>
            <span class="chat-item-meta">
              <span class="chat-item-time">${escapeHtml(formatTime(contact.ultimaFecha))}</span>
              ${unread > 0 ? `<span class="chat-badge-unread">${unread}</span>` : ""}
              ${unread > 0 ? `<span class="chat-new-label">Nuevo</span>` : ""}
            </span>
          </button>
        `;
      }).join("");
    }

    function sortContacts(items) {
      return [...items].sort((a, b) => {
        const unreadA = Number(a.noLeidos || 0) > 0 ? 1 : 0;
        const unreadB = Number(b.noLeidos || 0) > 0 ? 1 : 0;
        if (unreadA !== unreadB) return unreadB - unreadA;

        const dateA = parseDate(a.ultimaFecha);
        const dateB = parseDate(b.ultimaFecha);
        const timeA = dateA ? dateA.getTime() : 0;
        const timeB = dateB ? dateB.getTime() : 0;
        if (timeA !== timeB) return timeB - timeA;

        return String(a.nombre || "").localeCompare(String(b.nombre || ""), "es");
      });
    }

    function appendDateDivider(label) {
      if (!label) return;
      messagesArea.insertAdjacentHTML("beforeend", `
        <div class="chat-date-divider"><span>${escapeHtml(label)}</span></div>
      `);
    }

    function appendMessage(message) {
      const messageId = Number(message.idMensaje || 0);
      if (messageId && seenMessageIds.has(messageId)) {
        return;
      }
      if (messageId) {
        seenMessageIds.add(messageId);
      }

      const currentDateKey = dateKey(message.fecha);
      if (currentDateKey && currentDateKey !== lastRenderedDateKey) {
        appendDateDivider(formatDateDivider(message.fecha));
        lastRenderedDateKey = currentDateKey;
      }

      const side = message.esMio ? "sent" : "received";
      const text = escapeHtml(message.mensaje).replace(/\n/g, "<br>");
      messagesArea.insertAdjacentHTML("beforeend", `
        <div class="chat-bubble ${side}">
          <div class="chat-bubble-text">${text}</div>
          <div class="chat-bubble-meta">
            <span>${escapeHtml(formatTime(message.fecha))}</span>
            ${message.esMio ? '<i class="fas fa-check-double chat-check-icon"></i>' : ""}
          </div>
        </div>
      `);

      lastMessageId = Math.max(lastMessageId, messageId);
    }

    function scrollToBottom() {
      messagesArea.scrollTop = messagesArea.scrollHeight;
    }

    async function loadMessages(onlyNew) {
      if (!activeContact) return;

      const params = new URLSearchParams({ receptor: activeContact.idUsuario });
      if (onlyNew && lastMessageId > 0) {
        params.set("desde", lastMessageId);
      }

      try {
        const response = await fetch(`${messagesEndpoint}?${params.toString()}`, {
          credentials: "include",
        });
        const data = await response.json();

        if (!data.success) return;

        if (!onlyNew) {
          messagesArea.innerHTML = "";
          lastRenderedDateKey = "";
          lastMessageId = 0;
          seenMessageIds = new Set();
        }

        (data.mensajes || []).forEach(appendMessage);
        if ((data.mensajes || []).length) {
          scrollToBottom();
        }
      } catch (error) {
        console.error("Error cargando mensajes:", error);
      }
    }

    async function fetchContactList(endpoint, key) {
      const response = await fetch(endpoint, { credentials: "include" });
      const data = await response.json();
      return data.success ? (data[key] || []) : [];
    }

    function enrichFallbackContacts(items) {
      return items.map((item) => ({
        ...item,
        ultimoMensaje: item.ultimoMensaje || null,
        ultimaFecha: item.ultimaFecha || null,
        noLeidos: Number(item.noLeidos || 0),
      }));
    }

    function mergeActiveContact() {
      if (!activeContact) return;
      const refreshed = contacts.find((item) => Number(item.idUsuario) === Number(activeContact.idUsuario));
      if (refreshed) {
        refreshed.noLeidos = 0;
        activeContact = refreshed;
      }
    }

    async function loadContacts(showSkeleton = true) {
      if (loadingContacts) return;
      loadingContacts = true;
      if (showSkeleton) {
        renderSkeleton();
      }
      try {
        contacts = await fetchContactList(listEndpoint, listKey);
        if (!contacts.length && fallbackEndpoint) {
          contacts = enrichFallbackContacts(await fetchContactList(fallbackEndpoint, fallbackKey));
        }
        mergeActiveContact();
        renderContacts();
      } catch (error) {
        console.error("Error cargando conversaciones:", error);
        if (fallbackEndpoint) {
          try {
            contacts = enrichFallbackContacts(await fetchContactList(fallbackEndpoint, fallbackKey));
          } catch (fallbackError) {
            console.error("Error cargando usuarios registrados:", fallbackError);
        contacts = [];
          }
        } else {
          contacts = [];
        }
        mergeActiveContact();
        renderContacts();
      } finally {
        loadingContacts = false;
      }
    }

    function openConversation(contactId) {
      const contact = contacts.find((item) => Number(item.idUsuario) === Number(contactId));
      if (!contact) return;

      activeContact = contact;
      activeContact.noLeidos = 0;
      lastMessageId = 0;
      lastRenderedDateKey = "";

      placeholder.classList.add("d-none");
      activeView.classList.remove("d-none");
      headerAvatar.innerHTML = avatarHtml(contact);
      headerName.textContent = contact.nombre || emptyText;
      headerStatus.textContent = contactSubtitle(contact, contactMode);
      textarea.value = "";
      textarea.style.height = "";

      sidebar.classList.add("slide-out");
      panel.classList.add("slide-in");
      renderContacts();
      loadMessages(false);
      startPolling();
      loadContacts(false);
      textarea.focus();
    }

    async function sendMessage() {
      if (!activeContact) return;
      const text = textarea.value.trim();
      if (!text) return;

      sendButton.disabled = true;
      try {
        const response = await fetch(sendEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({
            receptor: activeContact.idUsuario,
            mensaje: text,
          }),
        });
        const data = await response.json();
        if (!data.success) return;

        appendMessage({
          idMensaje: data.idMensaje,
          idEmisor: 0,
          idReceptor: activeContact.idUsuario,
          mensaje: text,
          esMio: true,
          fecha: new Date().toISOString(),
          leido: 0,
        });
        const now = new Date().toISOString();
        activeContact.ultimoMensaje = text.slice(0, 60);
        activeContact.ultimaFecha = now;
        activeContact.ultimoIdMensaje = data.idMensaje || activeContact.ultimoIdMensaje || 0;
        contacts = contacts.map((contact) => (
          Number(contact.idUsuario) === Number(activeContact.idUsuario)
            ? { ...contact, ultimoMensaje: activeContact.ultimoMensaje, ultimaFecha: now, ultimoIdMensaje: activeContact.ultimoIdMensaje, noLeidos: 0 }
            : contact
        ));
        renderContacts();
        scrollToBottom();
        textarea.value = "";
        textarea.style.height = "";
        await loadContacts(false);
      } catch (error) {
        console.error("Error enviando mensaje:", error);
      } finally {
        sendButton.disabled = false;
        textarea.focus();
      }
    }

    list.addEventListener("click", (event) => {
      const item = event.target.closest(".chat-item");
      if (item) {
        openConversation(item.dataset.contactId);
      }
    });

    search.addEventListener("input", renderContacts);

    textarea.addEventListener("input", () => {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
    });

    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    sendButton.addEventListener("click", sendMessage);

    backButton.addEventListener("click", () => {
      sidebar.classList.remove("slide-out");
      panel.classList.remove("slide-in");
    });

    window.addEventListener("beforeunload", clearPolling);

    placeholder.querySelector("p").textContent = emptyText;
    ensureAllowedSession().then((isAllowed) => {
      if (!isAllowed) return;
      loadContacts();
      startContactPolling();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-chat-root]").forEach(initDirectChat);
  });
})();
