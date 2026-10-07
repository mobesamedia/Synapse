// Exercise the actual JS allowlist and queue, not a replacement command function.
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const sent=[],errors=[];let script;
const context={URLSearchParams,console,setTimeout,clearTimeout,window:null,top:null,qt:{webChannelTransport:{}},document:{readyState:'complete',createElement:()=>({}),head:{append:s=>script=s}},QWebChannel:function(transport,ready){ready({objects:{mindmapHost:{send:command=>sent.push(command)}}})}};
context.window=context;context.top=context;context.__SYNAPSE_MM_HOSTED__=true;context.__workspaceError=text=>errors.push(text);context.workspaceText=x=>x;vm.createContext(context);
for(const file of ['host_bridge.js','workspace_links.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../web_roadmap',file),'utf8'),context);
const seed="O'Brien · Größe · 心臓";context.workspacePickLinks([],seed,()=>{});assert.equal(sent.length,0);script.onload();assert.equal(sent.length,1);assert.match(sent[0],/^anki-links:/);const request=JSON.parse(decodeURIComponent(sent[0].slice(11)));assert.equal(request.seed,seed);
context.__workspaceLinksPicked({requestId:request.requestId,links:null});
const link={version:1,kind:'note',noteGuid:'safe-guid',noteId:'123',label:'Topic'};context.workspaceOpenLink(link);assert.match(sent[1],/^anki-open:/);
assert.equal(context.__synapseMindmapCommand('settings'),true);
for(const invalid of ['anki-open:javascript:alert(1)','arbitrary-command','anki-links:'+'a'.repeat(61000),null])assert.equal(context.__synapseMindmapCommand(invalid),false);
assert.equal(context.__synapseMindmapCommand('settings-save:'+encodeURIComponent(JSON.stringify({mindmap:true,roadmap:false}))),true);assert.equal(sent.length,4);assert.deepEqual(errors,[]);console.log('PASS actual host allowlist/queue, Link Card encoded Unicode payload, link open, reject invalid/oversized commands');
