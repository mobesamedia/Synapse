const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {pathToFileURL}=require('node:url');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.SYNAPSE_TEST_CHROME});
 try{
  const page=await browser.newPage({viewport:{width:980,height:760}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const fixture=JSON.parse(fs.readFileSync('/tmp/synapse-review-background-fixture.json'));
  await page.setContent('<style>'+fixture.reviewerCss+'</style><style>'+fixture.css+'</style><style>.card{font:20px Arial;background-color:white;color:black}</style><body class="card"><div id="qa">Question</div></body>');
  assert.match(await page.locator('body').evaluate(e=>getComputedStyle(e).backgroundImage),/data:image/);
  assert.equal(await page.locator('body').evaluate(e=>getComputedStyle(e).backgroundPosition),'50% 50%');
  assert.equal(await page.locator('#qa').evaluate(e=>getComputedStyle(e).filter),'none');
  await page.evaluate(()=>document.getElementById('qa').innerHTML='Answer');
  assert.match(await page.locator('body').evaluate(e=>getComputedStyle(e).backgroundImage),/data:image/);
  await page.addStyleTag({content:'.card{background:rgb(50,60,70)}'});
  assert.equal(await page.locator('body').evaluate(e=>getComputedStyle(e).backgroundImage),'none');
  await page.evaluate(()=>document.body.style.background='rgb(10, 20, 30)');
  await page.evaluate(fixture.off);
  assert.equal(await page.locator('body').evaluate(e=>e.style.background),'rgb(10, 20, 30)');
  await page.evaluate(fixture.on);await page.evaluate(fixture.on);await page.evaluate(fixture.off);
  assert.equal(await page.locator('body').evaluate(e=>e.style.background),'rgb(10, 20, 30)');
  await page.goto(pathToFileURL(path.resolve(__dirname,'../settings_web/settings.html')).href);
  await page.evaluate(()=>{initSettings({config:{custom_background_enabled:true},initialPage:'appearance'});});
  await page.evaluate(preview=>updateCustomBackground({hasImage:true,preview}),fixture.css.match(/url\("(.*?)"\)/)[1]);
  // Identify the actual appearance navigation key rather than assuming a label.
  await page.evaluate(()=>gotoPage(document.getElementById('custom_background_enabled').closest('.page').dataset.page));
  assert.equal(await page.locator('#custom_background_review_enabled').isChecked(),false);
  await page.locator('#custom_background_review_enabled + .slider').click();
  assert.equal(await page.locator('#reviewBackgroundDialog').isVisible(),true);
  assert.equal(await page.locator('#custom_background_review_enabled').isChecked(),false);
  await page.keyboard.press('Escape');
  assert.equal(await page.locator('#custom_background_review_enabled').isChecked(),false);
  await page.locator('#custom_background_review_enabled + .slider').click();
  await page.locator('#reviewBackgroundDialog .btn-primary').click();
  assert.equal(await page.locator('#reviewBackgroundControls').isVisible(),true);
  assert.deepEqual(await page.evaluate(()=>[collect().custom_background_review_intensity,collect().custom_background_review_blur]),[20,8]);
  for(const dark of [false,true]){
   await page.evaluate(dark=>{document.documentElement.classList.toggle('dark',dark);document.body.classList.toggle('dark',dark)},dark);
   await page.locator('#reviewBackgroundControls').scrollIntoViewIfNeeded();
   await page.screenshot({path:'/tmp/review-background-settings-'+(dark?'dark':'light')+'.png'});
  }
  await page.locator('#custom_background_review_enabled + .slider').click();
  assert.equal(await page.locator('#reviewBackgroundControls').isVisible(),false);
  assert.equal(await page.evaluate(()=>collect().custom_background_review_enabled),false);
  assert.deepEqual(errors,[]);
  console.log('PASS card CSS compatibility, unchanged content, inline restoration, enable/cancel/disable, defaults and settings');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
