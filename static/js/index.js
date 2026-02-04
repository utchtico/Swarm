(function () {
    const btn = document.getElementById('user-menu-button');
    const list = document.getElementById('user-menu-list');
    const root = document.getElementById('user-menu');

    function openMenu() {
        list.classList.remove('hidden');
        btn.setAttribute('aria-expanded', 'true');
        // Enfoca el primer elemento del menú
        const firstItem = list.querySelector('[role="menuitem"]');
        if (firstItem) firstItem.focus();
    }

    function closeMenu() {
        list.classList.add('hidden');
        btn.setAttribute('aria-expanded', 'false');
    }

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = btn.getAttribute('aria-expanded') === 'true';
        isOpen ? closeMenu() : openMenu();
    });

    // Cerrar con click afuera
    document.addEventListener('click', (e) => {
        if (!root.contains(e.target)) closeMenu();
    });

    // Cerrar con Esc
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMenu();
    });
})();

(function () {
    const nav = document.querySelector('.navbar-principal');
    const btn = nav.querySelector('.nav-toggle');
    const menu = nav.querySelector('#menu');

    // Toggle
    btn.addEventListener('click', () => {
        const open = nav.classList.toggle('is-open');
        btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    // Cierra al navegar (mejor UX)
    menu.addEventListener('click', (e) => {
        if (e.target.closest('a')) {
            nav.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
        }
    });

    // Opcional: cierra si se hace click fuera
    document.addEventListener('click', (e) => {
        if (!nav.contains(e.target)) {
            nav.classList.remove('is-open');
            btn.setAttribute('aria-expanded', 'false');
        }
    });
})();