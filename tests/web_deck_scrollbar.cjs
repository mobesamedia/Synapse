const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

(async () => {
    const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'synapse-deck-scrollbar-'));
    const browser = await chromium.launch({
        headless: true,
        ignoreDefaultArgs: ['--hide-scrollbars'],
        executablePath: process.env.SYNAPSE_TEST_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    });
    try {
        const themes = path.resolve(__dirname, '../theme/user_files');
        const page = await browser.newPage({ viewport: { width: 1100, height: 640 } });
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const fixture = path.join(temporary, 'decks.html');
        const load = async (theme, dark, count, overview = false) => {
            const rows = Array.from({ length: count }, (_, index) => `<tr><td style="padding:12px 20px">${index % 5 ? '　↳ Subdeck ' : 'Deck '}${index + 1}</td><td>12</td><td>34</td></tr>`).join('');
            fs.writeFileSync(fixture, `<!DOCTYPE html><link rel="stylesheet" href="${pathToFileURL(path.join(themes, theme)).href}"><body class="${overview ? 'overview' : 'deckbrowser'} ${dark ? 'nightMode' : ''}">${overview ? '<main id="custom-dashboard">' : ''}<div class="decks-container"><table style="width:100%">${rows}</table></div>${overview ? '</main>' : ''}`);
            await page.goto(pathToFileURL(fixture).href);
        };
        for (const theme of fs.readdirSync(themes).filter(name => name.endsWith('.css'))) {
            for (const dark of [false, true]) {
                await load(theme, dark, 75);
                const scrollbar = await page.evaluate(() => {
                    const style = getComputedStyle(document.documentElement, '::-webkit-scrollbar');
                    const thumb = getComputedStyle(document.documentElement, '::-webkit-scrollbar-thumb');
                    return { width: style.width, display: style.display, thumb: thumb.backgroundColor };
                });
                assert.equal(scrollbar.width, '12px', theme);
                assert.notEqual(scrollbar.display, 'none', theme);
                assert.notEqual(scrollbar.thumb, 'rgba(0, 0, 0, 0)', theme);
                assert.ok(await page.evaluate(() => document.scrollingElement.scrollHeight > innerHeight), theme);
                await page.mouse.move(550, 300);
                await page.mouse.wheel(0, 480);
                await page.waitForFunction(() => scrollY > 100);
                const down = await page.evaluate(() => scrollY);
                await page.mouse.wheel(0, -360);
                await page.waitForFunction(previous => scrollY < previous - 100, down);
                if (theme === 'medical_theme.css') {
                    await page.evaluate(() => scrollTo(0, 0));
                    await page.waitForFunction(() => scrollY === 0);
                    const thumbHeight = await page.evaluate(() => innerHeight * innerHeight / document.scrollingElement.scrollHeight);
                    await page.mouse.move(1094, thumbHeight / 2);
                    await page.mouse.down();
                    await page.mouse.move(1094, 420, { steps: 12 });
                    await page.mouse.up();
                    await page.waitForFunction(() => scrollY > 500);
                }
                await load(theme, dark, 2);
                assert.equal(await page.evaluate(() => document.scrollingElement.scrollHeight > innerHeight), false, theme + ' short list');
                assert.equal(await page.evaluate(() => document.documentElement.clientWidth), 1100, theme + ' short list needs no scrollbar');
            }
        }
        for (const dark of [false, true]) {
            await load('medical_theme.css', dark, 75, true);
            assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement, '::-webkit-scrollbar').width), '12px');
            await page.mouse.move(550, 300);
            await page.mouse.wheel(0, 480);
            await page.waitForFunction(() => scrollY > 100);
        }
        assert.deepEqual(errors, []);
        console.log('PASS all themes light/dark: visible scrollbar for long decks/subdecks, wheel up/down, mouse dragging, no scrollbar for short lists, overview scrolling');
    } finally {
        await browser.close();
        fs.rmSync(temporary, { recursive: true, force: true });
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
