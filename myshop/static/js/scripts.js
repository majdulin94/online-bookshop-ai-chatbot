// Rebuild allowed formatting; never insert untrusted HTML into the live DOM.
function safeUrl(value, external = false) {
    try {
        const url = new URL(value, window.location.origin);
        if (!["http:", "https:"].includes(url.protocol)) return "";
        if (!external && url.origin !== window.location.origin) return "";
        return url.href;
    } catch { return ""; }
}

function renderSafeMessage(target, value) {
    const parsed = new DOMParser().parseFromString(String(value).replace(/\n/g, "<br>"), "text/html");
    function append(parent, node) {
        if (node.nodeType === 3) { parent.appendChild(document.createTextNode(node.textContent)); return; }
        if (node.nodeType !== 1 || ["SCRIPT", "STYLE", "IFRAME", "OBJECT", "SVG", "MATH"].includes(node.tagName)) return;
        const allowed = ["BR", "B", "STRONG", "SPAN", "A"].includes(node.tagName);
        const clean = allowed ? document.createElement(node.tagName.toLowerCase()) : document.createDocumentFragment();
        if (node.tagName === "A") {
            const href = safeUrl(node.getAttribute("href"));
            if (href) clean.setAttribute("href", href);
        }
        for (const child of node.childNodes) append(clean, child);
        parent.appendChild(clean);
    }
    target.replaceChildren();
    for (const child of parsed.body.childNodes) append(target, child);
}

/***************************************
*         Chatbot Section              *
***************************************/

// Clear chatbot session if user logs in, logs out, or registers
const path = window.location.pathname;
if (
    [
        "/accounts/login/",
        "/accounts/logout/",
        "/accounts/register/",
    ].includes(path)
) {
    localStorage.removeItem("chatbotSessionId");
}

let chatbotSessionId = localStorage.getItem("chatbotSessionId") || null;

// Show or hide chatbot window and load chat history on page load
window.addEventListener("DOMContentLoaded", () => {
    const chatbotOpen = localStorage.getItem("chatbotOpen");
    const chatbotWindow = document.getElementById("chatbot-window");
    const openBtn = document.getElementById("open-chatbot-btn");
    if (chatbotOpen === "true") {
        chatbotWindow.style.display = "block";
        openBtn.style.display = "none";
        if (chatbotSessionId) {
            loadChatHistory();
            showAllSessionsBtn(true);
        } else {
            loadAllChatSessions();
            showAllSessionsBtn(false);
        }
    } else {
        chatbotWindow.style.display = "none";
        openBtn.style.display = "block";
    }
    if (document.querySelector('.cart-qty-group')) {
        cartPageInit();
    }
});

// Show/hide "Show all conversations" button
function showAllSessionsBtn(show = false) {
    let btn = document.getElementById("show-all-sessions-btn");
    if (!btn) {
        btn = document.createElement("button");
        btn.id = "show-all-sessions-btn";
        btn.className = "btn btn-link btn-sm mb-2";
        btn.innerHTML = '<i class="fa fa-list"></i> Show all conversations';
        btn.style.display = "none";
        btn.onclick = function () {
            localStorage.removeItem("chatbotSessionId");
            chatbotSessionId = null;
            loadAllChatSessions(false);
            showAllSessionsBtn(false);
        };
        document.getElementById("chatbot-messages").before(btn);
    }
    btn.style.display = show ? "block" : "none";
}

async function loadChatHistory() {
    let url = "/chatbot/history/";
    if (chatbotSessionId) {
        url += "?session_id=" + chatbotSessionId;
    }
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Request failed");
        const messagesDiv = document.getElementById("chatbot-messages");
        messagesDiv.innerHTML = "";

        // Always show welcome message if present, even if there are no messages yet
        if (data.welcome_message) {
            const welcome = document.createElement("div");
            welcome.className = "chatbot-welcome-message p-2 mb-2 rounded bg-light border";
            renderSafeMessage(welcome, data.welcome_message);
            messagesDiv.appendChild(welcome);
        }

        // Show messages (if any)
        if (data.messages && data.messages.length > 0) {
            data.messages.forEach((msg) => {
                if (msg.role === "assistant") {
                    addChatMessage(
                        "bot",
                        msg.content,
                        msg.sentiment,
                        messagesDiv
                    );
                    if (msg.suggested_books?.length) {
                        renderBookCards(msg.suggested_books, messagesDiv);
                    }
                } else {
                    addChatMessage("user", msg.content, null, messagesDiv);
                }
            });
        }

        document.getElementById("chatbot-quick-replies").innerHTML = "";
        if (data.session_id) {
            chatbotSessionId = data.session_id;
            localStorage.setItem("chatbotSessionId", chatbotSessionId);
        }
        showAllSessionsBtn(true);

        setTimeout(() => {
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }, 150);

    } catch (err) {
        console.error("Failed to load chat history", err);
    }
}

