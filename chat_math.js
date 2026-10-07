/* Local, untrusted-response renderer. Protect code and TeX from Markdown rewrites. */
(() => {
    const escape = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    const cache = new Map();
    function math(source, display, original) {
        if (!window.katex || source.length>12000) return escape(original);
        const key=JSON.stringify([source,display]);
        if(cache.has(key))return cache.get(key);
        let html;
        try {html=window.katex.renderToString(source,{displayMode:display,throwOnError:false,trust:false,maxExpand:500,maxSize:20,strict:'ignore',errorColor:'#b75e5e'});}
        catch (_) {return escape(original);}
        if(cache.size>=100)cache.delete(cache.keys().next().value);
        cache.set(key,html);return html;
    }
    window.synapseRenderMarkdown = raw => {
        // Strip our private placeholders from raw input so content cannot forge tokens.
        let s=String(raw||'').replace(/[\uE000\uE001]/g,'');
        const tokens=[];
        const token=html=>'\uE000'+(tokens.push(html)-1)+'\uE001';
        s=s.replace(/```[^\n`]*\n?([\s\S]*?)(?:```|$)/g,(_,code)=>token('<pre><code>'+escape(code.trim())+'</code></pre>'));
        s=s.replace(/`([^`\n]+)`/g,(_,code)=>token('<code>'+escape(code)+'</code>'));
        s=s.replace(/\\\[([\s\S]*?)\\\]|\$\$([\s\S]*?)\$\$|\\\(([\s\S]*?)\\\)/g,(all,bracket,dollar,inline)=>token(math(bracket??dollar??inline,inline===undefined,all)));
        // Avoid interpreting escaped dollar signs and ordinary prices as formulas.
        s=s.replace(/(^|[^\\$])\$([^\s$](?:[^$\n]*?[^\s$])?)\$(?!\d)/g,(all,prefix,tex)=>{
            if(/^\d[\d.,]*(?:\s|$)/.test(tex))return all;
            return prefix+token(math(tex,false,'$'+tex+'$'));
        });
        s=escape(s);
        s=s.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\*([^*\n]+)\*/g,'<em>$1</em>');
        s=s.replace(/(?:^|\n)[-•]\s+(.+)/g,'\n<li>$1</li>').replace(/(<li>[\s\S]+?<\/li>)+/g,'<ul>$&</ul>');
        s=s.replace(/(?:^|\n)\d+\.\s+(.+)/g,'\n<li>$1</li>').replace(/(?:^|\n)#{1,3}\s+(.+)/g,'\n<strong>$1</strong>');
        return s.replace(/\n/g,'<br>').replace(/\uE000(\d+)\uE001/g,(_,i)=>tokens[Number(i)]);
    };
})();
