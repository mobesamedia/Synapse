/* Qt controls must not use location.href: rejected navigation emits a failed
   load in WebEngine and non-gesture requests (autosave) may be blocked entirely. */
(() => {
    const hosted = window.__SYNAPSE_MM_HOSTED__ || window.__ROADMAP_HOSTED__;
    let host = null;
    const pending = new Set();
    const allowed = /^(switch:(mindmap|roadmap)|tutorial-init:[01]|roadmap-save|roadmap-export|workspace-export|workspace-import|image-add|settings|fullscreen|exitfullscreen|window|exitwindow)$/;
    window.__synapseMindmapCommand = command => {
        if (!hosted || window !== top || typeof command!=='string' || command.length>60050 || !(allowed.test(command)||/^(anki-(links|open)|settings-save):[A-Za-z0-9%_.!~*'()\-]+$/.test(command))) return false;
        if (host) host.send(command);
        else pending.add(command);
        return true;
    };
    if (!hosted || window !== top) return;
    const script = document.createElement('script');
    script.src = 'qrc:///qtwebchannel/qwebchannel.js';
    script.onload = () => {
        new QWebChannel(qt.webChannelTransport, channel => {
            host = channel.objects.mindmapHost;
            for (const command of pending) host.send(command);
            pending.clear();
        });
    };
    script.onerror = () => {
        const report = () => {
            const message = window.workspaceText('Could not connect to Anki. Please reopen the sidebar.');
            if (window.__mmToast) window.__mmToast(message, 'error', 9000);
            else {
                const status = document.getElementById('save-status');
                if (status) status.textContent = message;
            }
        };
        if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', report, {once:true});
        else report();
    };
    document.head.append(script);
})();