// Load all chat sessions for logged in users (collapsible view)
async function loadAllChatSessions(openLast = true) {
    let url = "/chatbot/history/";
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        const messagesDiv = document.getElementById("chatbot-messages");
        messagesDiv.innerHTML = "";

        if (data.all_sessions && data.all_sessions.length > 0) {
            data.all_sessions.forEach((session, idx) => {
                // Collapsible session header
                const sessionBlock = document.createElement("div");
                sessionBlock.className = "chat-session-block mb-2";
                const header = document.createElement("div");
                header.className = "session-header bg-secondary text-white rounded px-2 py-1 mb-1 d-flex align-items-center";
                header.style.cursor = "pointer";
                header.textContent = "Conversation #" + (data.all_sessions.length - idx) + " — " + session.created_at;
                const chevron = document.createElement("i");
                chevron.className = "fa fa-chevron-down ms-auto";
                header.appendChild(chevron);
                sessionBlock.appendChild(header);

                // Session messages (collapsible body)
                const body = document.createElement("div");
                body.className = "session-body";
                body.style.display = "none";
                session.messages.forEach(msg => {
                    if (msg.role === "assistant" && msg.suggested_books && msg.suggested_books.length) {
                        addChatMessage("bot", msg.content, msg.sentiment, body);
                        renderBookCards(msg.suggested_books, body);
                    } else {
                        addChatMessage(msg.role === "user" ? "user" : "bot", msg.content, msg.sentiment, body);
                    }
                });
                sessionBlock.appendChild(body);

                // Toggle session collapse on click
                header.addEventListener("click", () => {
                    body.style.display = (body.style.display === "none") ? "block" : "none";
                    const icon = header.querySelector("i.fa-chevron-down, i.fa-chevron-up");
                    if (icon) icon.className = body.style.display === "none" ?
                        "fa fa-chevron-down" : "fa fa-chevron-up";
                });

                // Load selected session on double click
                header.addEventListener("dblclick", () => {
                    localStorage.setItem("chatbotSessionId", session.session_id);
                    chatbotSessionId = session.session_id;
                    loadChatHistory();
                    showAllSessionsBtn(true);
                });

                messagesDiv.appendChild(sessionBlock);
            });

            // Show welcome message if exists
            if (data.welcome_message) {
                const welcome = document.createElement("div");
                welcome.className = "chatbot-welcome-message p-2 mb-2 rounded bg-light border";
                renderSafeMessage(welcome, data.welcome_message);
                messagesDiv.appendChild(welcome);
            }
        } else if (data.messages) {
            // For guests (single session only)
            if (data.welcome_message) {
                const welcome = document.createElement("div");
                welcome.className = "chatbot-welcome-message p-2 mb-2 rounded bg-light border";
                renderSafeMessage(welcome, data.welcome_message);
                messagesDiv.appendChild(welcome);
            }
            data.messages.forEach(msg => {
                addChatMessage(msg.role === "user" ? "user" : "bot", msg.content, msg.sentiment, messagesDiv);
                if (msg.suggested_books && msg.suggested_books.length) {
                    renderBookCards(msg.suggested_books, messagesDiv);
                }
            });
        }

        // Scroll to latest message in the last session
        setTimeout(() => {
            const bodies = messagesDiv.querySelectorAll('.session-body');
            if (bodies.length && openLast) {
                bodies.forEach((body, idx) => {
                    if (idx !== bodies.length - 1) body.style.display = "none";
                });
                bodies[bodies.length - 1].style.display = "block";
            } else if (bodies.length) {
                bodies.forEach(body => body.style.display = "none");
            }
            const allMsgs = messagesDiv.querySelectorAll('.chatbot-msg');
            if (allMsgs.length) {
                allMsgs[allMsgs.length - 1].scrollIntoView({behavior: "auto", block: "end"});
            } else {
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        }, 280);

    } catch (err) {
        console.error("Could not load chat history", err);
    }
}

