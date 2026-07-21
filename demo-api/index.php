<?php
/**
 * Orders API — demo backend para testes de exposição via RHCL.
 *
 * Rotas:
 *   GET /                → landing page (HTML)
 *   GET /api/health      → status do serviço
 *   GET /api/orders      → lista de pedidos
 *   GET /api/orders/{id} → um pedido
 */

$uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);

$orders = [
    ['id' => 1001, 'customer' => 'Ana Souza',      'items' => ['Espresso Duplo', 'Pão de Queijo'], 'total' => 18.50, 'status' => 'delivered'],
    ['id' => 1002, 'customer' => 'Bruno Lima',     'items' => ['Cappuccino', 'Croissant'],          'total' => 24.00, 'status' => 'preparing'],
    ['id' => 1003, 'customer' => 'Carla Menezes',  'items' => ['Cold Brew', 'Cheesecake'],          'total' => 32.90, 'status' => 'pending'],
    ['id' => 1004, 'customer' => 'Diego Ferreira', 'items' => ['Latte', 'Brownie', 'Água'],         'total' => 29.70, 'status' => 'delivered'],
    ['id' => 1005, 'customer' => 'Elisa Prado',    'items' => ['Mocha', 'Torta de Limão'],          'total' => 27.40, 'status' => 'canceled'],
];

function json_response(array $payload, int $status = 200): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Access-Control-Allow-Origin: *');
    header('X-Powered-By: orders-api/1.0');
    echo json_encode($payload, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);
    exit;
}

if ($uri === '/api/health') {
    json_response([
        'status'   => 'ok',
        'service'  => 'orders-api',
        'version'  => '1.0.0',
        'hostname' => gethostname(),
        'time'     => date('c'),
    ]);
}

if ($uri === '/api/orders') {
    json_response(['count' => count($orders), 'orders' => $orders]);
}

if (preg_match('#^/api/orders/(\d+)$#', $uri, $m)) {
    foreach ($orders as $order) {
        if ($order['id'] === (int)$m[1]) {
            json_response($order);
        }
    }
    json_response(['error' => 'order not found', 'id' => (int)$m[1]], 404);
}

if (str_starts_with($uri, '/api')) {
    json_response(['error' => 'route not found', 'path' => $uri], 404);
}

