// Separate toolbar documents, matching Anki's persistent top/bottom WebViews.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{pathToFileURL}=require('node:url');
(async()=>{const temp=fs.mkdtempSync(path.join(os.tmpdir(),'synapse-toolbar-test-')),browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 const root=path.resolve(__dirname,'..'),theme=path.join(root,'theme/user_files'),page=await browser.newPage({viewport:{width:1000,height:120}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const custom=path.join(temp,'custom.css');fs.writeFileSync(custom,fs.readFileSync(path.join(theme,'none.css'),'utf8').replace('medical_theme.css',pathToFileURL(path.join(theme,'medical_theme.css')).href).replaceAll('#f5f5f5','#aeeae0').replaceAll('#2c2c2c','#345678'));
 for(const dark of [false,true])for(const bar of ['top-toolbar','bottom-toolbar']){
  const file=path.join(temp,'fixture.html');fs.writeFileSync(file,'<!DOCTYPE html><style>:root{--canvas:'+(dark?'#2c2c2c':'#f5f5f5')+'}body{margin:0}.header{background:var(--canvas)}.toolbar{background:'+(dark?'#303030':'white')+'}#outer{background:var(--canvas)}</style><link rel="stylesheet" href="'+pathToFileURL(custom).href+'"><body class="'+bar+' '+(dark?'nightMode':'')+'"><div class="header"><div class="toolbar"><a id="decks">Decks</a> Add Browse</div></div><div id="outer"><table><tr><td>Create deck</td></tr></table></div>');await page.goto(pathToFileURL(file).href);
  const read=()=>page.evaluate(()=>({body:getComputedStyle(document.body).backgroundColor,html:getComputedStyle(document.documentElement).backgroundColor,pill:getComputedStyle(document.querySelector('.toolbar')).backgroundColor}));
  const original=await read();
  for(const state of ['deckBrowser','overview','review','deckBrowser']){
   await page.evaluate(state=>{document.body.classList.toggle('synapse-main-background',state==='deckBrowser'||state==='overview');document.body.classList.toggle('reviewing',state==='review');},state);
   const actual=await read();if(state==='review'){assert.equal(actual.body,dark?'rgb(44, 44, 44)':'rgb(245, 245, 245)');assert.equal(actual.html,actual.body);assert.equal(actual.pill,original.pill);}else{assert.equal(actual.body,dark?'rgb(52, 86, 120)':'rgb(174, 234, 224)');assert.equal(actual.html,actual.body);assert.equal(actual.pill,original.pill);assert.equal(await page.locator(bar==='top-toolbar'?'.header':'#outer').evaluate(el=>getComputedStyle(el).backgroundColor),'rgba(0, 0, 0, 0)');}
  }
 }
 for(const dark of [false,true])for(const bar of ['top-toolbar','bottom-toolbar']){
  const file=path.join(temp,'none-review.html');fs.writeFileSync(file,'<!DOCTYPE html><style>:root{--canvas:'+(dark?'#2c2c2c':'#f5f5f5')+'}.header{background:var(--canvas)}</style><link rel="stylesheet" href="'+pathToFileURL(path.join(theme,'none.css')).href+'"><body class="synapse-background-none reviewing '+bar+' '+(dark?'nightMode':'')+'"><div class="header">Toolbar</div>');await page.goto(pathToFileURL(file).href);
  const expected=bar==='top-toolbar'?(dark?'rgb(48, 48, 48)':'rgb(255, 255, 255)'):(dark?'rgb(44, 44, 44)':'rgb(245, 245, 245)');
  assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),expected);assert.equal(await page.evaluate(()=>getComputedStyle(document.documentElement).backgroundColor),expected);
  if(bar==='top-toolbar')assert.equal(await page.locator('.header').evaluate(el=>getComputedStyle(el).backgroundColor),expected);
 }
 assert.deepEqual(errors,[]);console.log('PASS solid top/bottom background on deckBrowser/overview, native Anki gray during review, return transitions and unchanged button surfaces in both modes');
}finally{await browser.close();fs.rmSync(temp,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1});
