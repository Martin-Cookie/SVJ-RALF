/* SVJ Správa – Client-side JavaScript */

// === Dark mode toggle ===
(function initDarkMode() {
    const toggle = document.getElementById('dark-toggle');
    const html = document.documentElement;

    // Load preference
    const stored = localStorage.getItem('darkMode');
    if (stored === 'true' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        html.classList.add('dark');
    }

    if (toggle) {
        toggle.addEventListener('click', function () {
            html.classList.toggle('dark');
            localStorage.setItem('darkMode', html.classList.contains('dark'));
        });
    }
})();

// === Mobile sidebar toggle ===
(function initSidebar() {
    const btn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    if (btn && sidebar) {
        btn.addEventListener('click', function () {
            sidebar.classList.toggle('max-md:-translate-x-full');
        });
        // Close on outside click
        document.addEventListener('click', function (e) {
            if (!sidebar.contains(e.target) && !btn.contains(e.target)) {
                sidebar.classList.add('max-md:-translate-x-full');
            }
        });
    }
})();

// === Keyboard shortcuts ===
(function initShortcuts() {
    let gPressed = false;
    let gTimeout = null;

    function isInputFocused() {
        const el = document.activeElement;
        return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
    }

    document.addEventListener('keydown', function (e) {
        // Don't capture when typing in input fields
        if (isInputFocused()) {
            // Escape blurs the current input
            if (e.key === 'Escape') {
                document.activeElement.blur();
                e.preventDefault();
            }
            return;
        }

        // Ctrl+K or / — focus search
        if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || e.key === '/') {
            e.preventDefault();
            const search = document.getElementById('global-search');
            if (search) search.focus();
            return;
        }

        // Escape — close modals/dropdowns
        if (e.key === 'Escape') {
            document.getElementById('shortcuts-modal')?.classList.add('hidden');
            document.getElementById('shortcuts-modal')?.classList.remove('flex');
            document.getElementById('notif-dropdown')?.classList.add('hidden');
            return;
        }

        // ? — show shortcuts help
        if (e.key === '?') {
            e.preventDefault();
            const modal = document.getElementById('shortcuts-modal');
            if (modal) {
                modal.classList.toggle('hidden');
                modal.classList.toggle('flex');
            }
            return;
        }

        // G + key navigation
        if (e.key.toLowerCase() === 'g' && !gPressed) {
            gPressed = true;
            clearTimeout(gTimeout);
            gTimeout = setTimeout(function () { gPressed = false; }, 1000);
            return;
        }

        if (gPressed) {
            gPressed = false;
            clearTimeout(gTimeout);
            var routes = { d: '/', v: '/vlastnici', j: '/jednotky', h: '/hlasovani' };
            var route = routes[e.key.toLowerCase()];
            if (route) {
                e.preventDefault();
                window.location.href = route;
            }
        }
    });
})();

// === Notification dropdown toggle ===
(function initNotifications() {
    const bell = document.getElementById('notif-bell');
    const dropdown = document.getElementById('notif-dropdown');
    if (bell && dropdown) {
        bell.addEventListener('click', function () {
            dropdown.classList.toggle('hidden');
        });
        document.addEventListener('click', function (e) {
            const wrapper = document.getElementById('notif-wrapper');
            if (wrapper && !wrapper.contains(e.target)) {
                dropdown.classList.add('hidden');
            }
        });
    }
})();

// === HTMX search results visibility ===
document.addEventListener('htmx:afterSwap', function (e) {
    if (e.detail.target.id === 'search-results') {
        var results = document.getElementById('search-results');
        var input = document.getElementById('global-search');
        if (results && input && input.value.length >= 2) {
            results.classList.remove('hidden');
        } else if (results) {
            results.classList.add('hidden');
        }
    }
});

// Hide search results on blur
document.addEventListener('click', function (e) {
    var results = document.getElementById('search-results');
    var input = document.getElementById('global-search');
    if (results && input && !input.contains(e.target) && !results.contains(e.target)) {
        results.classList.add('hidden');
    }
});

// === Client-side table sorting ===
(function initSortable() {
    document.querySelectorAll('[data-sort-table]').forEach(function (table) {
        var sortState = {};
        table.querySelectorAll('th[data-sort]').forEach(function (th) {
            th.addEventListener('click', function () {
                var colIdx = parseInt(th.getAttribute('data-sort'));
                var tbody = table.querySelector('tbody');
                if (!tbody) return;
                var rows = Array.from(tbody.querySelectorAll('tr'));
                var asc = sortState[colIdx] !== 'asc';
                sortState[colIdx] = asc ? 'asc' : 'desc';

                rows.sort(function (a, b) {
                    var cellA = a.cells[colIdx];
                    var cellB = b.cells[colIdx];
                    if (!cellA || !cellB) return 0;
                    var va = (cellA.textContent || '').trim();
                    var vb = (cellB.textContent || '').trim();
                    // Try numeric comparison
                    var na = parseFloat(va.replace(/[^\d.\-]/g, ''));
                    var nb = parseFloat(vb.replace(/[^\d.\-]/g, ''));
                    if (!isNaN(na) && !isNaN(nb)) {
                        return asc ? na - nb : nb - na;
                    }
                    // Fallback to locale string comparison
                    var cmp = va.localeCompare(vb, 'cs', { sensitivity: 'base' });
                    return asc ? cmp : -cmp;
                });

                rows.forEach(function (row) { tbody.appendChild(row); });

                // Update header arrows
                table.querySelectorAll('th[data-sort]').forEach(function (h) {
                    var txt = h.textContent.replace(/[↑↓↕]/g, '').trim();
                    if (h === th) {
                        h.textContent = txt + (asc ? ' ↑' : ' ↓');
                    } else {
                        h.textContent = txt + ' ↕';
                    }
                });
            });
        });
    });
})();
