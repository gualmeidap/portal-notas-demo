/* Boot-screen strings and the production (Portuguese) status names.
   Everything else is written inline with L(en, pt) in app.js / pages.js, so each
   screen keeps both languages side by side. Messages from the Python side arrive
   already translated (the API reads the X-Lang header). */
window.I18N = {
  en: {
    boot_note: 'The real Python code is starting inside your browser (WebAssembly). Nothing is sent to a server.',
    boot_runtime: 'Loading the Python runtime…', boot_packages: 'Loading pypdf and openpyxl…',
    boot_code: 'Loading the application code…', boot_seed: 'Reading ~40 fictional PDFs to build two months of history…',
    boot_failed: 'Could not start the demo in this browser: ',
  },
  pt: {
    boot_note: 'O código Python real está iniciando dentro do seu navegador (WebAssembly). Nada é enviado a um servidor.',
    boot_runtime: 'Carregando o runtime Python…', boot_packages: 'Carregando pypdf e openpyxl…',
    boot_code: 'Carregando o código da aplicação…', boot_seed: 'Lendo ~40 PDFs fictícios para montar dois meses de histórico…',
    boot_failed: 'Não foi possível iniciar a demo neste navegador: ',
  },
};

window.STATUS_LABELS = {
  'Pending': 'Pendente', 'Missing invoice': 'Sem Nota Fiscal', 'Awaiting Purchasing': 'Aguardando Compras',
  'Ready for Fiscal': 'Aguardando Envio Fiscal', 'Awaiting Fiscal': 'Aguardando Fiscal', 'Awaiting Cover': 'Aguardando Capa',
  'Ready to print': 'Pronto para Impressão', 'Completed': 'Concluído', 'Deleted': 'Excluído',
};
