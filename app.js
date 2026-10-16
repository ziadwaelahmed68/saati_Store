const $ = s => document.querySelector(s);

let P = [];
let nextProductCursor = null;
let mem = { cart: [], user: null };
let relines = () => {};

const API = (window.SAATI_API ? window.SAATI_API : '').replace(/\/$/, '');
const IMAGE_BASE = (window.SAATI_IMAGE_BASE ? window.SAATI_IMAGE_BASE : 'https://d28bzg8rlab4ye.cloudfront.net').replace(/\/$/, '');

const store = {
  get(key, fallback) {
    try {
      const val = JSON.parse(localStorage.getItem(key));
      return val !== null && val !== undefined ? val : fallback;
    } catch {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error('Storage error:', error);
    }
  }
};

const cart = () => store.get('cart', mem.cart);
const user = () => store.get('user', mem.user);
const usd = amount => '$' + Number(amount ? amount : 0).toFixed(2);
const esc = str =>
  String(str !== null && str !== undefined ? str : '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

function pick(a, b, fallback = '') {
  if (a !== undefined && a !== null && a !== '') return a;
  if (b !== undefined && b !== null && b !== '') return b;
  return fallback;
}

function formatOrderItem(i) {
  const itemName = esc(pick(i.name, i.productId, 'Watch'));
  const itemQty = pick(i.quantity, i.q, 1);
  return itemName + ' x ' + itemQty;
}

function clearSession(msg) {
  mem.user = null;
  store.set('user', null);
  nav();
  if (msg) toast(msg);
}

async function apiRequest(path, { method = 'GET', body, headers = {} } = {}) {
  const currentUser = user();
  const reqHeaders = { ...headers };
  if (currentUser && currentUser.token) {
    reqHeaders.Authorization = 'Bearer ' + currentUser.token;
  }
  if (body && !(body instanceof FormData)) {
    reqHeaders['Content-Type'] = 'application/json';
  }

  const response = await fetch(API + path, {
    method,
    headers: reqHeaders,
    body: body ? (body instanceof FormData ? body : JSON.stringify(body)) : undefined
  });

  const data = await response.json().catch(() => ({}));

  if (response.status === 401 && currentUser) {
    clearSession('Session expired. Please sign in again.');
    location.hash = '#/signin';
    throw new Error(pick(data.error, data.message, 'Session expired.'));
  }

  if (!response.ok) {
    throw new Error(pick(data.message, data.error, 'Request failed'));
  }

  return data;
}

const api = (path, body) => apiRequest(path, { method: 'POST', body });

function resolveProductImageUrl(product) {
  let imageUrl = String(pick(product.imageUrl, '')).trim();
  const imageKey = String(pick(product.imageKey, '')).trim();

  if (!imageUrl && imageKey) {
    const cleanKey = imageKey
      .replace(/^\/+/, '')
      .split('/')
      .map(part => encodeURIComponent(part))
      .join('/');
    imageUrl = IMAGE_BASE + '/' + cleanKey;
  }

  if (imageUrl) {
    try {
      const parsed = new URL(imageUrl, window.location.origin);
      imageUrl = parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : '';
    } catch {
      imageUrl = '';
    }
  }
  return imageUrl;
}

function normalizeProduct(product) {
  const category = String(pick(product.category, product.type, 'smart')).trim().toLowerCase();
  const id = String(pick(product.productId, product.id, '')).trim();
  return {
    id,
    productId: id,
    n: String(pick(product.name, 'SAATI Watch')).trim(),
    description: String(pick(product.description, '')).trim(),
    t: category.includes('classic') ? 'classic' : 'smart',
    p: Number(product.price),
    stockQuantity: Number(product.stockQuantity !== undefined ? product.stockQuantity : 25),
    c: '#17707a',
    imageKey: String(pick(product.imageKey, '')).trim(),
    imageUrl: resolveProductImageUrl(product),
    r: product.rating == null ? null : Number(product.rating)
  };
}

async function loadProducts(cursor = null, append = false) {
  const qs = cursor ? '?cursor=' + encodeURIComponent(cursor) : '';
  const data = await apiRequest('/api/products' + qs);
  const rawList = Array.isArray(data)
    ? data
    : Array.isArray(data.products)
      ? data.products
      : [];

  nextProductCursor = data.nextCursor ? data.nextCursor : null;
  const normalized = rawList
    .map(normalizeProduct)
    .filter(p => p.id && Number.isFinite(p.p) && p.p >= 0);

  P = append ? [...P, ...normalized] : normalized;
  return P;
}

function saveCart(items) {
  mem.cart = items;
  store.set('cart', items);
  nav();
}

function toast(message) {
  const element = $('#toast');
  if (!element) return;
  element.textContent = message;
  element.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => element.classList.remove('show'), 2400);
}

function navigateToPath(path) {
  if (path === '/admin') {
    history.pushState({}, '', '/admin');
    location.hash = '#/admin';
  } else if (path === '/') {
    if (location.pathname === '/admin') history.pushState({}, '', '/');
    location.hash = '#/';
  } else {
    location.hash = path.startsWith('#') ? path : '#' + path;
  }
}

