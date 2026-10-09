/* ============================================================
   PsyAI Connect – Re‑usable Custom <select>
   Works on any <select data-custom-select>
   ------------------------------------------------------------
   • Keeps the native <select> as source of truth
   • Fires native “change” so existing JS (agendaquotes.js) stays intact
   • Re‑renders automatically when the native options change (MutationObserver)
   • Fully keyboard‑accessible, ARIA‑compliant, dark‑mode ready
   ============================================================ */
(() => {
  const ICON_MAP = {
    Ansiedad:               'fa-brain',
    Estrés:                 'fa-bolt',
    Depresión:              'fa-cloud-rain',
    Autoestima:             'fa-heart',
    Duelo:                  'fa-feather',
    'Trastornos del Sueño': 'fa-moon',
    Adicciones:             'fa-pills',
    'Orientación Emocional':'fa-compass',
    'Terapia de Pareja':    'fa-user-friends',
    Otro:                   'fa-ellipsis-h'
  };

  // ---------- Helpers ----------
  const hashColor = (str) => {
    let h = 0;
    for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
    const hue = Math.abs(h) % 360;
    return `hsl(${hue} 55% 45%)`;
  };

  const initials = (name) => name
    .trim()
    .split(/\s+/)
    .map(w => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  // ---------- Component ----------
  class CustomSelect {
    constructor(native) {
      this.native = native;
      this.wrapper = null;
      this.button = null;
      this.listbox = null;
      this.options = [];
      this.open = false;
      this.activeIdx = -1;
      // placeholder text (first empty option or data-placeholder)
      const emptyOpt = native.querySelector('option[value=""]');
      this.placeholder = native.dataset.placeholder || (emptyOpt ? emptyOpt.textContent.trim() : 'Seleccionar');
      this._init();
    }

    _init() {
      // hide native visually but keep in flow for validation
      this.native.classList.add('cs-native-hidden');

      // wrapper
      this.wrapper = document.createElement('div');
      this.wrapper.className = 'cs-wrapper';
      this.native.parentNode.insertBefore(this.wrapper, this.native);
      this.wrapper.appendChild(this.native);

      // trigger button
      this.button = document.createElement('button');
      this.button.type = 'button';
      this.button.className = 'cs-trigger';
      this.button.setAttribute('role', 'combobox');
      this.button.setAttribute('aria-haspopup', 'listbox');
      this.button.setAttribute('aria-expanded', 'false');
      this.button.setAttribute('aria-controls', `cs-list-${this.native.id}`);
      this.button.setAttribute('tabindex', '0');
      this.wrapper.appendChild(this.button);

      // listbox
      this.listbox = document.createElement('div');
      this.listbox.className = 'cs-listbox';
      this.listbox.setAttribute('role', 'listbox');
      this.listbox.id = `cs-list-${this.native.id}`;
      this.listbox.hidden = true;
      this.wrapper.appendChild(this.listbox);

      this._renderOptions();
      this._syncButton();

      // events
      this.button.addEventListener('click', () => this.toggle());
      this.button.addEventListener('keydown', e => this._onTriggerKey(e));
      this.listbox.addEventListener('click', e => {
        const opt = e.target.closest('[role="option"]');
        if (opt) this._selectOption(opt);
      });
      this.listbox.addEventListener('keydown', e => this._onListKey(e));

      document.addEventListener('click', e => {
        if (this.open && !this.wrapper.contains(e.target)) this.close();
      });

      // observe native select for dynamic options
      this._observer = new MutationObserver(() => this._renderOptions());
      this._observer.observe(this.native, { childList: true, subtree: true });
    }

    // ---------- Rendering ----------
    _renderOptions() {
      const opts = Array.from(this.native.options);
      this.listbox.innerHTML = '';
      this.options = [];

      if (opts.length === 1 && !opts[0].value) {
        const empty = document.createElement('div');
        empty.className = 'cs-empty';
        empty.textContent = 'No hay profesionales disponibles por ahora';
        this.listbox.appendChild(empty);
        return;
      }

      opts.forEach((opt, i) => {
        if (!opt.value && i === 0) return; // skip placeholder
        const el = document.createElement('div');
        el.className = 'cs-option';
        el.setAttribute('role', 'option');
        el.setAttribute('aria-selected', 'false');
        el.dataset.value = opt.value;
        el.id = `${this.native.id}-opt-${i}`;

        if (this.native.id === 'tipoCita') {
          const icon = ICON_MAP[opt.text] || 'fa-circle';
          el.innerHTML = `<i class="fas ${icon} cs-opt-icon"></i><span>${opt.text}</span>`;
        } else { // profesional
          const parts = opt.text.split(' - ');
          const name = parts[0];
          const specialty = parts[1] || '';
          const bg = hashColor(name);
          el.innerHTML = `
            <div class="cs-avatar" style="background:${bg}">${initials(name)}</div>
            <div class="cs-prof-info">
              <span class="cs-prof-name">${name}</span>
              ${specialty ? `<span class="cs-prof-spec">${specialty}</span>` : ''}
            </div>`;
        }
        this.listbox.appendChild(el);
        this.options.push(el);
      });
    }

    _syncButton() {
      const val = this.native.value;
      const selOpt = this.native.querySelector(`option[value="${val}"]`);
      if (!selOpt || !val) {
        this.button.innerHTML = `<span class="cs-placeholder">${this.placeholder}</span>
                                 <i class="fas fa-chevron-down cs-arrow"></i>`;
        return;
      }
      if (this.native.id === 'tipoCita') {
        const icon = ICON_MAP[selOpt.text] || 'fa-circle';
        this.button.innerHTML = `<i class="fas ${icon} cs-sel-icon"></i>
                                 <span>${selOpt.text}</span>
                                 <i class="fas fa-chevron-down cs-arrow"></i>`;
      } else {
        const parts = selOpt.text.split(' - ');
        const name = parts[0];
        const bg = hashColor(name);
        this.button.innerHTML = `<div class="cs-avatar" style="background:${bg}">${initials(name)}</div>
                                 <span>${name}</span>
                                 <i class="fas fa-chevron-down cs-arrow"></i>`;
      }
    }

    // ---------- Open / Close ----------
    toggle() { this.open ? this.close() : this.openPanel(); }

    openPanel() {
      // Ensure enough room below; scroll trigger into view if needed
      const rect = this.button.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      if (spaceBelow < 160) {
        this.button.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // recalc after scroll (next frame)
        requestAnimationFrame(() => this._doOpenPanel());
        return;
      }
      this._doOpenPanel();
    }

    _doOpenPanel() {
      const rect = this.button.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      const maxHeight = Math.min(280, Math.max(160, spaceBelow - 12));
      const openUp = spaceBelow < 160 && spaceAbove > spaceBelow;

      this.open = true;
      this.wrapper.classList.add('cs-open');
      this.button.setAttribute('aria-expanded', 'true');
      this.listbox.hidden = false;
      this.listbox.style.maxHeight = `${maxHeight}px`;

      if (openUp) {
        this.listbox.style.top = 'auto';
        this.listbox.style.bottom = '100%';
        this.listbox.style.marginBottom = '6px';
      } else {
        this.listbox.style.top = '100%';
        this.listbox.style.bottom = 'auto';
        this.listbox.style.marginTop = '6px';
      }
      this.listbox.style.minWidth = `${rect.width}px`;

      requestAnimationFrame(() => this.listbox.classList.add('cs-show'));
      this.activeIdx = -1;
      this._highlight(-1);
      window.addEventListener('resize', this._reposition.bind(this));
    }

    _reposition() {
      if (!this.open) return;
      const rect = this.button.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      const maxHeight = Math.min(280, Math.max(160, spaceBelow - 12));
      const openUp = spaceBelow < 160 && spaceAbove > spaceBelow;
      this.listbox.style.maxHeight = `${maxHeight}px`;
      if (openUp) {
        this.listbox.style.top = 'auto';
        this.listbox.style.bottom = '100%';
        this.listbox.style.marginBottom = '6px';
        this.listbox.style.marginTop = '';
      } else {
        this.listbox.style.top = '100%';
        this.listbox.style.bottom = 'auto';
        this.listbox.style.marginTop = '6px';
        this.listbox.style.marginBottom = '';
      }
      this.listbox.style.minWidth = `${rect.width}px`;
    }

    close() {
      this.open = false;
      this.wrapper.classList.remove('cs-open');
      this.button.setAttribute('aria-expanded', 'false');
      this.listbox.classList.remove('cs-show');
      setTimeout(() => { this.listbox.hidden = true; }, 160);
      window.removeEventListener('resize', this._reposition.bind(this));
    }

    // ---------- Keyboard ----------
    _onTriggerKey(e) {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
        e.preventDefault(); this.openPanel(); this._highlight(0);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault(); this.openPanel(); this._highlight(this.options.length - 1);
      } else if (e.key === 'Escape') this.close();
      else if (e.key.length === 1) this._jumpToLetter(e.key);
    }

    _onListKey(e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); this._highlight(this.activeIdx + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); this._highlight(this.activeIdx - 1); }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); this._selectOption(this.options[this.activeIdx]); }
      else if (e.key === 'Escape') { this.close(); this.button.focus(); }
      else if (e.key === 'Tab') { this.close(); }
      else if (e.key.length === 1) this._jumpToLetter(e.key);
    }

    _highlight(idx) {
      if (!this.options.length) return;
      idx = Math.max(0, Math.min(idx, this.options.length - 1));
      this.options.forEach((o, i) => {
        const sel = i === idx;
        o.setAttribute('aria-selected', sel);
        o.classList.toggle('cs-highlight', sel);
      });
      this.activeIdx = idx;
      this.options[idx]?.scrollIntoView({ block: 'nearest' });
    }

    _jumpToLetter(ch) {
      const lower = ch.toLowerCase();
      for (let i = 0; i < this.options.length; i++) {
        const txt = this.options[i].textContent.trim().toLowerCase();
        if (txt.startsWith(lower)) { this._highlight(i); break; }
      }
    }

    // ---------- Selection ----------
    _selectOption(optEl) {
      if (!optEl) return;
      const val = optEl.dataset.value;
      this.native.value = val;
      this.native.dispatchEvent(new Event('change', { bubbles: true }));
      this._syncButton();
      this.close();
      this.button.focus();
    }
  }

  // ---------- Auto‑init ----------
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('select[data-custom-select]').forEach(sel => new CustomSelect(sel));
  });
})();