// Add chat message bubble (user or bot)
function addChatMessage(sender, text, sentiment, container) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `chatbot-msg ${sender}`;
    const bubble = document.createElement("div");
    bubble.className = "chatbot-bubble";
    if (sender === "user") {
        bubble.textContent = text;
        bubble.style.whiteSpace = "pre-wrap";
    } else {
        renderSafeMessage(bubble, text);
    }
    if (sentiment) bubble.appendChild(document.createTextNode(" " + getSentimentEmoji(sentiment)));
    msgDiv.appendChild(bubble);
    (container || document.getElementById("chatbot-messages")).appendChild(msgDiv);
}


// Open chatbot window
document.getElementById("open-chatbot-btn").onclick = function () {
    document.getElementById("chatbot-window").style.display = "block";
    this.style.display = "none";
    localStorage.setItem("chatbotOpen", "true");
    chatbotSessionId = localStorage.getItem("chatbotSessionId") || null;
    if (chatbotSessionId) {
        loadChatHistory();
        showAllSessionsBtn(true);
    } else {
        loadAllChatSessions();
        showAllSessionsBtn(false);
    }
};
// Close chatbot window
document.getElementById("close-chatbot-btn").onclick = function () {
    document.getElementById("chatbot-window").style.display = "none";
    document.getElementById("open-chatbot-btn").style.display = "block";
    localStorage.setItem("chatbotOpen", "false");
};

document.addEventListener("DOMContentLoaded", function () {
    var chatbotBtn = document.getElementById('navbarChatbotBtn');
    if (chatbotBtn) {
        chatbotBtn.addEventListener('click', function (e) {
            e.preventDefault();
            var chatbotWindow = document.getElementById('chatbot-window');
            var openBtn = document.getElementById('open-chatbot-btn');
            let chatbotSessionId = localStorage.getItem("chatbotSessionId") || null;

            if (chatbotWindow.style.display === 'block') {
                // Close chatbot window
                chatbotWindow.style.display = 'none';
                openBtn.style.display = 'block';
                localStorage.setItem("chatbotOpen", "false");
            } else {
                // Open chatbot window
                chatbotWindow.style.display = 'block';
                openBtn.style.display = 'none';
                localStorage.setItem("chatbotOpen", "true");
                chatbotSessionId = localStorage.getItem("chatbotSessionId") || null;

                if (chatbotSessionId) {
                    loadChatHistory();
                    showAllSessionsBtn(true);
                } else {
                    loadAllChatSessions();
                    showAllSessionsBtn(false);
                }
            }
        });
    }
});


// Get sentiment emoji
function getSentimentEmoji(sentiment) {
    if (!sentiment) return "";
    sentiment = sentiment.toLowerCase();
    if (sentiment === "positive") return "🙂";
    if (sentiment === "negative") return "🙁";
    if (sentiment === "neutral") return "😐";
    return "";
}

// Render quick reply buttons below the chat
function renderQuickReplies(quickReplies) {
    const container = document.getElementById("chatbot-quick-replies");
    container.innerHTML = "";
    if (!quickReplies?.length) return;

    // Create close button
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.title = "Close suggestions";
    closeBtn.innerHTML = "&times;";
    closeBtn.style.cssText =
        "float:right;margin-left:10px;background:transparent;border:none;font-size:1.4em;color:#999;cursor:pointer;";
    closeBtn.onclick = () => { container.innerHTML = ""; };
    container.appendChild(closeBtn);

    // Add quick reply buttons
    quickReplies.forEach((label) => {
        const btn = document.createElement("button");
        btn.className = "quick-reply-btn";
        btn.textContent = label;
        btn.onclick = () => {
            document.getElementById("chatbot-input").value = label;
            document
                .getElementById("chatbot-form")
                .dispatchEvent(new Event("submit"));
            container.innerHTML = "";
        };
        container.appendChild(btn);
    });
}

