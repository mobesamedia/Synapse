const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

(async () => {
    const browser = await chromium.launch({
        headless: true,
        executablePath: process.env.SYNAPSE_TEST_CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    });
    try {
        const page = await browser.newPage();
        await page.route('https://**/*', route => route.abort());
        await page.addInitScript(() => {
            window.auditCommands = [];
            window.pycmd = command => window.auditCommands.push(command);
        });
        await page.goto(pathToFileURL(path.resolve(__dirname, '../web_notebook/index.html')).href);
        const reset = async () => page.evaluate(() => {
            loadContent(JSON.stringify({ pages: [{ id: 'audit', title: 'Audit', blocks: [{ type: 'text', html: '' }] }], activePageId: 'audit' }));
            window.auditExecuted = false;
            window.auditCommands = [];
            notebookSecurityNotices.clear();
            document.getElementById('notebook-security-notice').hidden = true;
        });
        for (const htmlClipboard of [false, true]) {
            await reset();
            const payload = '[Link](https://example.invalid/" onmouseover="window.auditExecuted=true;pycmd`audit-injected`" data-extra=")';
            await page.locator('#editor > :first-child').focus();
            if (htmlClipboard) {
                await page.evaluate(payload => {
                    const clipboardData = new DataTransfer();
                    const holder = document.createElement('div');
                    holder.textContent = payload;
                    clipboardData.setData('text/html', holder.innerHTML);
                    editor.firstElementChild.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData }));
                }, payload);
                await page.keyboard.press('Space');
            } else {
                await page.keyboard.insertText(payload);
            }
            await page.locator('#editor > :first-child').hover();
            assert.equal(await page.evaluate(() => window.auditExecuted), false, 'Markdown must not create executable attributes');
            assert.equal(await page.evaluate(() => window.auditCommands.includes('audit-injected')), false, 'Markdown must not call the bridge');
            assert.equal(await page.locator('#editor [onmouseover]').count(), 0);
            assert.equal(await page.locator('#editor a').count(), 0);
            assert.equal(await page.locator('#notebook-security-notice').isVisible(), true);
            await page.getByRole('button', { name: 'Dismiss', exact: true }).click();
            assert.equal(await page.locator('#notebook-security-notice').isVisible(), false);
            await page.locator('#editor > :first-child').focus();
            await page.keyboard.press('Space');
            assert.equal(await page.locator('#notebook-security-notice').isVisible(), false);
        }
        await reset();
        await page.locator('#editor > :first-child').focus();
        await page.keyboard.insertText('[<img src=x onerror=alert>](https://example.invalid/)');
        assert.equal(await page.locator('#editor img').count(), 0);
        assert.equal(await page.locator('#editor a').textContent(), '<img src=x onerror=alert>');
        await reset();
        await page.evaluate(() => {
            const block = editor.firstElementChild;
            block.innerHTML = '<b>Keep bold</b> [One](https://example.invalid/one) and [Two](http://example.invalid/two?a=1&b=2) <code>[Code](https://example.invalid/code)</code>';
            block.dispatchEvent(new InputEvent('input', { bubbles: true }));
        });
        assert.equal(await page.locator('#editor b').textContent(), 'Keep bold');
        assert.equal(await page.locator('#editor a').count(), 2);
        assert.equal(await page.locator('#editor a').nth(1).getAttribute('href'), 'http://example.invalid/two?a=1&b=2');
        assert.equal(await page.locator('#editor code').textContent(), '[Code](https://example.invalid/code)');
        assert.equal(await page.locator('#editor a').first().getAttribute('rel'), 'noopener');
        assert.equal(await page.locator('#notebook-security-notice').isVisible(), false);
        await reset();
        await page.locator('#editor > :first-child').focus();
        await page.evaluate(() => {
            const clipboardData = new DataTransfer();
            clipboardData.setData('text/html', '<b>Safe text</b><img src="https://example.invalid/image" onerror="window.auditExecuted=true">');
            editor.firstElementChild.dispatchEvent(new ClipboardEvent('paste', { bubbles: true, cancelable: true, clipboardData }));
        });
        assert.equal(await page.locator('#notebook-security-notice').isVisible(), true);
        assert.equal(await page.locator('#editor b').textContent(), 'Safe text');
        assert.equal(await page.locator('#editor [onerror]').count(), 0);
        assert.equal(await page.evaluate(() => window.auditExecuted), false);
        await page.goto(pathToFileURL(path.resolve(__dirname, '../chat_ui.html')).href);
        assert.equal(await page.locator('.context-info-popover').count(), 2);
        for (const popover of await page.locator('.context-info-popover').all()) {
            assert.match(await popover.textContent(), /Quick Actions always send.*even when this switch is off/);
            assert.match(await popover.textContent(), /questions you type yourself/);
        }
        console.log('PASS Markdown clipboard/input XSS, bridge isolation, literal labels, formatting and ordinary links');
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
