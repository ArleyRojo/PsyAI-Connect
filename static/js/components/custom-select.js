/* ============================================================
   PsyAI Connect – Custom <select> reutilizable (v2, corregido)
   Se activa en cualquier <select data-custom-select>
   ------------------------------------------------------------
   • El <select> nativo sigue siendo la fuente de verdad
   • Dispara "change" nativo (agendaquotes.js sigue funcionando)
   • Se re-renderiza solo cuando cambian las <option> (MutationObserver)
   • Detecta cambios programáticos de .value (select.value = '')
   • El panel vive en <body> con position:fixed (nunca se recorta)
   • Se abre SIEMPRE de forma síncrona: ya no depende de eventos
     de scroll ni de doble disparo pointerdown + click
   ============================================================ */
(() => {
  const ICON_MAP = {
    'Ansiedad':              'fa-brain',
    'Estrés':                'fa-bolt',
    'Depresión':             'fa-cloud-rain',
    'Autoestima':            'fa-heart',
    'Duelo':                 'fa-feather',
    'Trastornos del Sueño':  'fa-moon',
    'Adicciones':            'fa-pills',
    'Orientación Emocional': 'fa-compass',
    'Terapia de Pareja':     'fa-user-friends',
    'Otro':                  'fa-ellipsis-h',
    'Primera sesión':        'fa-door-open',
    'Seguimiento':           'fa-rotate',
    'Evaluación':            'fa-clipboard-check'
  };

  const MAX_H = 280;   // alto máximo del panel
  const GAP   = 6;     // separación entre botón y panel
  const EDGE  = 12;    // margen mínimo contra el borde de la ventana

  // ---------- Helpers ----------
  const hashColor = (str) => {
    let h = 0;
    for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
    return `hsl(${Math.abs(h) % 360} 55% 45%)`;
  };

  const initials = (name) => name.trim().split(/\s+/)
    .map(w => w[0]).slice(0, 2).join('').toUpperCase();

  const el = (tag, className, text) => {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (text != null) n.textContent = text;
    return n;
  };

  const faIcon = (cls, extra) => {
    const i = document.createElement('i');
    i.className = `fas ${cls}${extra ? ' ' + extra : ''}`;
    i.setAttribute('aria-hidden', 'true');
    return i;
  };

  const avatar = (name) => {
    const a = el('div', 'cs-avatar', initials(name));
    a.style.background = hashColor(name);
    return a;
  };

  // El nombre puede venir como "Nombre - Especialidad"
  const splitName = (text) => {
    const parts = text.split(' - ');
    return { name: parts[0].trim(), specialty: (parts[1] || '').trim() };
  };

  let uid = 0;

  // ---------- Componente ----------
  class CustomSelect {
    constructor(native) {
      this.native    = native;
      this.id        = native.id || `cs-auto-${++uid}`;
      this.isTipo    = /tipo/i.test(this.id);
      this.open      = false;
      this.activeIdx = -1;
      this.options   = [];
      this._typed    = '';
      this._typedAt  = 0;

      const emptyOpt = native.querySelector('option[value=""]');
      this.placeholder = native.dataset.placeholder ||
                         (emptyOpt ? emptyOpt.textContent.trim() : 'Seleccionar');
      this._init();
    }

    _init() {
      const native = this.native;
      native.classList.add('cs-native-hidden');
      native.setAttribute('tabindex', '-1');
      native.setAttribute('aria-hidden', 'true');

      // Wrapper + disparador
      this.wrapper = el('div', 'cs-wrapper');
      native.parentNode.insertBefore(this.wrapper, native);
      this.wrapper.appendChild(native);

      this.button = el('button', 'cs-trigger');
      this.button.type = 'button';
      this.button.setAttribute('role', 'combobox');
      this.button.setAttribute('aria-haspopup', 'listbox');
      this.button.setAttribute('aria-expanded', 'false');
      this.button.setAttribute('aria-controls', `cs-list-${this.id}`);
      this.wrapper.appendChild(this.button);

      // Panel (se queda en <body>, oculto hasta que se abre)
      this.listbox = el('div', 'cs-listbox');
      this.listbox.id = `cs-list-${this.id}`;
      this.listbox.setAttribute('role', 'listbox');
      this.listbox.hidden = true;
      document.body.appendChild(this.listbox);

      this._renderOptions();
      this._syncButton();

      // --- Eventos del disparador (un solo camino: click) ---
      this.button.addEventListener('click', (e) => {
        e.preventDefault();
        this.toggle();
      });
      this.button.addEventListener('keydown', (e) => this._onKey(e));

      // Mantener el foco en el botón al interactuar con el panel
      this.listbox.addEventListener('mousedown', (e) => e.preventDefault());
      this.listbox.addEventListener('click', (e) => {
        const opt = e.target.closest('[role="option"]');
        if (opt) this._selectOption(opt);
      });
      this.listbox.addEventListener('mousemove', (e) => {
        const opt = e.target.closest('[role="option"]');
        if (opt) this._highlight(this.options.indexOf(opt), false);
      });

      // Cierre por clic fuera (pointerdown en captura: no depende del orden de click)
      this._onDocPointer = (e) => {
        if (!this.open) return;
        if (this.wrapper.contains(e.target) || this.listbox.contains(e.target)) return;
        this.close();
      };
      document.addEventListener('pointerdown', this._onDocPointer, true);

      // Si enfocan el <select> oculto (p. ej. clic en el <label for>), pasa el foco al botón
      native.addEventListener('focus', () => this.button.focus());

      // Opciones dinámicas (fetch de profesionales, etc.)
      this._observer = new MutationObserver(() => {
        this._renderOptions();
        this._syncButton();
      });
      this._observer.observe(native, { childList: true, subtree: true, characterData: true });

      // Cambios por teclado/otros scripts que sí emiten "change"
      native.addEventListener('change', () => this._syncButton());

      // Cambios programáticos: select.value = '' no emite evento
      const desc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
      Object.defineProperty(native, 'value', {
        configurable: true,
        get() { return desc.get.call(this); },
        set: (v) => { desc.set.call(native, v); this._syncButton(); }
      });
      const idxDesc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'selectedIndex');
      Object.defineProperty(native, 'selectedIndex', {
        configurable: true,
        get() { return idxDesc.get.call(this); },
        set: (v) => { idxDesc.set.call(native, v); this._syncButton(); }
      });

      // Reset del formulario
      const form = native.closest('form');
      if (form) form.addEventListener('reset', () => setTimeout(() => this._syncButton(), 0));

      native._customSelect = this;
    }

    // ---------- Render ----------
    _selectedOption() {
      const i = this.native.selectedIndex;
      return i >= 0 ? this.native.options[i] : null;
    }

    _renderOptions() {
      const real = Array.from(this.native.options).filter(o => o.value !== '');
      this.listbox.textContent = '';
      this.options = [];
      this.activeIdx = -1;

      if (!real.length) {
        const msg = /profesional/i.test(this.id)
          ? 'No hay profesionales disponibles por ahora'
          : 'No hay opciones disponibles por ahora';
        this.listbox.appendChild(el('div', 'cs-empty', msg));
        return;
      }

      const selected = this._selectedOption();
      real.forEach((opt, n) => {
        const item = el('div', 'cs-option');
        item.setAttribute('role', 'option');
        item.id = `${this.id}-opt-${n}`;
        item.dataset.value = opt.value;
        item.setAttribute('aria-selected', String(opt === selected));

        if (this.isTipo) {
          item.appendChild(faIcon(ICON_MAP[opt.text.trim()] || 'fa-circle', 'cs-opt-icon'));
          item.appendChild(el('span', '', opt.text.trim()));
        } else {
          const { name, specialty } = splitName(opt.text);
          item.appendChild(avatar(name));
          const info = el('div', 'cs-prof-info');
          info.appendChild(el('span', 'cs-prof-name', name));
          if (specialty) info.appendChild(el('span', 'cs-prof-spec', specialty));
          item.appendChild(info);
        }
        this.listbox.appendChild(item);
        this.options.push(item);
      });
    }

    _syncButton() {
      const sel = this._selectedOption();
      const hasValue = !!(sel && sel.value !== '');

      this.button.textContent = '';
      if (!hasValue) {
        this.button.appendChild(el('span', 'cs-placeholder', this.placeholder));
      } else if (this.isTipo) {
        const txt = sel.text.trim();
        this.button.appendChild(faIcon(ICON_MAP[txt] || 'fa-circle', 'cs-sel-icon'));
        this.button.appendChild(el('span', 'cs-value', txt));
      } else {
        const { name } = splitName(sel.text);
        this.button.appendChild(avatar(name));
        this.button.appendChild(el('span', 'cs-value', name));
      }
      this.button.appendChild(faIcon('fa-chevron-down', 'cs-arrow'));

      // Marcar la opción realmente seleccionada
      this.options.forEach(o => o.setAttribute(
        'aria-selected', String(hasValue && o.dataset.value === sel.value)
      ));
    }

    // ---------- Abrir / cerrar ----------
    toggle() { this.open ? this.close() : this.openPanel(); }

    openPanel() {
      if (this.open) return;

      // Cerrar cualquier otro desplegable abierto
      document.querySelectorAll('select[data-custom-select]').forEach(s => {
        if (s._customSelect && s._customSelect !== this) s._customSelect.close();
      });

      const lb = this.listbox;
      lb.hidden = false;
      lb.style.visibility = 'hidden';       // medir sin mostrar
      lb.classList.remove('cs-show');

      // Si no cabe debajo, desplazar la página (instantáneo, síncrono)
      const need = Math.min(MAX_H, lb.scrollHeight) + GAP + EDGE;
      let rect = this.button.getBoundingClientRect();
      const below = window.innerHeight - rect.bottom;
      if (below < need) {
        const maxScroll = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
        const delta = Math.min(need - below, Math.max(0, maxScroll));
        if (delta > 0) window.scrollBy({ top: delta, behavior: 'instant' });
      }

      this.open = true;                      // ← se marca abierto SIEMPRE
      this.wrapper.classList.add('cs-open');
      this.button.setAttribute('aria-expanded', 'true');
      this._place();
      lb.style.visibility = '';
      void lb.offsetHeight;                  // reflow para animar la entrada
      lb.classList.add('cs-show');

      // Resaltar la opción seleccionada (o la primera)
      const selIdx = this.options.findIndex(o => o.getAttribute('aria-selected') === 'true');
      this._highlight(selIdx >= 0 ? selIdx : 0, true);

      this._onResize = () => this._place();
      this._onScroll = () => this._place();
      window.addEventListener('resize', this._onResize);
      document.addEventListener('scroll', this._onScroll, { capture: true, passive: true });
    }

    _place() {
      if (!this.open) return;
      const rect = this.button.getBoundingClientRect();
      if (rect.bottom < 0 || rect.top > window.innerHeight) { this.close(); return; }

      const lb = this.listbox;
      const content = Math.min(MAX_H, lb.scrollHeight);
      const below = window.innerHeight - rect.bottom - GAP - EDGE;
      const above = rect.top - GAP - EDGE;
      const openUp = below < Math.min(content, 160) && above > below;

      const room = openUp ? above : below;
      let maxH = Math.min(MAX_H, Math.max(120, room));

      // Evitar que el último ítem quede cortado a medias
      const first = this.options[0];
      const optH = first ? first.offsetHeight : 0;
      if (optH && room < content) {
        maxH = Math.max(optH * 2, Math.floor(maxH / optH) * optH);
      }

      lb.style.position  = 'fixed';
      lb.style.left      = `${rect.left}px`;
      lb.style.width     = `${rect.width}px`;
      lb.style.maxHeight = `${maxH}px`;
      if (openUp) {
        lb.style.top = 'auto';
        lb.style.bottom = `${window.innerHeight - rect.top + GAP}px`;
      } else {
        lb.style.bottom = 'auto';
        lb.style.top = `${rect.bottom + GAP}px`;
      }
    }

    close() {
      if (!this.open) return;
      this.open = false;
      this.wrapper.classList.remove('cs-open');
      this.button.setAttribute('aria-expanded', 'false');
      this.button.removeAttribute('aria-activedescendant');
      this.listbox.classList.remove('cs-show');
      this.listbox.hidden = true;
      window.removeEventListener('resize', this._onResize);
      document.removeEventListener('scroll', this._onScroll, { capture: true });
    }

    // ---------- Teclado (el foco siempre queda en el botón) ----------
    _onKey(e) {
      const k = e.key;
      if (!this.open) {
        if (k === 'Enter' || k === ' ' || k === 'ArrowDown' || k === 'ArrowUp') {
          e.preventDefault();
          this.openPanel();
        } else if (k.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
          this.openPanel();
          this._typeAhead(k);
        }
        return;
      }
      if (k === 'ArrowDown') { e.preventDefault(); this._highlight(this.activeIdx + 1, true); }
      else if (k === 'ArrowUp') { e.preventDefault(); this._highlight(this.activeIdx - 1, true); }
      else if (k === 'Home') { e.preventDefault(); this._highlight(0, true); }
      else if (k === 'End') { e.preventDefault(); this._highlight(this.options.length - 1, true); }
      else if (k === 'Enter' || k === ' ') { e.preventDefault(); this._selectOption(this.options[this.activeIdx]); }
      else if (k === 'Escape') { e.preventDefault(); this.close(); }
      else if (k === 'Tab') { this.close(); }
      else if (k.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) { this._typeAhead(k); }
    }

    _typeAhead(ch) {
      const now = Date.now();
      this._typed = (now - this._typedAt > 700 ? '' : this._typed) + ch.toLowerCase();
      this._typedAt = now;
      const idx = this.options.findIndex(o => o.textContent.trim().toLowerCase().startsWith(this._typed));
      if (idx >= 0) this._highlight(idx, true);
    }

    _highlight(idx, scroll) {
      if (!this.options.length) return;
      idx = Math.max(0, Math.min(idx, this.options.length - 1));
      this.options.forEach((o, i) => o.classList.toggle('cs-highlight', i === idx));
      this.activeIdx = idx;
      this.button.setAttribute('aria-activedescendant', this.options[idx].id);
      if (scroll) this.options[idx].scrollIntoView({ block: 'nearest' });
    }

    // ---------- Selección ----------
    _selectOption(optEl) {
      if (!optEl) return;
      const changed = this.native.value !== optEl.dataset.value;
      this.native.value = optEl.dataset.value;       // el setter ya sincroniza el botón
      if (changed) this.native.dispatchEvent(new Event('change', { bubbles: true }));
      this.close();
      this.button.focus();
    }
  }

  // ---------- Auto-inicio ----------
  const init = () => document
    .querySelectorAll('select[data-custom-select]')
    .forEach(sel => { if (!sel._customSelect) new CustomSelect(sel); });

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  window.PsyCustomSelect = { init };
})();