// Render mini book cards in the chatbot
function renderBookCards(books, container) {
    if (!books?.length) return;
    books.forEach(book => {
        const tmpl = document.getElementById('chatbot-book-card-template');
        if (!tmpl) return;
        const card = tmpl.content.cloneNode(true);
        card.querySelector('.mini-book-cover').src = safeUrl(book.cover_url, true) || "/static/images/placeholder.jpg";
        card.querySelector('.mini-book-cover').alt = (book.title || "Book") + " cover";
        card.querySelector('.mini-book-title').textContent = book.title || "";
        card.querySelector('.mini-book-author').textContent =
            "Author(s): " + (book.authors || "-");
        card.querySelector('.mini-book-category').textContent =
            "Category: " + (book.category?.name || book.category || "-");
        card.querySelector('.mini-book-topic').textContent =
            "Topic: " + (book.topic_tag || "-");
        card.querySelector('.mini-book-price').textContent = book.price ? `${book.price} €` : "";
        const rating = Number(book.average_rating);
        card.querySelector('.mini-book-rating').textContent = Number.isFinite(rating) && rating >= 1 && rating <= 5
            ? "\u2605".repeat(Math.round(rating)) + " (" + rating + " / 5, " + (Number(book.num_reviews) || 0) + " reviews)"
            : "No ratings";
        const bookLink = safeUrl(book.link);
        card.querySelector('.mini-action-view').href = bookLink || "#";
        card.querySelector('.mini-action-cart').onclick = function (e) {
            e.preventDefault();
            addToCart(book.slug, book.title);
        };
        card.querySelector('.mini-action-wishlist').onclick = function (e) {
            e.preventDefault();
            addToWishlist(book.slug, book.title);
        };
        const msgDiv = document.createElement("div");
        msgDiv.className = "chatbot-msg bot";
        msgDiv.appendChild(card);
        (container || document.getElementById("chatbot-messages")).appendChild(msgDiv);
    });
}

// Helper: show a toast message in the chatbot window
function showChatbotToast(message, color = "danger") {
    let old = document.getElementById("chatbot-toast");
    if (old) old.remove();
    let toast = document.createElement("div");
    toast.id = "chatbot-toast";
    toast.style.position = "fixed";
    toast.style.right = "56px";
    toast.style.bottom = "430px";
    toast.style.zIndex = 2000;
    toast.style.minWidth = "220px";
    toast.style.maxWidth = "330px";
    toast.style.padding = "13px 24px";
    toast.style.borderRadius = "18px";
    toast.style.background = color === "success"
        ? "linear-gradient(90deg,#53E0A5,#BFA4F5)"
        : "linear-gradient(90deg,#FFB7D5 60%,#FFD6EC 100%)";
    toast.style.color = "#232";
    toast.style.fontSize = "1.08em";
    toast.style.fontWeight = "600";
    toast.style.boxShadow = "0 8px 32px #e3e3e399";
    toast.style.textAlign = "center";
    toast.style.letterSpacing = "0.02em";
    toast.style.pointerEvents = "none";
    toast.textContent = message.replace(/<\/?b>/g, "");
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        setTimeout(() => toast.remove(), 600);
    }, 1700);
}