function nav() {
  const currentUser = user();
  const isAdmin = currentUser && currentUser.role === 'admin';
  const count = cart().reduce((sum, item) => sum + Number(item.q ? item.q : 0), 0);
  const wishlist = store.get('wish', []);
  const element = $('#nav');
  if (!element) return;

  const userDisplayName = currentUser ? esc(pick(currentUser.name, currentUser.email, 'User')) : '';

  element.innerHTML = `
    <a class="logo" href="#/">SAATI</a>
    <a href="#/products">Watches</a>
    <a href="#/products" title="Wishlist">♥ ${wishlist.length}</a>
    <a href="#/checkout">Cart (<span id="cn">${count}</span>)</a>
    ${currentUser ? '<a href="#/orders">My Orders</a>' : ''}
    ${isAdmin ? '<a href="#/admin" class="badge">Admin</a>' : ''}
    ${
      currentUser
        ? `<a href="#" id="out">Sign out (${userDisplayName})</a>`
        : '<a href="#/signin">Sign in</a>'
    }
    <button class="mode" id="mode" aria-label="Toggle dark mode">◐</button>
  `;

  const signout = $('#out');
  if (signout) {
    signout.onclick = async event => {
      event.preventDefault();
      try {
        await apiRequest('/api/signout', { method: 'POST' });
      } catch {}
      clearSession('Signed out');
      navigateToPath('/');
    };
  }

  const mode = $('#mode');
  if (mode) {
    mode.onclick = () => {
      const root = document.documentElement;
      root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    };
  }
}

function watch(product) {
  if (product.imageUrl) {
    return `
      <img
        src="${esc(product.imageUrl)}"
        alt="${esc(product.n)}"
        loading="lazy"
        style="width:100%;height:100%;object-fit:contain"
        onerror="this.onerror=null;this.style.display='none';this.parentElement.insertAdjacentHTML('beforeend', window.__fallbackSvg('${esc(product.n)}'))"
      >
    `;
  }
  return window.__fallbackSvg(product.n, product.c);
}

window.__fallbackSvg = (name, color = '#17707a') => `
  <svg viewBox="0 0 200 200" role="img" aria-label="${esc(name)}">
    <rect x="73" y="0" width="54" height="200" rx="12" fill="${esc(color)}"/>
    <rect x="38" y="32" width="124" height="136" rx="32" fill="#252a30"/>
    <rect x="47" y="41" width="106" height="118" rx="25" fill="#101820"/>
    <circle cx="100" cy="100" r="43" fill="#f1f1ed"/>
    <circle cx="100" cy="100" r="39" fill="none" stroke="#888" stroke-width="2"/>
    <line x1="100" y1="100" x2="100" y2="75" stroke="#222" stroke-width="4"/>
    <line x1="100" y1="100" x2="119" y2="110" stroke="#222" stroke-width="3"/>
    <circle cx="100" cy="100" r="4" fill="#c33"/>
    <text x="100" y="135" text-anchor="middle" font-size="7" fill="#222">SAATI</text>
  </svg>
`;

function rating(product) {
  return product.r == null || !Number.isFinite(product.r) ? '' : ' · ★ ' + product.r;
}

function card(product, index = 0) {
  const wishlist = store.get('wish', []);
  const saved = wishlist.includes(product.id);
  const outOfStock = product.stockQuantity <= 0;

  return `
    <div class="card" style="animation-delay:${index * 45}ms">
      <button class="heart ${saved ? 'on' : ''}" data-wish="${esc(product.id)}" aria-label="Toggle wishlist">♥</button>
      <div class="img" data-open="${esc(product.id)}" role="button" tabindex="0">
        ${watch(product)}
      </div>
      <h3>${esc(product.n)}</h3>
      <div>
        ${product.t === 'smart' ? 'Smartwatch' : 'Classic watch'}
        ${rating(product)}
      </div>
      ${product.description ? `<p style="font-size:.88rem;opacity:.82;margin:.4em 0">${esc(product.description)}</p>` : ''}
      <p class="price">${usd(product.p)}</p>
      <button class="btn" data-add="${esc(product.id)}" ${outOfStock ? 'disabled' : ''}>
        ${outOfStock ? 'Out of stock' : 'Add to cart'}
      </button>
    </div>
  `;
}

function openModal(id) {
  const product = P.find(p => p.id === String(id).trim());
  if (!product || !$('#modal')) return;
  const descText = esc(pick(product.description, 'Precision engineered SAATI timepiece.'));

  $('#modal').innerHTML = `
    <div class="mb">
      <div class="mc" role="dialog" aria-modal="true">
        <button class="x" aria-label="Close">×</button>
        <div class="mw">${watch(product)}</div>
        <div>
          <h2>${esc(product.n)}</h2>
          <p class="price">${usd(product.p)}${rating(product)}</p>
          <p>${descText}</p>
          <p>Category: ${product.t === 'smart' ? 'Smartwatch' : 'Classic watch'}</p>
          <p>Stock Available: ${product.stockQuantity}</p>
          <button class="btn" data-add="${esc(product.id)}" ${product.stockQuantity <= 0 ? 'disabled' : ''}>
            ${product.stockQuantity <= 0 ? 'Out of stock' : 'Add to cart'}
          </button>
        </div>
      </div>
    </div>
  `;
}

