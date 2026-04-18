document.addEventListener('DOMContentLoaded', () => {
    // Mobile Menu Toggle
    const toggler = document.querySelector('.navbar-toggler');
    const menu = document.querySelector('.navbar-menu-pill');

    if (toggler && menu) {
        toggler.addEventListener('click', () => {
            menu.classList.toggle('show');
            const expanded = toggler.getAttribute('aria-expanded') === 'true' || false;
            toggler.setAttribute('aria-expanded', !expanded);
        });
    }

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (menu && menu.classList.contains('show') && !menu.contains(e.target) && !toggler.contains(e.target)) {
            menu.classList.remove('show');
            toggler.setAttribute('aria-expanded', 'false');
        }
    });

    // Active Link Highlighting
    const currentPath = window.location.pathname;
    const links = document.querySelectorAll('.nav-link');

    links.forEach(link => {
        if (link.getAttribute('href') === currentPath || (currentPath === '/' && link.getAttribute('href').endsWith('index.html'))) {
            link.classList.add('active');
        }
    });
});
