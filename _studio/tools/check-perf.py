"""The homepage figure must stay cheap while idle on a phone. Serves the repo
root, loads / as a 390x844 phone at 3x with the CPU slowed 4x, lets the
animation settle, then sums requestAnimationFrame callback time over 5 s.
Fails above the budget or on any console error. Exits non-zero on failure.

    python _studio/tools/check-perf.py
"""
import pathlib, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUDGET = 300.0   # ms of rAF callback time per second, idle
SETTLE = 4.0     # s
WINDOW = 5.0     # s

WRAP = """
(function(){
  var raf = window.requestAnimationFrame.bind(window);
  window.__rafMs = 0; window.__rafN = 0;
  window.requestAnimationFrame = function(cb){
    return raf(function(t){
      var s = performance.now();
      try { cb(t); } finally { window.__rafMs += performance.now() - s; window.__rafN++; }
    });
  };
})();
"""


def free_port():
    while True:
        s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
        if port != 8123:
            return port


def main():
    port = free_port()
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    errors = []
    try:
        for _ in range(50):
            try:
                socket.create_connection(('127.0.0.1', port), .2).close(); break
            except OSError:
                time.sleep(.1)
        with sync_playwright() as pw:
            br = pw.chromium.launch(channel='chrome')
            ctx = br.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=3,
                                 is_mobile=True, has_touch=True)
            ctx.route('**/googletagmanager.com/**', lambda r: r.fulfill(body='', content_type='text/javascript'))
            ctx.add_init_script(WRAP)
            page = ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            cdp = ctx.new_cdp_session(page)
            cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
            page.goto(f'http://127.0.0.1:{port}/', wait_until='load')
            time.sleep(SETTLE)
            page.evaluate('window.__rafMs = 0; window.__rafN = 0')
            t = time.perf_counter()
            time.sleep(WINDOW)
            ms, n = page.evaluate('[window.__rafMs, window.__rafN]')
            dt = time.perf_counter() - t
            br.close()
    finally:
        srv.terminate(); srv.wait()

    per = ms / dt
    print(f'idle rAF script: {per:.0f} ms/s ({ms:.0f} ms over {dt:.1f} s, {n} callbacks, '
          f'{n/dt:.1f} fps, {ms/max(n,1):.1f} ms each), budget {BUDGET:.0f} ms/s')
    fail = []
    if n / dt < 20:
        fail.append(f'the animation is not running: {n/dt:.1f} callbacks a second')
    if per > BUDGET:
        fail.append(f'over budget: {per:.0f} > {BUDGET:.0f} ms/s')
    for e in errors:
        fail.append(f'console error: {e}')
    if fail:
        print('\n'.join(fail)); sys.exit(1)
    print('perf ok')


if __name__ == '__main__':
    main()