function closeModal() {
  if ($('#modal')) $('#modal').innerHTML = '';
}

const pages = {
  home() {
    $('#app').innerHTML = `
      <div class="promo">Welcome to SAATI Watches</div>
      <main class="wrap hero">
        <div>
          <h1>Time, worn well.</h1>
          <p>Smart and classic watches for every moment.</p>
          <a class="btn" href="#/products">Shop watches</a>
          ${user() ? '' : '<a class="btn alt" href="#/signin">Sign in</a>'}
        </div>
        <div class="stage" id="stage"></div>
      </main>
      <section class="wrap">
        <h2>Our watches</h2>
        <div class="grid" id="bs"></div>
      </section>
    `;

    $('#bs').innerHTML = P.length
      ? P.slice(0, 4).map(card).join('')
      : '<p>No watches available right now.</p>';

    if (P.length && $('#stage')) {
      $('#stage').innerHTML = `
        <div class="w">${watch(P[0])}</div>
        <div class="tag">${esc(P[0].n)} · ${usd(P[0].p)}</div>
      `;
    }
  },

  products() {
    $('#app').innerHTML = `
      <main class="wrap">
        <h1>Watches</h1>
        <div class="bar">
          <div class="tabs">
            <button class="on" data-t="all">All</button>
            <button data-t="smart">Smart</button>
            <button data-t="classic">Classic</button>
          </div>
          <input id="sq" type="search" placeholder="Search watches">
          <select id="so">
            <option value="f">Featured</option>
            <option value="a">Price: low to high</option>
            <option value="d">Price: high to low</option>
          </select>
        </div>
        <p id="cnt"></p>
        <div class="grid" id="grid"></div>
        <div style="text-align:center;margin-top:24px" id="moreWrap"></div>
      </main>
    `;

    let type = 'all';

    const draw = () => {
      const query = $('#sq').value.toLowerCase().trim();
      const order = $('#so').value;

      let list = P.filter(product => {
        const matchType = type === 'all' ? true : product.t === type;
        const matchText = product.n.toLowerCase().includes(query) ? true : product.description.toLowerCase().includes(query);
        return matchType && matchText;
      });

      if (order === 'a') list.sort((a, b) => a.p - b.p);
      if (order === 'd') list.sort((a, b) => b.p - a.p);

      $('#cnt').textContent = list.length + ' watches';
      $('#grid').innerHTML = list.length
        ? list.map(card).join('')
        : '<p>No watches match your search.</p>';

      $('#moreWrap').innerHTML = nextProductCursor
        ? '<button class="btn alt" id="loadMoreBtn">Load more watches</button>'
        : '';

      const moreBtn = $('#loadMoreBtn');
      if (moreBtn) {
        moreBtn.onclick = async () => {
          moreBtn.disabled = true;
          moreBtn.textContent = 'Loading...';
          try {
            await loadProducts(nextProductCursor, true);
            draw();
          } catch (e) {
            toast(e.message);
          }
        };
      }
    };

    document.querySelectorAll('.tabs button').forEach(button => {
      button.onclick = () => {
        document.querySelectorAll('.tabs button').forEach(item => item.classList.remove('on'));
        button.classList.add('on');
        type = button.dataset.t;
        draw();
      };
    });

    $('#sq').oninput = draw;
    $('#so').onchange = draw;
    draw();
  },

  signin() {
    let signup = false;

    const draw = () => {
      $('#app').innerHTML = `
        <main class="wrap">
          <form class="form" id="f">
            <h1>${signup ? 'Create account' : 'Sign in'}</h1>
            ${signup ? '<label for="nm">Name</label><input id="nm" required autocomplete="name">' : ''}
            <label for="em">Email</label>
            <input id="em" type="email" required autocomplete="email">
            <label for="pw">Password</label>
            <input id="pw" type="password" required minlength="6" autocomplete="${signup ? 'new-password' : 'current-password'}">
            <p class="err" id="err"></p>
            <button class="btn" id="submitAuthBtn">${signup ? 'Create account' : 'Sign in'}</button>
            <div style="margin-top:14px">
              <a href="#" id="sw">${signup ? 'I have an account' : 'Create an account'}</a>
            </div>
          </form>
        </main>
      `;

      $('#sw').onclick = event => {
        event.preventDefault();
        signup = !signup;
        draw();
      };

      $('#f').onsubmit = async event => {
        event.preventDefault();
        $('#err').textContent = '';
        const email = $('#em').value.trim().toLowerCase();
        const password = $('#pw').value;

        try {
          const data = await api(
            signup ? '/api/signup' : '/api/signin',
            {
              ...(signup ? { name: $('#nm').value.trim() } : {}),
              email,
              password
            }
          );

          mem.user = {
            name: pick(data.name, email),
            email,
            role: pick(data.role, 'customer'),
            token: data.token
          };

          store.set('user', mem.user);
          nav();
          toast('Welcome, ' + mem.user.name + '!');

          if (mem.user.role === 'admin' || data.redirectTo === '/admin') {
            navigateToPath('/admin');
          } else {
            navigateToPath('/');
          }
        } catch (error) {
          $('#err').textContent = error.message;
        }
      };
    };

    draw();
  },

  async orders() {
    if (!user()) {
      toast('Please sign in to view your orders.');
      location.hash = '#/signin';
      return;
    }

    $('#app').innerHTML = '<main class="wrap"><p>Loading your orders...</p></main>';
    try {
      const list = await apiRequest('/api/orders');
      const rowsHtml = list
        .map(o => {
          const oid = esc(pick(o.orderId, o.id));
          const dt = esc(String(pick(o.createdAt, '')).slice(0, 10));
          const itemsArr = Array.isArray(o.items) ? o.items : [];
          const itemsStr = itemsArr.map(formatOrderItem).join(', ');
          const st = esc(pick(o.status, 'PENDING'));
          return `<tr>
            <td><b>${oid}</b></td>
            <td>${dt}</td>
            <td>${itemsStr}</td>
            <td><span class="badge">${st}</span></td>
            <td>${usd(o.total)}</td>
          </tr>`;
        })
        .join('');

      $('#app').innerHTML = `
        <main class="wrap">
          <h1>My Orders</h1>
          ${
            !list.length
              ? '<p>You have not placed any orders yet.</p><a class="btn" href="#/products">Shop watches</a>'
              : `<div class="table-wrap">
                  <table class="adm-tbl">
                    <thead><tr><th>Order ID</th><th>Date</th><th>Items</th><th>Status</th><th>Total</th></tr></thead>
                    <tbody>${rowsHtml}</tbody>
                  </table>
                </div>`
          }
        </main>
      `;
    } catch (e) {
      $('#app').innerHTML = `<main class="wrap"><h1>My Orders</h1><p class="err">${esc(e.message)}</p></main>`;
    }
  },

  checkout() {
    if (!user()) {
      toast('Please sign in to access checkout.');
      location.hash = '#/signin';
      return;
    }

    if (!cart().length) {
      $('#app').innerHTML = `
        <main class="wrap form">
          <h1>Your cart is empty</h1>
          <a class="btn" href="#/products">Browse watches</a>
        </main>
      `;
      return;
    }

    let promo = false;

    const totals = () => {
      const subtotal = cart().reduce((sum, item) => {
        const product = P.find(p => p.id === String(item.id).trim());
        return sum + (product ? product.p * item.q : 0);
      }, 0);
      const discount = promo ? subtotal * 0.1 : 0;
      const shipping = subtotal - discount >= 300 ? 0 : 9.99;
      return { subtotal, discount, shipping, total: subtotal - discount + shipping };
    };

    $('#app').innerHTML = `
      <main class="wrap">
        <div class="form">
          <h1>Checkout</h1>
          <div id="lines"></div>
          <div id="sum"></div>
          <label for="pc">Promo code</label>
          <div class="row">
            <input id="pc" placeholder="SAATI10">
            <button type="button" class="btn alt" id="ap">Apply</button>
          </div>
          <form id="pay">
            <label for="ad">Shipping address</label>
            <input id="ad" required minlength="5" autocomplete="street-address">
            <label for="mt">Payment method</label>
            <select id="mt">
              <option value="cod">Cash on delivery</option>
              <option value="card">Credit card (demo only)</option>
            </select>
            <p class="err" id="err"></p>
            <button class="btn" id="placeOrderBtn">Place order</button>
          </form>
        </div>
      </main>
    `;

    const drawLines = () => {
      const result = totals();
      $('#lines').innerHTML = cart()
        .map(item => {
          const product = P.find(p => p.id === String(item.id).trim());
          if (!product) return '';
          return `
            <div class="row">
              <span>${esc(product.n)}</span>
              <span>
                <button type="button" data-q="${esc(product.id)}:-1">−</button>
                ${item.q}
                <button type="button" data-q="${esc(product.id)}:1">+</button>
              </span>
              <span>${usd(product.p * item.q)}</span>
            </div>
          `;
        })
        .join('');

      $('#sum').innerHTML = `
        <div class="row"><span>Subtotal</span><span>${usd(result.subtotal)}</span></div>
        ${promo ? `<div class="row"><span>Discount</span><span>−${usd(result.discount)}</span></div>` : ''}
        <div class="row"><span>Shipping</span><span>${result.shipping ? usd(result.shipping) : 'Free'}</span></div>
        <div class="row"><b>Total</b><b>${usd(result.total)}</b></div>
      `;
    };

    drawLines();

    relines = () => {
      if (cart().length) drawLines();
      else pages.checkout();
    };

    $('#ap').onclick = () => {
      if ($('#pc').value.trim().toUpperCase() === 'SAATI10') {
        promo = true;
        drawLines();
        toast('Promo applied: 10% off');
      } else {
        $('#err').textContent = 'Invalid promo code.';
      }
    };

    const idempotencyKey = typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : String(Date.now());

    $('#pay').onsubmit = async event => {
      event.preventDefault();
      $('#placeOrderBtn').disabled = true;
      $('#err').textContent = '';

      try {
        const data = await apiRequest('/api/checkout', {
          method: 'POST',
          headers: { 'Idempotency-Key': idempotencyKey },
          body: {
            items: cart().map(item => ({
              productId: String(item.id),
              quantity: item.q
            })),
            address: $('#ad').value,
            method: $('#mt').value,
            promo: promo ? 'SAATI10' : '',
            idempotencyKey
          }
        });

        const orderId = pick(data.order_id, data.orderId, 'Submitted');
        saveCart([]);
        await loadProducts().catch(() => {});

        $('#app').innerHTML = `
          <main class="wrap form">
            <h1>Order submitted</h1>
            <p>Order: <b>${esc(orderId)}</b></p>
            <p>Authoritative Total Charged: <b>${usd(data.total)}</b></p>
            <a class="btn" href="#/">Back to home</a>
          </main>
        `;
      } catch (error) {
        $('#err').textContent = error.message;
        $('#placeOrderBtn').disabled = false;
      }
    };
  },

  admin() {
    const currentUser = user();
    if (!currentUser) {
      toast('Please sign in to access the dashboard.');
      navigateToPath('/signin');
      return;
    }
    if (currentUser.role !== 'admin') {
      toast('Access denied: Administrator privileges required.');
      navigateToPath('/');
      return;
    }

    let activeTab = 'overview';
    let ordersCursor = null;
    let adminOrders = [];
    let editingProduct = null;

    const renderShell = () => {
      $('#app').innerHTML = `
        <div class="admin-shell">
          <aside class="admin-side" aria-label="Admin Navigation">
            <h3 style="margin-bottom:8px">Admin Panel</h3>
            <button data-adm-tab="overview" class="${activeTab === 'overview' ? 'on' : ''}">Overview</button>
            <button data-adm-tab="orders" class="${activeTab === 'orders' ? 'on' : ''}">Orders Management</button>
            <button data-adm-tab="products" class="${activeTab === 'products' ? 'on' : ''}">Products Catalog</button>
            <button data-adm-tab="product-form" class="${activeTab === 'product-form' ? 'on' : ''}">
              ${editingProduct ? 'Edit Product' : '+ Add Product'}
            </button>
          </aside>
          <section id="admContent"><p>Loading...</p></section>
        </div>
      `;

      document.querySelectorAll('[data-adm-tab]').forEach(btn => {
        btn.onclick = () => {
          activeTab = btn.dataset.admTab;
          if (activeTab !== 'product-form') editingProduct = null;
          renderShell();
        };
      });

      if (activeTab === 'overview') loadOverview();
      else if (activeTab === 'orders') loadAdminOrders();
      else if (activeTab === 'products') loadAdminProducts();
      else if (activeTab === 'product-form') renderProductForm();
    };

    async function loadOverview() {
      const box = $('#admContent');
      try {
        const stats = await apiRequest('/api/admin/stats');
        const sb = stats.statusBreakdown ? stats.statusBreakdown : {};
        box.innerHTML = `
          <h1>Dashboard Overview</h1>
          <div class="stat-grid">
            <div class="stat-card"><div>Total Products</div><div class="val">${stats.totalProducts}</div></div>
            <div class="stat-card"><div>Total Orders</div><div class="val">${stats.totalOrders}</div></div>
            <div class="stat-card"><div>Total Revenue</div><div class="val">${usd(stats.totalRevenue)}</div></div>
          </div>
          <h2>Order Status Summary</h2>
          <div class="stat-grid">
            ${Object.entries(sb)
              .map(
                ([st, count]) => `
                <div class="stat-card">
                  <div><span class="badge">${esc(st)}</span></div>
                  <div class="val" style="margin-top:8px">${count}</div>
                </div>`
              )
              .join('')}
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<p class="err">${esc(e.message)}</p>`;
      }
    }

    async function loadAdminOrders(cursor = null, append = false) {
      const box = $('#admContent');
      const statusEl = $('#admOrdStatus');
      const searchEl = $('#admOrdSearch');
      const dateEl = $('#admOrdDate');
      const statusVal = statusEl ? statusEl.value : '';
      const qVal = searchEl ? searchEl.value : '';
      const dateVal = dateEl ? dateEl.value : '';

      try {
        const params = new URLSearchParams();
        if (statusVal) params.set('status', statusVal);
        if (qVal) params.set('q', qVal);
        if (dateVal) params.set('dateFrom', dateVal);
        if (cursor) params.set('cursor', cursor);

        const data = await apiRequest('/api/admin/orders?' + params.toString());
        ordersCursor = data.nextCursor ? data.nextCursor : null;
        const incomingOrders = Array.isArray(data.orders) ? data.orders : [];
        adminOrders = append ? [...adminOrders, ...incomingOrders] : incomingOrders;

        const orderRows = adminOrders
          .map(o => {
            const custDisplay = esc(pick(o.customerName, o.customerEmail));
            const dtStr = esc(String(pick(o.createdAt, '')).slice(0, 16).replace('T', ' '));
            return `<tr>
              <td><b>${esc(o.orderId)}</b></td>
              <td>${dtStr}</td>
              <td>${custDisplay}<br><small>${esc(o.customerEmail)}</small></td>
              <td>${usd(o.total)}</td>
              <td><span class="badge">${esc(o.status)}</span></td>
              <td>
                <button class="btn sm alt" data-inspect-order="${esc(o.orderId)}">Inspect</button>
              </td>
            </tr>`;
          })
          .join('');

        box.innerHTML = `
          <h1>Orders Management</h1>
          <div class="bar">
            <input id="admOrdSearch" type="search" placeholder="Search Order ID or Customer" value="${esc(qVal)}">
            <select id="admOrdStatus">
              <option value="">All Statuses</option>
              ${['PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED']
                .map(s => `<option value="${s}" ${statusVal === s ? 'selected' : ''}>${s}</option>`)
                .join('')}
            </select>
            <input id="admOrdDate" type="date" value="${esc(dateVal)}">
            <button class="btn sm" id="admOrdFilterBtn">Filter</button>
          </div>
          ${
            !adminOrders.length
              ? '<p>No orders match the current filters.</p>'
              : `<div class="table-wrap">
                  <table class="adm-tbl">
                    <thead>
                      <tr>
                        <th>Order ID</th>
                        <th>Date</th>
                        <th>Customer</th>
                        <th>Total</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>${orderRows}</tbody>
                  </table>
                </div>`
          }
          ${ordersCursor ? '<div style="margin-top:16px"><button class="btn alt sm" id="admMoreOrders">Load next page</button></div>' : ''}
        `;

        $('#admOrdFilterBtn').onclick = () => loadAdminOrders(null, false);
        const moreBtn = $('#admMoreOrders');
        if (moreBtn) moreBtn.onclick = () => loadAdminOrders(ordersCursor, true);

        box.querySelectorAll('[data-inspect-order]').forEach(btn => {
          btn.onclick = () => inspectOrderModal(btn.dataset.inspectOrder);
        });
      } catch (e) {
        box.innerHTML = `<p class="err">${esc(e.message)}</p>`;
      }
    }

    async function inspectOrderModal(orderId) {
      try {
        const o = await apiRequest('/api/admin/orders/' + encodeURIComponent(orderId));
        const mapTransitions = {
          PENDING: ['CONFIRMED', 'CANCELLED'],
          CONFIRMED: ['SHIPPED', 'CANCELLED'],
          SHIPPED: ['DELIVERED'],
          DELIVERED: [],
          CANCELLED: []
        };
        const transitions = mapTransitions[o.status] ? mapTransitions[o.status] : [];
        const itemsList = Array.isArray(o.items) ? o.items : [];
        const itemRows = itemsList
          .map(i => {
            const pName = esc(pick(i.name, i.productId));
            return `<tr>
              <td>${pName}</td>
              <td>${i.quantity}</td>
              <td>${usd(i.unitPrice)}</td>
              <td>${usd(i.unitPrice * i.quantity)}</td>
            </tr>`;
          })
          .join('');

        $('#modal').innerHTML = `
          <div class="mb">
            <div class="mc" style="grid-template-columns:1fr" role="dialog" aria-modal="true">
              <button class="x" aria-label="Close">×</button>
              <h2>Order ${esc(o.orderId)}</h2>
              <p><b>Date:</b> ${esc(o.createdAt)} · <b>Status:</b> <span class="badge">${esc(o.status)}</span></p>
              <p><b>Customer:</b> ${esc(o.customerName)} (${esc(o.customerEmail)})</p>
              <p><b>Shipping Address:</b> ${esc(o.address)} · <b>Payment:</b> ${esc(o.method)}</p>
              <div class="table-wrap">
                <table class="adm-tbl">
                  <thead><tr><th>Product</th><th>Qty</th><th>Unit Price</th><th>Line Total</th></tr></thead>
                  <tbody>${itemRows}</tbody>
                </table>
              </div>
              <p style="text-align:right"><b>Total: ${usd(o.total)}</b></p>
              ${
                transitions.length
                  ? `<div class="row">
                      <label for="newOrdSt"><b>Transition Status:</b></label>
                      <select id="newOrdSt">
                        ${transitions.map(t => `<option value="${t}">${t}</option>`).join('')}
                      </select>
                      <button class="btn sm" id="saveOrdStBtn">Update Status</button>
                    </div>`
                  : '<p><i>Order is in a terminal state.</i></p>'
              }
            </div>
          </div>
        `;

        const saveBtn = $('#saveOrdStBtn');
        if (saveBtn) {
          saveBtn.onclick = async () => {
            const nextSt = $('#newOrdSt').value;
            try {
              await apiRequest('/api/admin/orders/' + encodeURIComponent(orderId) + '/status', {
                method: 'PATCH',
                body: { status: nextSt }
              });
              toast('Order ' + orderId + ' updated to ' + nextSt);
              closeModal();
              loadAdminOrders();
            } catch (e) {
              toast(e.message);
            }
          };
        }
      } catch (e) {
        toast(e.message);
      }
    }

    async function loadAdminProducts() {
      const box = $('#admContent');
      try {
        await loadProducts();
        box.innerHTML = `
          <div class="row" style="border:0">
            <h1>Products Catalog (${P.length})</h1>
            <button class="btn sm" id="newProdBtn">+ Add Product</button>
          </div>
          ${
            !P.length
              ? '<p>No products in catalog.</p>'
              : `<div class="table-wrap">
                  <table class="adm-tbl">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Category</th>
                        <th>Price</th>
                        <th>Stock</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      ${P.map(
                        p => `<tr>
                          <td>${esc(p.id)}</td>
                          <td><b>${esc(p.n)}</b></td>
                          <td>${esc(p.t)}</td>
                          <td>${usd(p.p)}</td>
                          <td>${p.stockQuantity}</td>
                          <td>
                            <button class="btn sm alt" data-edit-prod="${esc(p.id)}">Edit</button>
                            <button class="btn sm danger" data-del-prod="${esc(p.id)}">Delete</button>
                          </td>
                        </tr>`
                      ).join('')}
                    </tbody>
                  </table>
                </div>`
          }
        `;

        $('#newProdBtn').onclick = () => {
          editingProduct = null;
          activeTab = 'product-form';
          renderShell();
        };

        box.querySelectorAll('[data-edit-prod]').forEach(btn => {
          btn.onclick = () => {
            editingProduct = P.find(x => x.id === btn.dataset.editProd) ? P.find(x => x.id === btn.dataset.editProd) : null;
            activeTab = 'product-form';
            renderShell();
          };
        });

        box.querySelectorAll('[data-del-prod]').forEach(btn => {
          btn.onclick = async () => {
            const pid = btn.dataset.delProd;
            const prod = P.find(x => x.id === pid);
            const prodLabel = prod ? prod.n : pid;
            if (!confirm('Delete product "' + prodLabel + '" permanently?')) return;
            try {
              await apiRequest('/api/admin/products/' + encodeURIComponent(pid), { method: 'DELETE' });
              toast('Product deleted.');
              await loadAdminProducts();
            } catch (e) {
              toast(e.message);
            }
          };
        });
      } catch (e) {
        box.innerHTML = `<p class="err">${esc(e.message)}</p>`;
      }
    }

    function renderProductForm() {
      const box = $('#admContent');
      const isEdit = Boolean(editingProduct);
      let uploadedKey = editingProduct ? pick(editingProduct.imageKey, '') : '';
      let uploadedUrl = editingProduct ? pick(editingProduct.imageUrl, '') : '';
      const initName = editingProduct ? esc(editingProduct.n) : '';
      const initPrice = editingProduct ? editingProduct.p : '';
      const initStock = editingProduct ? editingProduct.stockQuantity : 25;
      const initDesc = editingProduct ? esc(editingProduct.description) : '';

      box.innerHTML = `
        <h1>${isEdit ? 'Edit Product: ' + initName : 'Add New Product'}</h1>
        <form class="form" id="admProdForm" style="margin:0;max-width:560px">
          <label for="pfName">Product Name</label>
          <input id="pfName" required maxlength="120" value="${initName}">

          <label for="pfCategory">Category</label>
          <select id="pfCategory">
            <option value="smart" ${editingProduct && editingProduct.t === 'smart' ? 'selected' : ''}>Smartwatch (smart)</option>
            <option value="classic" ${editingProduct && editingProduct.t === 'classic' ? 'selected' : ''}>Classic watch (classic)</option>
          </select>

          <label for="pfPrice">Price (USD)</label>
          <input id="pfPrice" type="number" step="0.01" min="0" required value="${initPrice}">

          <label for="pfStock">Stock Quantity</label>
          <input id="pfStock" type="number" step="1" min="0" required value="${initStock}">

          <label for="pfDesc">Description</label>
          <textarea id="pfDesc" rows="3">${initDesc}</textarea>

          <label for="pfImg">Product Image (JPEG, PNG, WEBP up to 5MB)</label>
          <input id="pfImg" type="file" accept="image/jpeg,image/png,image/webp">
          <div class="preview-box" id="pfPreview">
            ${uploadedUrl ? `<img src="${esc(uploadedUrl)}" alt="Preview">` : '<span>No image</span>'}
          </div>

          <p class="err" id="pfErr"></p>
          <div style="display:flex;gap:12px;margin-top:14px">
            <button class="btn" id="pfSaveBtn">${isEdit ? 'Save Changes' : 'Create Product'}</button>
            <button type="button" class="btn alt" id="pfCancelBtn">Cancel</button>
          </div>
        </form>
      `;

      $('#pfCancelBtn').onclick = () => {
        editingProduct = null;
        activeTab = 'products';
        renderShell();
      };

      $('#pfImg').onchange = e => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = ev => {
          $('#pfPreview').innerHTML = `<img src="${esc(ev.target.result)}" alt="Preview">`;
        };
        reader.readAsDataURL(file);
      };

      $('#admProdForm').onsubmit = async e => {
        e.preventDefault();
        $('#pfErr').textContent = '';
        $('#pfSaveBtn').disabled = true;

        try {
          const file = $('#pfImg').files && $('#pfImg').files[0];
          if (file) {
            try {
              const presign = await apiRequest('/api/admin/images/upload-url', {
                method: 'POST',
                body: {
                  filename: file.name,
                  contentType: file.type,
                  fileSize: file.size
                }
              });
              const putResp = await fetch(presign.uploadUrl, {
                method: 'PUT',
                headers: { 'Content-Type': file.type },
                body: file
              });
              if (!putResp.ok) throw new Error('Direct S3 upload failed');
              uploadedKey = presign.imageKey;
              uploadedUrl = presign.imageUrl;
            } catch {
              const fd = new FormData();
              fd.append('file', file);
              const up = await apiRequest('/api/admin/images/upload', {
                method: 'POST',
                body: fd
              });
              uploadedKey = up.imageKey;
              uploadedUrl = up.imageUrl;
            }
          }

          const payload = {
            name: $('#pfName').value.trim(),
            category: $('#pfCategory').value,
            price: Number($('#pfPrice').value),
            stockQuantity: Number($('#pfStock').value),
            description: $('#pfDesc').value.trim(),
            imageKey: uploadedKey,
            imageUrl: uploadedUrl
          };

          if (isEdit) {
            await apiRequest('/api/admin/products/' + encodeURIComponent(editingProduct.id), {
              method: 'PUT',
              body: payload
            });
            toast('Product updated successfully.');
          } else {
            await apiRequest('/api/admin/products', {
              method: 'POST',
              body: payload
            });
            toast('Product created successfully.');
          }

          editingProduct = null;
          await loadProducts();
          activeTab = 'products';
          renderShell();
        } catch (errObj) {
          $('#pfErr').textContent = errObj.message;
          $('#pfSaveBtn').disabled = false;
        }
      };
    }

    renderShell();
  }
};