document.getElementById("chatbot-form").onsubmit = async function (e) {
    e.preventDefault();
    const input = document.getElementById("chatbot-input");
    const msg = input.value.trim();
    if (!msg) return;

    // 1. Add the user's message as a chat bubble
    addChatMessage("user", msg);

    // 2. Show a temporary waiting bubble for the bot ("...")
    addChatMessage("bot", "...");

    input.value = "";
    document.getElementById("chatbot-quick-replies").innerHTML = "";

    // 3. Collect filter values along with the message
    const minPrice = document.getElementById('filter-min-price').value;
    const maxPrice = document.getElementById('filter-max-price').value;
    const minRating = document.getElementById('filter-min-rating').value;
    const stockStatus = document.getElementById('filter-stock-status').value;

    let body = { message: msg };
    if (minPrice || maxPrice)
        body.price_filter = { ...(minPrice && { min: minPrice }), ...(maxPrice && { max: maxPrice }) };
    if (minRating)
        body.rating_filter = { min: minRating };
    if (stockStatus)
        body.stock_status = stockStatus;

    try {
        const resp = await fetch("/chatbot/api/", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
            body: JSON.stringify(body),
        });
        const data = await resp.json();

        // 4. Remove the temporary "..." waiting message
        const msgs = document.querySelectorAll(".chatbot-msg.bot .chatbot-bubble");
        if (msgs.length > 0 && msgs[msgs.length - 1].textContent === "...") {
            msgs[msgs.length - 1].parentNode.parentNode.removeChild(
                msgs[msgs.length - 1].parentNode
            );
        }

        // 5. Add the bot's reply as a bubble, with sentiment if present
        if (data.reply)
            addChatMessage("bot", data.reply, data.sentiment);

        // 6. Display book results if any exist
        if (data.books?.length) {
            renderBookCards(data.books);
        }

        // 7. Show quick replies if available
        if ((!data.books || !data.books.length) && data.quick_replies?.length) {
            renderQuickReplies(data.quick_replies);
        }


    } catch (err) {
        addChatMessage("bot", "Sorry, I couldn't connect. Try again!");
    }
};


// ========== base Functions ==========
// Lottie animation
document.addEventListener("DOMContentLoaded", function () {
    if (window.lottie) {
        // Chatbot button
        if (document.getElementById("lottie-chatbot-icon")) {
            lottie.loadAnimation({
                container: document.getElementById("lottie-chatbot-icon"),
                renderer: "svg",
                loop: true,
                autoplay: true,
                path: "/static/animations/chatbot-animated.json",
            });
        }
        // Chatbot title
        var chatbotTitleLottie = document.getElementById("lottie-chatbot-title");
        if (chatbotTitleLottie) {
            lottie.loadAnimation({
                container: chatbotTitleLottie,
                renderer: "svg",
                loop: true,
                autoplay: true,
                path: "/static/animations/chatbot-titel02.json",
            });
        }
        // Book search
        var bookSearchLottie = document.getElementById("lottie-book-search");
        if (bookSearchLottie) {
            lottie.loadAnimation({
                container: bookSearchLottie,
                renderer: "svg",
                loop: true,
                autoplay: true,
                path: "/static/animations/book-search.json",
            });
        }
    }
});

// Dropdowns bootstrap (navbar)
document.addEventListener("DOMContentLoaded", function () {
    document
        .querySelectorAll(".dropdown-toggle")
        .forEach(function (dropdownToggleEl) {
            new bootstrap.Dropdown(dropdownToggleEl);
        });
});


/****************************************
*         Cart Section (cart.html)      *
****************************************/
function cartPageInit() {
    const MIN_QTY = 1;
    const MAX_QTY = 10;

    function updateCartAjax(input, quantity) {
        const form = input.closest('.cart-update-form');
        const action = form.action;
        const csrf = form.querySelector('input[name="csrfmiddlewaretoken"]').value;

        fetch(action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrf,
                'Accept': 'application/json',
            },
            body: new URLSearchParams({ quantity: quantity }),
        })
            .then(resp => resp.json())
            .then(data => {
                if (data.status === 'success') {
                    // Update the book total price
                    const itemTotal = form.parentElement.parentElement.querySelector('.item-total');
                    if (itemTotal) itemTotal.innerHTML = "€" + data.item_total.toFixed(2);

                    // Update cart summary
                    document.querySelector('span[data-summary="subtotal"]').innerHTML = "€" + data.subtotal.toFixed(2);
                    document.querySelector('span[data-summary="shipping"]').innerHTML = "€" + data.shipping_cost.toFixed(2);
                    document.querySelector('span[data-summary="tax"]').innerHTML = "€" + data.tax.toFixed(2);
                    document.querySelector('span[data-summary="total"]').innerHTML = "€" + data.total.toFixed(2);

                    // Show message if the cart is now empty
                    if (data.subtotal === 0) {
                        const table = document.querySelector('.table-responsive');
                        if (table) table.style.display = "none";
                        const summaryRow = document.querySelector('.row.justify-content-end');
                        if (summaryRow) summaryRow.style.display = "none";
                        const emptyAlert = document.getElementById('empty-cart-alert');
                        if (emptyAlert) emptyAlert.style.display = "block";
                    }
                } else {
                    alert(data.message || "Error updating cart");
                }
            });
    }

    // Plus button
    document.querySelectorAll('.btn-qty-increase').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const input = btn.closest('.cart-qty-group').querySelector('.cart-qty-input');
            let quantity = parseInt(input.value) || MIN_QTY;
            if (quantity < MAX_QTY) {
                quantity += 1;
                input.value = quantity;
                updateCartAjax(input, quantity);
            } else {
                input.value = MAX_QTY;
            }
        });
    });

    // Minus button
    document.querySelectorAll('.btn-qty-decrease').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const input = btn.closest('.cart-qty-group').querySelector('.cart-qty-input');
            let quantity = parseInt(input.value) || MIN_QTY;
            if (quantity > MIN_QTY) {
                quantity -= 1;
                input.value = quantity;
                updateCartAjax(input, quantity);
            } else {
                input.value = MIN_QTY;
            }
        });
    });

    // On manual input (change or Enter)
    document.querySelectorAll('.cart-qty-input').forEach(function (input) {
        input.addEventListener('change', function () {
            let quantity = parseInt(input.value);
            if (isNaN(quantity) || quantity < MIN_QTY) quantity = MIN_QTY;
            if (quantity > MAX_QTY) quantity = MAX_QTY;
            input.value = quantity;
            updateCartAjax(input, quantity);
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                input.blur(); // Trigger change event
            }
        });
    });
}
/***************************************
*      Cart & Wishlist Section (Chatbot)         *
***************************************/

