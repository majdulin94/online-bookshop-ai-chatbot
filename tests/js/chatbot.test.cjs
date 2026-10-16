const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

function page() {
    const dom = new JSDOM(`<!doctype html><body>
        <div id="chatbot-window"></div><button id="open-chatbot-btn"></button>
        <button id="close-chatbot-btn"></button><div id="chatbot-messages"></div>
        <div id="chatbot-quick-replies"></div><form id="chatbot-form"></form>
        <input id="chatbot-input"><input id="filter-min-price"><input id="filter-max-price">
        <input id="filter-min-rating"><input id="filter-stock-status">
        </body>`, {url: 'http://localhost/', runScripts: 'outside-only'});
    dom.window.scrollTo = () => {};
    dom.window.lottie = {loadAnimation() {}};
    dom.window.bootstrap = {Dropdown: function() {}};
    dom.window.fetch = async () => ({ok: true, json: async () => ({messages: []})});
    dom.window.eval(fs.readFileSync('myshop/static/js/scripts.js', 'utf8'));
    return dom;
}

test('user messages remain literal text, including historical attack payloads', () => {
    const dom = page(); const w = dom.window;
    const payload = '<img src=x onerror="window.pwned=true"><script>alert(1)</script>';
    w.addChatMessage('user', payload);
    assert.equal(w.document.querySelector('.chatbot-bubble').textContent, payload);
    assert.equal(w.document.querySelectorAll('.chatbot-bubble img, .chatbot-bubble script').length, 0);
    w.close();
});

test('bot formatting preserves safe order links while removing active content', () => {
    const dom = page(); const w = dom.window;
    w.addChatMessage('bot', '<b>Hello</b><br><a href="/orders/order-history/" onclick="alert(1)">Orders</a><img src=x onerror=alert(1)><a href="javascript:alert(1)">bad</a><svg onload=alert(1)></svg>');
    const bubble = w.document.querySelector('.chatbot-bubble');
    assert.equal(bubble.querySelectorAll('img,svg,script,[onclick],[onerror]').length, 0);
    assert.equal(bubble.querySelector('a').href, 'http://localhost/orders/order-history/');
    assert.equal(bubble.querySelectorAll('a')[1].hasAttribute('href'), false);
    assert.ok(bubble.querySelector('b')); assert.ok(bubble.querySelector('br'));
    w.close();
});

test('toast content and book URLs cannot execute injected markup', () => {
    const dom = page(); const w = dom.window;
    w.showChatbotToast('<img src=x onerror=alert(1)>');
    assert.equal(w.document.querySelector('#chatbot-toast img'), null);
    assert.equal(w.safeUrl('javascript:alert(1)'), '');
    assert.equal(w.safeUrl('https://untrusted.example/orders'), '');
    assert.equal(w.safeUrl('data:image/svg+xml,bad', true), '');
    w.close();
});

test('chat submission includes CSRF header and posts JSON', async () => {
    const dom = page(); const w = dom.window;
    w.document.cookie = 'csrftoken=test-token';
    let sent;
    w.fetch = async (url, options) => {sent = {url, options}; return {ok: true, json: async () => ({reply: 'Hello', sentiment: 'Neutral'})};};
    w.document.querySelector('#chatbot-input').value = 'Novels';
    await w.document.querySelector('#chatbot-form').onsubmit({preventDefault() {}});
    assert.equal(sent.url, '/chatbot/api/');
    assert.equal(sent.options.headers['X-CSRFToken'], 'test-token');
    assert.equal(JSON.parse(sent.options.body).message, 'Novels');
    w.close();
});

test('conversation list expands without an undefined openLast variable', async () => {
    const dom = page(); const w = dom.window;
    w.HTMLElement.prototype.scrollIntoView = () => {};
    w.fetch = async () => ({ok: true, json: async () => ({all_sessions: [{session_id: 'demo', created_at: '2026-10-15', messages: []}]})});
    await w.loadAllChatSessions(true);
    await new Promise(resolve => setTimeout(resolve, 320));
    assert.equal(w.document.querySelector('.session-body').style.display, 'block');
    w.close();
});

const conciseWelcome = 'Good afternoon! 📚 Looking for book recommendations? Hi! 👋 What would you like to read today?\n\n🤖 I’m an AI-assisted assistant. Ask me for recommendations by mood, price, or availability.\nFor example, try asking:\n• “Show me some sci-fi novels”\n• “Recommend books to learn Python”\n• “Give me a romantic story”\n\nWhat are you in the mood for today? 😊';

test('new guest renders exactly one concise welcome through both history loaders', async () => {
    const dom = page(); const w = dom.window;
    w.fetch = async () => ({ok: true, json: async () => ({welcome_message: conciseWelcome, messages: [], session_id: 'demo'})});
    for (const load of [w.loadAllChatSessions, w.loadChatHistory, w.loadAllChatSessions]) {
        await load();
        const messages = w.document.querySelector('#chatbot-messages');
        assert.equal(messages.querySelectorAll('.chatbot-welcome-message').length, 1);
        assert.equal((messages.textContent.match(/What are you in the mood for today/g) || []).length, 1);
        assert.equal((messages.textContent.match(/•/g) || []).length, 3);
        assert.doesNotMatch(messages.textContent, /show my orders|how can i pay|demo-owner/);
    }
    w.close();
});

test('new account renders one welcome outside its empty conversation', async () => {
    const dom = page(); const w = dom.window;
    w.fetch = async () => ({ok: true, json: async () => ({welcome_message: conciseWelcome, all_sessions: [{session_id: 'demo', created_at: '2026-10-16', messages: []}]})});
    await w.loadAllChatSessions(false);
    assert.equal(w.document.querySelectorAll('.chatbot-welcome-message').length, 1);
    assert.equal(w.document.querySelectorAll('.session-body .chatbot-msg').length, 0);
    w.close();
});

test('sentiment emojis retain the original three-way mapping in rendered replies', () => {
    const dom = page(); const w = dom.window;
    for (const [sentiment, emoji] of [['Positive', '🙂'], ['Negative', '🙁'], ['Neutral', '😐']]) {
        w.addChatMessage('bot', 'Here are some books:', sentiment);
        assert.equal(w.getSentimentEmoji(sentiment), emoji);
        assert.equal([...w.document.querySelectorAll('.chatbot-bubble')].at(-1).textContent, 'Here are some books: ' + emoji);
    }
    w.close();
});

test('welcome rendering retains the XSS-safe formatter', async () => {
    const dom = page(); const w = dom.window;
    w.fetch = async () => ({ok: true, json: async () => ({welcome_message: conciseWelcome + '<img src=x onerror=alert(1)><script>alert(1)</script>', messages: []})});
    await w.loadAllChatSessions();
    assert.equal(w.document.querySelectorAll('.chatbot-welcome-message img, .chatbot-welcome-message script, .chatbot-welcome-message [onerror]').length, 0);
    w.close();
});
