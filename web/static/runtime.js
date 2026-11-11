/* Transport for API calls.
 *  - "server": plain fetch to FastAPI.
 *  - "browser" (GitHub Pages): the Python package runs in this page via Pyodide;
 *    calls go straight to app.browser.handle(), the same route table FastAPI uses.
 */
window.Runtime = (() => {
  const MODE = window.DEMO_RUNTIME || 'server';
  const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.29.5/full/';
  let handle = null;
  let pyodide = null;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.onload = resolve;
      s.onerror = () => reject(new Error(`could not load ${src}`));
      document.head.append(s);
    });
  }

  async function boot(progress) {
    if (MODE !== 'browser') return;
    progress('boot_runtime', 10);
    await loadScript(PYODIDE + 'pyodide.js');
    pyodide = await window.loadPyodide({ indexURL: PYODIDE });
    const manifest = await (await fetch('py/manifest.json', { cache: 'no-cache' })).json();
    progress('boot_packages', 45);
    await pyodide.loadPackage(manifest.wheels.map((w) => new URL(`py/wheels/${w}`, location.href).href));
    progress('boot_code', 65);
    for (const file of manifest.files) {
      const text = await (await fetch(`py/${file}`, { cache: 'no-cache' })).text();
      const path = `/home/pyodide/${file}`;
      pyodide.FS.mkdirTree(path.slice(0, path.lastIndexOf('/')));
      pyodide.FS.writeFile(path, text);
    }
    progress('boot_seed', 80);
    await new Promise((r) => setTimeout(r, 30)); // let the progress text paint
    pyodide.runPython('import sys; sys.path.insert(0, "/home/pyodide")\nfrom app import browser\nbrowser.boot()');
    handle = pyodide.globals.get('browser').handle;
    progress('', 100);
  }

  const apiPath = (url) => '/' + url.replace(/^\/?/, '').split('?')[0];
  const queryOf = (url) => Object.fromEntries(new URL(url, location.href).searchParams);

  /* Returns {status, json} or {status, file: {blob, filename, inline}}. */
  async function request(method, url, { json, form, lang } = {}) {
    if (MODE !== 'browser') {
      const opts = { method, headers: { 'X-Lang': lang } };
      if (form) opts.body = form;
      else if (json !== undefined) { opts.body = JSON.stringify(json); opts.headers['Content-Type'] = 'application/json'; }
      const res = await fetch(url, opts);
      if ((res.headers.get('content-type') || '').includes('json')) return { status: res.status, json: await res.json() };
      const disp = res.headers.get('content-disposition') || '';
      return { status: res.status, file: { blob: await res.blob(), filename: (disp.match(/filename="([^"]+)"/) || [])[1] || 'file', inline: !disp.startsWith('attachment') } };
    }
    let formJson = null;
    const files = [];
    if (form) {
      const fields = {};
      for (const [k, v] of form.entries()) {
        if (v instanceof File) files.push([v.name, new Uint8Array(await v.arrayBuffer())]);
        else fields[k] = v;
      }
      formJson = JSON.stringify(fields);
    }
    const pyFiles = files.length ? pyodide.toPy(files) : null;
    const res = handle(method, apiPath(url), JSON.stringify(queryOf(url)), json === undefined ? null : JSON.stringify(json),
      formJson, pyFiles, lang);
    const [status, kind, payload, media, filename, inline] = res.toJs();
    res.destroy();
    if (pyFiles) pyFiles.destroy();
    if (kind === 'json') return { status, json: JSON.parse(payload) };
    return { status, file: { blob: new Blob([payload], { type: media }), filename, inline } };
  }

  return { MODE, boot, request };
})();
