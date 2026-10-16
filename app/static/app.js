/* Interações da interface. Os formulários e os dados continuam no servidor. */
document.addEventListener('DOMContentLoaded', () => {
  const now = new Date();
  const shortDate = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
  const month = new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' });
  const week = new Intl.DateTimeFormat('pt-BR', { weekday: 'long' });
  document.querySelectorAll('[data-local-date]').forEach((el) => {
    const kind = el.dataset.localDate;
    el.textContent = kind === 'day' ? String(now.getDate()).padStart(2, '0')
      : kind === 'month' ? month.format(now)
      : kind === 'weekday' ? week.format(now) : shortDate.format(now);
  });
  document.addEventListener('input', (e) => {
    if (e.target.classList?.contains('money')) e.target.value = e.target.value.replace(/[^0-9.,-]/g, '');
  });
  document.querySelectorAll('[data-password-toggle]').forEach((button) => {
    const field = document.getElementById(button.dataset.passwordToggle);
    if (!field) return;
    button.addEventListener('click', () => {
      const show = field.type === 'password';
      field.type = show ? 'text' : 'password';
      button.setAttribute('aria-label', show ? 'Ocultar senha' : 'Mostrar senha');
      button.setAttribute('aria-pressed', String(show));
      button.querySelector('i').className = show ? 'bi bi-eye-slash' : 'bi bi-eye';
    });
  });
  const tabs = document.querySelector('.premium-tabs');
  const active = tabs?.querySelector('.active');
  if (tabs && active && tabs.scrollWidth > tabs.clientWidth) {
    tabs.scrollLeft = active.offsetLeft - tabs.offsetLeft - 20;
  }
  // Os diálogos ficam fora do conteúdo para não criarem camadas sobrepostas.
  document.querySelectorAll('main .modal').forEach((modal) => document.body.appendChild(modal));
});
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/static/sw.js').catch(() => {}));
}