document.addEventListener('click', event => {
  if (event.target.classList.contains('mb') || event.target.classList.contains('x')) {
    closeModal();
    return;
  }

  const element = event.target.closest('[data-add], [data-q], [data-wish], [data-open]');
  if (!element) return;
  const data = element.dataset;

  if (data.add) {
    const id = String(data.add).trim();
    const product = P.find(p => p.id === id);
    if (!product || product.stockQuantity <= 0) return;

    const items = cart();
    const existing = items.find(item => String(item.id).trim() === id);
    if (existing) {
      if (existing.q >= product.stockQuantity) {
        toast('Maximum available stock reached');
        return;
      }
      existing.q++;
    } else {
      items.push({ id, q: 1 });
    }

    saveCart(items);
    toast(product.n + ' added to cart');
    return;
  }

  if (data.q) {
    const [id, amount] = data.q.split(':');
    const items = cart();
    const item = items.find(entry => String(entry.id).trim() === id);
    if (!item) return;

    item.q += Number(amount);
    saveCart(items.filter(entry => entry.q > 0));
    relines();
    return;
  }

  if (data.wish) {
    const id = String(data.wish).trim();
    let wishlist = store.get('wish', []);
    wishlist = wishlist.includes(id)
      ? wishlist.filter(item => item !== id)
      : [...wishlist, id];
    store.set('wish', wishlist);
    nav();
    toast(wishlist.includes(id) ? 'Saved to wishlist' : 'Removed from wishlist');
    return;
  }

  if (data.open) {
    openModal(data.open);
  }
});

