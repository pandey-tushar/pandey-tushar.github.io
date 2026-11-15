"""The homepage must stay cheap on a phone. Serves the repo root, loads / as a
390x844 phone at 3x with the CPU slowed 4x, then measures main-thread task time
per second in three windows: idle, scrolling the page top to bottom and back,
and working the lattice figure (flipping qubits and pressing Correct). Fails
above the budget in any window, if anything animates while idle, or on any
console error. Exits non-zero on failure.

    python _studio/tools/check-perf.py
"""
import pathlib, re, socket, subprocess, sys, time
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
BUDGET = 300.0   # ms of main-thread task time per second
IDLE_FPS = 2.0   # rAF callbacks a second allowed while nobody touches the page
SETTLE = 2.0     # s
WINDOW = 5.0     # s

WRAP = """
(function(){
  var raf = window.requestAnimationFrame.bind(window);
  window.__rafN = 0;
  window.requestAnimationFrame = function(cb){
    return raf(function(t){ window.__rafN++; cb(t); });
  };
})();
"""


def free_port():
    while True:
        s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
        if port != 8123:
            return port


def task_ms(cdp):
    m = {x['name']: x['value'] for x in cdp.send('Performance.getMetrics')['metrics']}
    return m['TaskDuration'] * 1000


def measure(page, cdp, act):
    t0, k0 = time.perf_counter(), task_ms(cdp)
    act()
    rest = WINDOW - (time.perf_counter() - t0)
    if rest > 0:
        time.sleep(rest)
    dt = time.perf_counter() - t0
    return (task_ms(cdp) - k0) / dt, dt


def main():
    port = free_port()
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '--bind', '127.0.0.1'],
                           cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    errors, out = [], {}
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
            ctx.route(re.compile(r'googletagmanager\.com'), lambda r: r.fulfill(body='', content_type='text/javascript'))
            ctx.add_init_script(WRAP)
            page = ctx.new_page()
            page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
            page.on('pageerror', lambda e: errors.append(str(e)))
            cdp = ctx.new_cdp_session(page)
            cdp.send('Performance.enable')
            cdp.send('Emulation.setCPUThrottlingRate', {'rate': 4})
            page.goto(f'http://127.0.0.1:{port}/', wait_until='load')
            time.sleep(SETTLE)

            n0 = page.evaluate('window.__rafN')
            out['idle'] = measure(page, cdp, lambda: None)
            fps = (page.evaluate('window.__rafN') - n0) / out['idle'][1]

            def scroll():
                h = page.evaluate('document.documentElement.scrollHeight')
                for dy in [160] * (h // 160 + 1) + [-320] * (h // 320 + 1):
                    page.mouse.wheel(0, dy)
                    time.sleep(.02)
            out['scroll'] = measure(page, cdp, scroll)

            qs = page.locator('#lattice [data-q]')
            fix = page.locator('#fix')
            page.evaluate('window.scrollTo(0,0)')
            if qs.count() == 0 or fix.count() == 0:
                errors.append('no lattice figure: #lattice [data-q] and #fix not found')
            else:
                # one in-page script taps at a quick person's pace, a tap or a press of
                # Correct every 0.4 s: a Playwright call per tap would bill its own
                # injected work to the page's main thread
                def work():
                    page.evaluate('''async () => {
                      const q = document.querySelectorAll('#lattice [data-q]'), fix = document.getElementById('fix');
                      const wait = ms => new Promise(r => setTimeout(r, ms));
                      for (let i = 0; i < 9; i++) {
                        q[(i * 7) % q.length].dispatchEvent(new MouseEvent('click', {bubbles: true}));
                        await wait(400);
                        if (i % 3 == 2) { fix.click(); await wait(400); }
                      }
                    }''')
                out['figure'] = measure(page, cdp, work)
            br.close()
    finally:
        srv.terminate(); srv.wait()

    fail = []
    for k, (per, dt) in out.items():
        print(f'{k}: {per:.0f} ms/s main-thread task time over {dt:.1f} s, budget {BUDGET:.0f} ms/s')
        if per > BUDGET:
            fail.append(f'{k}: over budget: {per:.0f} > {BUDGET:.0f} ms/s')
    if 'idle' in out:
        print(f'idle: {fps:.1f} animation callbacks a second, allowed {IDLE_FPS:.0f}')
        if fps > IDLE_FPS:
            fail.append(f'idle: something animates while nobody touches the page ({fps:.1f}/s)')
    for e in errors:
        fail.append(f'error: {e}')
    if fail:
        print('\n'.join(fail)); sys.exit(1)
    print('perf ok')


if __name__ == '__main__':
    main()
