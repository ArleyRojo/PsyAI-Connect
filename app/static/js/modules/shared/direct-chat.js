(function () {
  "use strict";

  const POLL_MS = 3000;
  const MAX_TEXTAREA_HEIGHT = 120;

  (function injectPhotoStyles() {
    if (document.getElementById("chatPhotoStyles")) return;
    var s = document.createElement("style");
    s.id = "chatPhotoStyles";
    s.textContent = "#chatPhotoOverlay{position:fixed;top:0;left:0;width:100%;height:100%;z-index:99999;display:none;align-items:center;justify-content:center}#chatPhotoBackdrop{position:absolute;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.75);backdrop-filter:blur(4px)}.chat-photo-wrap{position:relative;max-width:90vw;max-height:90vh;display:flex;align-items:center;justify-content:center}.chat-photo-close{position:absolute;top:-40px;right:0;background:none;border:none;color:#fff;font-size:2rem;cursor:pointer;padding:4px 10px;line-height:1;z-index:1;opacity:.8;transition:opacity .2s}.chat-photo-close:hover{opacity:1}#chatPhotoFull{max-width:90vw;max-height:85vh;border-radius:12px;box-shadow:0 8px 40px rgba(0,0,0,.4);object-fit:contain;background:#000}.chat-bubble{display:flex;align-items:flex-end;gap:8px;max-width:85%;margin-bottom:10px}.chat-bubble.sent{flex-direction:row-reverse;align-self:flex-end}.chat-bubble.received{flex-direction:row;align-self:flex-start}.chat-bubble-body{display:flex;flex-direction:column;max-width:100%}.chat-bubble-avatar{width:32px;height:32px;border-radius:50%;object-fit:cover;flex-shrink:0;cursor:pointer;transition:opacity .2s;background:var(--gray-bg,#eef3f8)}.chat-bubble-avatar:hover{opacity:.8}";
    document.head.appendChild(s);
  })();

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

  var coloresLetras = {
    'A':'#1D9E75','B':'#378ADD','C':'#D85A30','D':'#534AB7','E':'#BA7517',
    'F':'#639922','G':'#D4537E','H':'#1D9E75','I':'#378ADD','J':'#D85A30',
    'K':'#534AB7','L':'#BA7517','M':'#639922','N':'#D4537E','O':'#1D9E75',
    'P':'#378ADD','Q':'#D85A30','R':'#534AB7','S':'#BA7517','T':'#639922',
    'U':'#D4537E','V':'#1D9E75','W':'#378ADD','X':'#D85A30','Y':'#534AB7',
    'Z':'#BA7517'
  };

  function svgAvatar(letra, size, fontSize) {
    var color = coloresLetras[letra.toUpperCase()] || "#6c757d";
    return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='" + size + "' height='" + size + "' viewBox='0 0 " + size + " " + size + "'%3E%3Ccircle cx='" + (size/2) + "' cy='" + (size/2) + "' r='" + (size/2) + "' fill='" + encodeURIComponent(color) + "'/%3E%3Ctext x='" + (size/2) + "' y='" + (size/2 + fontSize*0.4) + "' text-anchor='middle' fill='white' font-family='Arial' font-weight='700' font-size='" + fontSize + "'%3E" + letra + "%3C/text%3E%3C/svg%3E";
  }

  function photoUrl(fileName) {
    if (!fileName) return null;
    return `/uploads/${encodeURIComponent(fileName)}`;
  }

  function chatAvatarSrc(nombre, size, fz) {
    var inits = initials(nombre);
    var letra = inits.charAt(0).toUpperCase() || '?';
    return svgAvatar(letra, size || 44, fz || 18);
  }

  function avatarHtml(contact) {
    var name = escapeHtml(contact.nombre || "Usuario");
    var rawName = contact.nombre || "Usuario";
    if (contact.fotoPerfil) {
      return `<div class="chat-avatar-circle"><img class="chat-avatar-img" src="${photoUrl(contact.fotoPerfil)}" alt="${escapeHtml(rawName)}" data-nombre="${escapeHtml(rawName)}" data-size="44" onerror="chatFallbackImg(this)"><span class="chat-online-dot"></span></div>`;
    }
    return `<div class="chat-avatar-circle"><img src="${chatAvatarSrc(contact.nombre, 44, 18)}" alt="${name}" style="width:100%;height:100%;border-radius:50%"><span class="chat-online-dot"></span></div>`;
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

  function normalizeRole(value) {
    return String(value || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function rolesMatch(userRole, requiredRole) {
    const current = normalizeRole(userRole);
    const expected = normalizeRole(requiredRole);
    const aliases = {
      paciente: ["paciente", "patient"],
      profesional: ["profesional", "professional", "psicologo", "psicologa"],
      admin: ["admin", "administrador"],
    };

    if (!expected) return true;
    const allowed = aliases[expected] || [expected];
    return allowed.includes(current);
  }

  function normalizeContact(item) {
    const idUsuario = item.idUsuario ?? item.id ?? item.idPaciente ?? item.idProfesional ?? item.usuarioId;
    return {
      ...item,
      idUsuario,
      nombre: item.nombre || item.name || item.paciente || item.profesional || "Usuario",
      fotoPerfil: item.fotoPerfil || item.foto || item.avatar || null,
      ultimoMensaje: item.ultimoMensaje || null,
      ultimaFecha: item.ultimaFecha || null,
      noLeidos: Number(item.noLeidos || 0),
    };
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

      if (!rolesMatch(user.rol || user.role, requiredRole)) {
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
        const active = activeContact && Number(activeContact.idUsuario) === Number(contact.idUsuario) ? " active" : "";
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

    function getSenderPhoto() {
      if (activeContact?.fotoPerfil) return photoUrl(activeContact.fotoPerfil);
      return null;
    }

    function getMyPhoto() {
      try {
        const u = JSON.parse(localStorage.getItem("usuario") || "{}");
        if (u.fotoPerfil) return photoUrl(u.fotoPerfil);
      } catch (e) {}
      return null;
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
      var photo = message.esMio ? getMyPhoto() : getSenderPhoto();
      var bubbleName = "";
      if (message.esMio) {
        try { var u = JSON.parse(localStorage.getItem("usuario") || "{}"); bubbleName = u.nombre || ""; } catch(e) {}
      } else {
        bubbleName = activeContact?.nombre || "";
      }
      var rawName = bubbleName;
      bubbleName = escapeHtml(bubbleName);
      if (!photo) {
        var inits = initials(rawName);
        var letra = inits.charAt(0).toUpperCase() || "?";
        var svg = svgAvatar(letra, 28, 12);
        photo = svg;
      }
      const photoHtml = '<img src="' + photo + '" alt="' + bubbleName + '" data-nombre="' + bubbleName + '" data-size="28" class="chat-bubble-avatar" onerror="chatFallbackImg(this)" onclick="var e=document.getElementById(\'chatPhotoFull\');if(e){e.src=this.src;var o=document.getElementById(\'chatPhotoOverlay\');if(o)o.style.display=\'flex\';document.body.style.overflow=\'hidden\'}">';
      messagesArea.insertAdjacentHTML("beforeend", `
        <div class="chat-bubble ${side}">
          ${photoHtml}
          <div class="chat-bubble-body">
            <div class="chat-bubble-text">${text}</div>
            <div class="chat-bubble-meta">
              <span>${escapeHtml(formatTime(message.fecha))}</span>
              ${message.esMio ? '<i class="fas fa-check-double chat-check-icon"></i>' : ""}
            </div>
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
      const response = await fetch(endpoint, {
        credentials: "include",
        cache: "no-store",
      });
      const data = await response.json();
      if (!response.ok || data.success === false) return [];

      const candidates = [
        key,
        "profesionales",
        "pacientes",
        "usuarios",
        "items",
        "data",
      ];
      const collectionKey = candidates.find((candidate) => Array.isArray(data[candidate]));
      const items = collectionKey ? data[collectionKey] : (Array.isArray(data) ? data : []);
      return items.map(normalizeContact).filter((item) => item.idUsuario);
    }

    function enrichFallbackContacts(items) {
      return items.map((item) => normalizeContact({
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

      var headerImg = headerAvatar.querySelector("img");
      if (headerImg) {
        headerImg.style.cursor = "pointer";
        headerImg.addEventListener("click", function(e) {
          e.stopPropagation();
          showPhotoModal(headerImg.src);
        });
      }
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

  window.chatFallbackImg = function(img) {
    if (!img || !img.parentNode) return;
    var nombre = img.getAttribute("data-nombre") || img.alt || "Usuario";
    var inits = initials(nombre);
    var letra = inits.charAt(0).toUpperCase() || "?";
    var sz = parseInt(img.getAttribute("data-size")) || parseInt(img.width) || parseInt(img.parentNode.offsetWidth) || 44;
    var fz = Math.round(sz * 0.4);
    img.src = svgAvatar(letra, sz, fz);
    img.onerror = null;
    img.style.width = "100%";
    img.style.height = "100%";
    img.style.borderRadius = "50%";
    img.style.objectFit = "cover";
  };

  function showPhotoModal(src) {
    var overlay = document.getElementById("chatPhotoOverlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "chatPhotoOverlay";
      overlay.innerHTML =
        '<div id="chatPhotoBackdrop"></div><div class="chat-photo-wrap"><button class="chat-photo-close" onclick="var o=document.getElementById(\'chatPhotoOverlay\');if(o)o.style.display=\'none\';document.body.style.overflow=\'\'" aria-label="Cerrar">&times;</button><img id="chatPhotoFull" src="" alt="Foto de perfil"></div>';
      overlay.querySelector("#chatPhotoBackdrop").addEventListener("click", function() {
        overlay.style.display = "none";
        document.body.style.overflow = "";
      });
      document.body.appendChild(overlay);
    }
    overlay.querySelector("#chatPhotoFull").src = src;
    overlay.style.display = "flex";
    document.body.style.overflow = "hidden";
  }

  document.addEventListener("DOMContentLoaded", function() {
    document.addEventListener("keydown", function(e) {
      if (e.key === "Escape") {
        var o = document.getElementById("chatPhotoOverlay");
        if (o && o.style.display !== "none" && o.style.display !== "") {
          o.style.display = "none";
          document.body.style.overflow = "";
        }
      }
    });
    document.querySelectorAll("[data-chat-root]").forEach(initDirectChat);
  });
})();
