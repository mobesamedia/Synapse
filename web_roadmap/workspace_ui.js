/* Shared visual controls for Mindmap and Roadmap. No persistence or host commands. */
(() => {
    document.documentElement.classList.toggle('dark',typeof window.__SYNAPSE_MM_DARK__==='boolean'?window.__SYNAPSE_MM_DARK__:matchMedia('(prefers-color-scheme: dark)').matches);
    const paths = {
        plus: '<path d="M12 5v14M5 12h14"/>',
        minus: '<path d="M5 12h14"/>',
        fit: '<path d="M8 4H4v4m12-4h4v4M4 16v4h4m12-4v4h-4"/><rect x="8" y="8" width="8" height="8" rx="1"/>',
        center: '<circle cx="12" cy="12" r="6"/><path d="M12 2v4m0 12v4M2 12h4m12 0h4"/>',
        hand: '<path d="M8 12V6a2 2 0 0 1 4 0v6-8a2 2 0 0 1 4 0v8-6a2 2 0 0 1 4 0v8c0 5-3 8-7 8-3 0-5-2-7-5l-3-4a2 2 0 0 1 3-2l2 2"/>',
        auto: '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/><path d="m9 8 2 8 2-3 3-2-7-3Z"/>',
        menu: '<path d="M5 6h14M5 12h14M5 18h14"/>',
        rename: '<path d="m4 16 12-12 4 4L8 20H4v-4ZM14 6l4 4"/>',
        duplicate: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V4H4v12h4"/>',
        export: '<path d="M12 3v12m-4-4 4 4 4-4M5 17v4h14v-4"/>',
        import: '<path d="M12 15V3m-4 4 4-4 4 4M5 17v4h14v-4"/>',
        delete: '<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>'
    };
    const icon = key => `<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${paths[key]}</svg>`;
    const grids = new Map();
    window.__workspaceGrid = (element, view) => {
        grids.set(element, {...view});
        const size = 20 * view.scale;
        const opacity = Math.min(1, Math.max(0, (view.scale - .2) / .5));
        const dark = document.documentElement.classList.contains('dark');
        element.style.backgroundSize = `${size}px ${size}px`;
        element.style.backgroundPosition = `${view.x % size}px ${view.y % size}px`;
        element.style.backgroundImage = `radial-gradient(rgba(${dark ? '96,96,96' : '215,215,215'},${opacity}) 1px, transparent 0)`;
    };
    const refreshGrid = () => grids.forEach((view, element) => window.__workspaceGrid(element, view));
    new MutationObserver(refreshGrid).observe(document.documentElement, {attributes:true, attributeFilter:['class']});
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event=>{if(typeof window.__SYNAPSE_MM_DARK__!=='boolean')document.documentElement.classList.toggle('dark',event.matches);refreshGrid();});
    window.__mindmapSaveStatus = state => {
        const status = document.getElementById('mindmap-save-status');
        if (!status) return;
        const labels = {saved:window.workspaceText('Saved'), pending:window.workspaceText('Saving...'), error:window.workspaceText('Save failed')};
        status.textContent = window.__SYNAPSE_MM_I18N__?.['save_status_' + state] || labels[state];
        status.dataset.state = state;
    };
    function mapSelector(select, id) {
        if (!select) return;
        const button = document.createElement('button');
        button.id = id + '-btn';
        button.className = 'workspace-map-select';
        button.type = 'button';
        button.setAttribute('aria-haspopup', 'listbox');
        button.setAttribute('aria-expanded', 'false');
        select.after(button);
        let menu;
        function sync() {
            const label = select.options[select.selectedIndex]?.textContent || '…';
            button.textContent = label;
            button.title = label;
            button.disabled = select.disabled;
        }
        function close() { menu?.remove(); menu = null; button.setAttribute('aria-expanded', 'false'); }
        function open() {
            close();
            menu = document.createElement('div');
            menu.className = 'workspace-map-menu';
            menu.id = id + '-menu';
            menu.setAttribute('role','listbox');
            menu.setAttribute('aria-label', window.workspaceText('Select document'));
            for (const option of select.options) {
                const item = document.createElement('button');
                item.type = 'button';
                item.className = 'workspace-map-option' + (option.selected ? ' selected' : '');
                item.textContent = option.textContent;
                item.setAttribute('role','option');
                item.setAttribute('aria-selected', String(option.selected));
                item.onclick = event => {
                    event.stopPropagation(); select.value = option.value; sync(); close();
                    select.dispatchEvent(new Event('change')); button.focus();
                };
                menu.append(item);
            }
            document.body.append(menu);
            const r = button.getBoundingClientRect();
            menu.style.minWidth = Math.max(r.width, 160) + 'px';
            menu.style.maxWidth = Math.max(160, innerWidth - 16) + 'px';
            menu.style.left = Math.max(8, Math.min(r.left, innerWidth-menu.offsetWidth-8)) + 'px';
            menu.style.top = (r.bottom + 4) + 'px';
            menu.style.maxHeight = Math.max(80, Math.min(300, innerHeight-r.bottom-12)) + 'px';
            button.setAttribute('aria-expanded','true');
            menu.querySelector('.selected')?.scrollIntoView({block:'nearest'});
        }
        button.onclick = event => { event.stopPropagation(); menu ? close() : open(); };
        button.onkeydown = event => {
            if (event.key === 'ArrowDown') { event.preventDefault(); open(); menu.querySelector('button')?.focus(); }
        };
        document.addEventListener('keydown', event => {
            if (!menu) return;
            if (event.key === 'Escape') { close(); button.focus(); }
            else if (['ArrowDown','ArrowUp'].includes(event.key) && menu.contains(document.activeElement)) {
                event.preventDefault(); const items = [...menu.children];
                items[(items.indexOf(document.activeElement) + (event.key==='ArrowDown'?1:items.length-1)) % items.length].focus();
            }
        });
        document.addEventListener('click', event => { if (!menu?.contains(event.target)) close(); });
        window.addEventListener('resize', close);
        select.addEventListener('change', sync);
        new MutationObserver(sync).observe(select,{childList:true,subtree:true,attributes:true});
        sync();
    }
    document.addEventListener('DOMContentLoaded', () => {
        for (const [selector, name] of Object.entries({
            '#zoom-in-btn':'plus','#zoom-in':'plus','#zoom-out-btn':'minus','#zoom-out':'minus',
            '#fit-map-btn':'fit','#fit':'fit','#center-view-btn':'center','#center':'center',
            '#add-menu > summary':'plus','[data-mode="hand"]':'hand','[data-mode="auto"]':'auto',
            '#hamburger-btn':'menu','#document-menu > summary':'menu'
        })) {
            const button = document.querySelector(selector);
            if (!button) continue;
            if (name === 'center') {
                button.removeAttribute('data-i18n');
                const label = document.createElement('span');
                label.textContent = window.__SYNAPSE_MM_I18N__?.center_view || window.workspaceText('Center view');
                label.setAttribute('data-i18n','center_view');
                button.innerHTML = icon(name); button.append(label);
            } else button.innerHTML = icon(name);
        }
        for (const [selector, name] of Object.entries({'#import-btn':'import','#export-btn':'export','#delete-map-btn':'delete'})) {
            const slot = document.querySelector(selector + ' .dropdown-icon');
            if (slot) slot.innerHTML = icon(name);
        }
        for (const button of document.querySelectorAll('#document-menu [data-doc]')) {
            const name = button.dataset.doc;
            if (paths[name]) { const text = document.createElement('span'); text.textContent=button.textContent; button.innerHTML=icon(name); button.append(text); }
        }
        mapSelector(document.getElementById('mindmap-select'), 'mindmap-select');
        mapSelector(document.getElementById('map-select'), 'map-select');
        window.__mindmapSaveStatus('saved');
    });
})();
