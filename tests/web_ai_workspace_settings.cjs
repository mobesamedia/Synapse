const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
try{
const page=await browser.newPage({viewport:{width:400,height:760}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto('file://'+path.resolve(__dirname,'../chat_ui.html'));
await page.evaluate(()=>{
 document.getElementById('settings-panel').classList.add('open');
 window.sent=[];window.sendToPython=(action,data)=>sent.push({action,data});
});
await page.getByRole('tab',{name:'Layout',exact:true}).click();
assert(await page.locator('#ai-basic-settings').isHidden());
await page.selectOption('#s-lineheight','1.35');await page.selectOption('#s-messagegap','6');await page.selectOption('#s-fontsize','15px');await page.locator('.s-save').click();
assert.equal(await page.evaluate(()=>sent[0].data.lineHeight),1.35);
assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--chat-message-gap')),'6px');
await page.evaluate(()=>{startAIBubble();appendChunk(String.raw`Integral: \(\int_0^`);appendChunk(String.raw`1 x^2\,dx=\frac13\)`);finalizeResponse();});
assert.equal(await page.locator('#chat .katex').count(),1);
await page.evaluate(()=>{document.getElementById('settings-panel').classList.add('open');setSettingsTab('layout');});
await page.screenshot({path:'/tmp/ai-layout-settings.png'});
await page.evaluate(()=>{document.body.innerHTML='<div class="bubble" id="result"></div>';document.getElementById('result').innerHTML=renderMarkdown(String.raw`Fraction: \(\frac{a_1}{b^2}\). $$\begin{pmatrix}1&2\\3&4\end{pmatrix}$$`);});
assert.equal(await page.locator('.katex').count(),2);assert.equal(await page.locator('.katex-error').count(),0);
await page.evaluate(()=>document.getElementById('result').innerHTML=renderMarkdown('`$x$`\n```tex\n\\frac{a}{b}\n```\n<img src=x onerror=alert(1)>'));
assert.equal(await page.locator('.katex').count(),0);assert.equal(await page.locator('code').count(),2);assert.equal(await page.locator('img').count(),0);
await page.evaluate(()=>document.getElementById('result').innerHTML=renderMarkdown(String.raw`\(\href{javascript:alert(1)}{click}\)`));assert.equal(await page.locator('a').count(),0);
const fn=fs.readFileSync(path.resolve(__dirname,'../workspace_settings.js'),'utf8');
for(const group of ['maps','notebook'])for(const dark of [false,true]){
 const values=group==='maps'?{mindmap:true,roadmap:true}:{notebook:true,todo:true,pdf:true};
 await page.evaluate(({fn,group,values,dark})=>{
 window.commands=[];window.__synapseMindmapCommand=c=>commands.push(c);window.pycmd=c=>commands.push(c);
 (0,eval)('('+fn+')')({group,values,labels:{mindmap:'MindMap',roadmap:'FreeMap',notebook:'Notebook',todo:'To-Do',pdf:'PDF'},title:'Workspace settings',description:'Choose which tabs are visible. Hiding a tab does not delete its data.',save:'Save',cancel:'Cancel',colors:{bg:dark?'#2c2c2c':'#fff',text:dark?'#fff':'#222',surface:dark?'#252525':'#f5f5f5',grey_light:dark?'#414141':'#eee',blue_accent:'#577b9a'}});
 },{fn,group,values,dark});
 assert.equal(Math.round((await page.locator('dialog').boundingBox()).y),10);
 const checks=page.locator('dialog input');for(let i=0;i<await checks.count();i++)await checks.nth(i).uncheck();assert(await page.getByRole('button',{name:'Save',exact:true}).isDisabled());await checks.last().check();await page.getByRole('button',{name:'Save',exact:true}).click();
 assert.equal(await page.evaluate(()=>commands.length),1);
 await page.evaluate(()=>synapseWorkspaceSettingsError('Try again'));assert(await page.getByRole('button',{name:'Cancel',exact:true}).isEnabled());
 await page.screenshot({path:`/tmp/workspace-${group}-${dark?'dark':'light'}.png`});
 await page.getByRole('button',{name:'Cancel',exact:true}).click();await page.waitForFunction(()=>!document.querySelector('dialog'));
}
assert.deepEqual(errors,[]);console.log('PASS local formulas, code isolation, HTML safety, layout tabs/save, embedded workspace menus, validation and errors in both themes');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