header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Orders API · Demo RHCL</title>
<style>
  :root {
    --bg: #0b0f1a;
    --card: rgba(255, 255, 255, 0.055);
    --border: rgba(255, 255, 255, 0.12);
    --text: #e8ecf4;
    --muted: #93a0b4;
    --accent: #ff7a59;
    --accent2: #7c5cff;
    --ok: #3ecf8e;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    background:
      radial-gradient(1000px 500px at 85% -10%, rgba(124, 92, 255, 0.28), transparent 60%),
      radial-gradient(800px 420px at -10% 110%, rgba(255, 122, 89, 0.22), transparent 60%),
      var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 48px 20px;
  }
  .wrap { max-width: 860px; width: 100%; }
  .badge {
    display: inline-flex; align-items: center; gap: 8px;
    border: 1px solid var(--border); border-radius: 999px;
    padding: 6px 14px; font-size: 13px; color: var(--muted);
    background: var(--card); backdrop-filter: blur(8px);
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ok);
         box-shadow: 0 0 10px var(--ok); animation: pulse 2s infinite; }
  @keyframes pulse { 50% { opacity: 0.45; } }
  h1 {
    margin: 22px 0 10px; font-size: clamp(34px, 6vw, 56px); line-height: 1.05;
    letter-spacing: -0.02em;
  }
  h1 span {
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .sub { color: var(--muted); font-size: 17px; max-width: 560px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 14px; margin-top: 36px; }
  .card {
    background: var(--card); border: 1px solid var(--border); border-radius: 16px;
    padding: 20px; backdrop-filter: blur(8px);
    transition: transform 0.15s ease, border-color 0.15s ease;
  }
  .card:hover { transform: translateY(-3px); border-color: rgba(255,255,255,0.25); }
  .card .method {
    font-size: 11px; font-weight: 700; letter-spacing: 0.08em;
    color: var(--ok); margin-bottom: 8px;
  }
  .card code {
    font-family: "SF Mono", ui-monospace, Menlo, monospace;
    font-size: 14px; color: var(--text); word-break: break-all;
  }
  .card p { color: var(--muted); font-size: 13.5px; margin-top: 8px; line-height: 1.5; }
  .section-title {
    margin: 44px 0 4px; font-size: 22px; letter-spacing: -0.01em;
  }
  .section-sub { color: var(--muted); font-size: 14px; margin-bottom: 16px; }
  .orders { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 14px; }
  .order {
    background: var(--card); border: 1px solid var(--border); border-radius: 16px;
    padding: 18px; backdrop-filter: blur(8px);
  }
  .order .top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .order .oid { font-family: "SF Mono", ui-monospace, Menlo, monospace; font-size: 13px; color: var(--muted); }
  .order .customer { font-weight: 650; font-size: 15.5px; margin-bottom: 6px; }
  .order .items { color: var(--muted); font-size: 13.5px; line-height: 1.55; min-height: 42px; }
  .order .bottom { display: flex; justify-content: space-between; align-items: baseline;
                   margin-top: 12px; padding-top: 12px; border-top: 1px dashed var(--border); }
  .order .total { font-size: 18px; font-weight: 700; }
  .status { font-size: 11px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase;
            border-radius: 999px; padding: 4px 10px; }
  .status.delivered { color: #3ecf8e; background: rgba(62, 207, 142, 0.12); }
  .status.preparing { color: #f7b955; background: rgba(247, 185, 85, 0.12); }
  .status.pending   { color: #6aa9ff; background: rgba(106, 169, 255, 0.12); }
  .status.canceled  { color: #ff6b6b; background: rgba(255, 107, 107, 0.12); }
  .status-line {
    margin-top: 34px; display: flex; align-items: center; gap: 10px;
    color: var(--muted); font-size: 14px; flex-wrap: wrap;
  }
  .chip {
    font-family: "SF Mono", ui-monospace, Menlo, monospace; font-size: 12.5px;
    border: 1px solid var(--border); border-radius: 8px; padding: 4px 10px;
    color: var(--text); background: rgba(0,0,0,0.25);
  }
  footer { margin-top: 40px; color: var(--muted); font-size: 12.5px; }
  footer b { color: var(--text); font-weight: 600; }
  a { color: var(--accent); text-decoration: none; }
</style>
</head>
<body>
  <div class="wrap">
    <span class="badge"><span class="dot"></span> serviço interno · aguardando exposição via RHCL</span>
    <h1>Orders <span>API</span></h1>
    <p class="sub">Backend de demonstração em PHP para o teste de exposição ponta a ponta
    com Red Hat Connectivity Link — Gateway API, HTTPRoute e DNSPolicy.</p>

    <div class="grid">
      <div class="card">
        <div class="method">GET</div>
        <code>/api/health</code>
        <p>Status do serviço, versão e hostname do pod que respondeu.</p>
      </div>
      <div class="card">
        <div class="method">GET</div>
        <code>/api/orders</code>
        <p>Lista completa de pedidos com cliente, itens, total e status.</p>
      </div>
      <div class="card">
        <div class="method">GET</div>
        <code>/api/orders/{id}</code>
        <p>Detalhe de um pedido específico. Experimente <code>/api/orders/1002</code>.</p>
      </div>
    </div>

    <h2 class="section-title">Pedidos agora ☕</h2>
    <p class="section-sub">Renderizados ao vivo a partir de <code>GET /api/orders</code> — a página e a API são o mesmo serviço.</p>
    <div class="orders" id="orders"></div>

    <div class="status-line">
      <span>Respondido por</span> <span class="chip"><?= htmlspecialchars(gethostname()) ?></span>
      <span>em</span> <span class="chip"><?= date('d/m/Y H:i:s') ?></span>
      <span id="live"></span>
    </div>

    <footer>
      <b>orders-api 1.0.0</b> · PHP <?= PHP_VERSION ?> · exposto?
      pergunte ao seu agente: <i>"exponha o service orders-api do namespace demo-apps via RHCL"</i>
    </footer>
  </div>
  <script>
    fetch('/api/health').then(r => r.json()).then(d => {
      document.getElementById('live').innerHTML =
        '<span class="chip" style="color:var(--ok)">API ' + d.status + '</span>';
    }).catch(() => {});

    const labels = { delivered: 'entregue', preparing: 'preparando',
                     pending: 'pendente', canceled: 'cancelado' };
    fetch('/api/orders').then(r => r.json()).then(d => {
      document.getElementById('orders').innerHTML = d.orders.map(o => `
        <div class="order">
          <div class="top">
            <span class="oid">#${o.id}</span>
            <span class="status ${o.status}">${labels[o.status] ?? o.status}</span>
          </div>
          <div class="customer">${o.customer}</div>
          <div class="items">${o.items.join(' · ')}</div>
          <div class="bottom">
            <span class="oid">${o.items.length} itens</span>
            <span class="total">R$ ${o.total.toFixed(2).replace('.', ',')}</span>
          </div>
        </div>`).join('');
    }).catch(() => {
      document.getElementById('orders').innerHTML =
        '<p style="color:var(--muted)">Não foi possível carregar os pedidos.</p>';
    });
  </script>
</body>
</html>