// Add to cart
function addToCart(bookSlug, bookTitle) {
    fetch(`/cart/add/${bookSlug}/`, {
        method: 'POST',
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({ quantity: 1 }),
        credentials: 'include'
    })
        .then(resp => resp.json())
        .then(data => {
            if (data.status === "success") {
                showChatbotToast(`✔️ <b>${bookTitle}</b> has been added to your cart`, "success");
                if ('cart_count' in data) updateCartBadge(data.cart_count);
            } else {
                showChatbotToast(`⚠️ ${data.message || "An error occurred while adding <b>" + bookTitle + "</b> to the cart"}`, "danger");
            }
        })
        .catch(err => {
            showChatbotToast(`⚠️ Could not connect to the server!`, "danger");
        });
}

function updateCartBadge(count) {
    let badge = document.querySelector('.cart-badge');
    if (count > 0) {
        if (!badge) {
            let cartIcon = document.querySelector('a[title="Cart"]');
            badge = document.createElement('span');
            badge.className = "cart-badge position-absolute top-0 start-100 translate-middle badge rounded-pill bg-success";
            badge.style.fontSize = "0.65em";
            cartIcon.appendChild(badge);
        }
        badge.textContent = count;
    } else if (badge) {
        badge.remove();
    }
}

// Add to wishlist
function addToWishlist(bookSlug, bookTitle) {
    fetch(`/cart/wishlist/add/${bookSlug}/`, {
        method: 'POST',
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify({}),
        credentials: 'include'
    })
        .then(resp => resp.json())
        .then(data => {
            if (data.status === "success") {
                showChatbotToast(`❤️ <b>${bookTitle}</b> added to wishlist`, "success");
                if ('wishlist_count' in data) updateWishlistBadge(data.wishlist_count);
            } else {
                showChatbotToast(`⚠️ ${data.message || "Error adding to wishlist"}`, "danger");
            }
        })
        .catch(err => {
            showChatbotToast(`⚠️ Could not connect to the server!`, "danger");
        });
}

function updateWishlistBadge(count) {
    let badge = document.querySelector('.wishlist-badge');
    if (count > 0) {
        if (!badge) {
            let wishlistIcon = document.querySelector('a[title="Wishlist"]');
            badge = document.createElement('span');
            badge.className = "wishlist-badge position-absolute top-0 start-100 translate-middle badge rounded-pill bg-pink";
            badge.style.fontSize = "0.65em";
            wishlistIcon.appendChild(badge);
        }
        badge.textContent = count;
    } else if (badge) {
        badge.remove();
    }
}

/***************************************
*          Utilities Section           *
***************************************/
function getCSRFToken() {
    return document.cookie.split('; ')
        .find(row => row.startsWith('csrftoken='))
        ?.split('=')[1];
}
