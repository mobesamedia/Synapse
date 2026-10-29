// Synthetic HTML audio bridge; no SoundCloud/network/user-profile access.
const {chromium}=require('playwright'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const token='soundcloud-audio-unit-test';
const shim=fs.readFileSync(path.resolve(__dirname,'../soundcloud_native_audio.js'),'utf8').replace('__SYNAPSE_AUDIO_TOKEN__',JSON.stringify(token));
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});try{
 for(const unsupported of [false,true]){
  const page=await browser.newPage(),messages=[],errors=[];
  page.on('console',message=>{if(message.text().startsWith('SCNATIVE:'))messages.push(JSON.parse(message.text().slice(9)))});
  page.on('pageerror',e=>errors.push(e.message));
  if(unsupported)await page.addInitScript(()=>{const original=HTMLMediaElement.prototype.canPlayType;HTMLMediaElement.prototype.canPlayType=function(type){return /mp4a/.test(type)?'':original.call(this,type)};});
  await page.route('https://audio-host.test/',route=>route.fulfill({contentType:'text/html',body:'<iframe id="scplayer" src="https://w.soundcloud.com/player/"></iframe>'}));
  await page.route('https://w.soundcloud.com/player/',route=>route.fulfill({contentType:'text/html',body:'<script>'+shim+'</script><script>window.audio=new Audio();</script>'}));
  await page.goto('https://audio-host.test/');
  const frame=page.frames().find(frame=>frame.url().startsWith('https://w.soundcloud.com/'));
  assert.ok(frame);
  if(!unsupported){assert.equal(messages.length,0);assert.ok(!(await frame.evaluate(()=>navigator.userAgent)).includes('iPhone'));await page.close();continue;}
  assert.equal(messages[0].command,'init');
  const session=messages[0].session;
  await frame.evaluate(()=>{audio.src='https://playback.media-streaming.soundcloud.cloud/test/playlist.m3u8';});
  await page.waitForTimeout(25);
  const load=messages.find(message=>message.command==='load');assert.ok(load);
  assert.equal(await frame.evaluate(()=>audio.paused),true);
  assert.ok((await page.evaluate(()=>navigator.userAgent)).includes('Chrome'));
  async function reply(event,extra={}){await page.evaluate(payload=>document.getElementById('scplayer').contentWindow.postMessage(payload,'https://w.soundcloud.com'),{type:'synapse-native-audio',token,session,id:load.id,event,...extra});await page.waitForTimeout(25);}
  await reply('metadata',{duration:120});assert.equal(await frame.evaluate(()=>audio.duration),120);
  assert.equal(await frame.evaluate(()=>audio.buffered.length),0);
  await reply('buffer',{ranges:[[0,20]]});assert.equal(await frame.evaluate(()=>audio.buffered.end(0)),20);
  await frame.evaluate(()=>{window.playResult='pending';audio.play().then(()=>playResult='resolved',()=>playResult='rejected');});
  await reply('playing',{session:'stale-session'});assert.equal(await frame.evaluate(()=>audio.paused),true);
  await reply('playing');assert.equal(await frame.evaluate(()=>audio.paused),false);assert.equal(await frame.evaluate(()=>playResult),'resolved');
  await reply('position',{position:12});assert.equal(await frame.evaluate(()=>audio.currentTime),12);
  await frame.evaluate(()=>{audio.currentTime=30;audio.volume=.23;});await reply('position',{position:30});assert.equal(await frame.evaluate(()=>audio.seeking),false);
  assert.ok(messages.some(message=>message.command==='seek'&&message.position===30));assert.ok(messages.some(message=>message.command==='volume'&&Math.abs(message.volume-.23)<.01));
  await frame.evaluate(()=>audio.pause());await reply('pause');assert.equal(await frame.evaluate(()=>audio.paused),true);
  await reply('ended');assert.equal(await frame.evaluate(()=>audio.ended),true);
  await frame.evaluate(()=>{window.playResult='pending';audio.play().then(()=>playResult='resolved',()=>playResult='rejected');});await reply('error');assert.equal(await frame.evaluate(()=>playResult),'rejected');assert.equal(await frame.evaluate(()=>audio.error.code),4);
  await frame.evaluate(()=>{audio.removeAttribute('src');audio.load();});await page.waitForTimeout(25);assert.ok(messages.some(message=>message.command==='dispose'));
  assert.deepEqual(errors,[]);await page.close();
 }
 console.log('PASS native HLS bridge events, play/pause, seek, volume, errors, stale sessions, source disposal; supported browsers and host page unchanged');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
