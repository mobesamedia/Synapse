(() => {
    window.workspaceText = text => window.__WORKSPACE_I18N__?.[text] || text;
    window.applyWorkspaceI18n = (root=document) => {
        const texts = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let node;
        while ((node=texts.nextNode())) {
            if (node.parentElement?.closest('script,style,#objects,#mindmap-viewport,#workspace-nav')) continue;
            const value=node.textContent.trim();
            if (window.__WORKSPACE_I18N__?.[value]) node.textContent=node.textContent.replace(value,workspaceText(value));
        }
        for (const e of root.querySelectorAll('[title],[aria-label]')) {
            for (const attr of ['title','aria-label']) if(e.hasAttribute(attr)) e.setAttribute(attr,workspaceText(e.getAttribute(attr)));
        }
    };
    document.addEventListener('DOMContentLoaded',()=>applyWorkspaceI18n());
})();