document.addEventListener('keydown', event => {
  if (event.key === 'Escape') closeModal();
  if (event.key === 'Enter' && event.target.dataset && event.target.dataset.open) {
    openModal(event.target.dataset.open);
  }
});

function route() {
  closeModal();

  if (location.pathname === '/admin' && !location.hash.startsWith('#/admin')) {
    location.hash = '#/admin';
    return;
  }

  const name = location.hash.replace('#/', '') ? location.hash.replace('#/', '') : 'home';
  const targetPage = pages[name] ? pages[name] : pages.home;
  targetPage();
  nav();
  window.scrollTo(0, 0);
}

window.addEventListener('hashchange', route);
window.addEventListener('popstate', route);

const message = $('#mq');
if (message) {
  const messages = [
    'Free shipping over $300',
    'Two-year warranty',
    '30-day returns',
    'Smart and classic collections'
  ];
  message.innerHTML = [...messages, ...messages].map(item => `<span>${item}</span>`).join('');
}

(async function start() {
  nav();
  if ($('#app')) {
    $('#app').innerHTML = '<main class="wrap"><p>Loading SAATI watches...</p></main>';
  }
  try {
    await loadProducts();
    route();
  } catch (error) {
    console.error('SAATI products error:', error);
    if (location.hash === '#/signin' || location.hash === '#/admin' || location.pathname === '/admin') {
      route();
      return;
    }
    if ($('#app')) {
      $('#app').innerHTML = `
        <main class="wrap">
          <h1>Unable to load watches</h1>
          <p>Please check the API configuration and try again.</p>
        </main>
      `;
    }
  }
})();