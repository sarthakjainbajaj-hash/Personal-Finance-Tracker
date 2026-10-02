// ==========================================================================
// Personal Finance Tracker - Client Interactions
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
    // 1. Auto-fill current date for date inputs if not already specified
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach((input) => {
        if (!input.value) {
            const today = new Date();
            const yyyy = today.getFullYear();
            const mm = String(today.getMonth() + 1).padStart(2, '0');
            const dd = String(today.getDate()).padStart(2, '0');
            input.value = `${yyyy}-${mm}-${dd}`;
        }
    });

    // 2. Mobile Sidebar Toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            sidebar.classList.toggle('show');
        });

        // Close when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth < 992 && sidebar.classList.contains('show')) {
                if (!sidebar.contains(e.target) && e.target !== sidebarToggle) {
                    sidebar.classList.remove('show');
                }
            }
        });
    }

    // 3. Category quick-select pills in Transactions form
    const catPills = document.querySelectorAll('.cat-pill');
    const categoryInput = document.querySelector('input[name="category"]');
    if (catPills.length > 0 && categoryInput) {
        catPills.forEach((pill) => {
            pill.addEventListener('click', () => {
                categoryInput.value = pill.getAttribute('data-category') || pill.textContent.trim();
                categoryInput.focus();
            });
        });
    }

    // 4. Password Visibility Toggle
    const togglePasswordButtons = document.querySelectorAll('.toggle-password-btn');
    togglePasswordButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const targetInput = document.getElementById(targetId) || btn.previousElementSibling;
            if (targetInput && targetInput.tagName === 'INPUT') {
                const isPassword = targetInput.type === 'password';
                targetInput.type = isPassword ? 'text' : 'password';
                const icon = btn.querySelector('i');
                if (icon) {
                    icon.classList.toggle('bi-eye', !isPassword);
                    icon.classList.toggle('bi-eye-slash', isPassword);
                }
            }
        });
    });

    // 5. Confirm deletion safety
    const confirmForms = document.querySelectorAll('form[data-confirm-delete]');
    confirmForms.forEach((form) => {
        form.addEventListener('submit', (event) => {
            const confirmMsg = form.getAttribute('data-confirm-message') || 'Are you sure you want to delete this? This action cannot be undone.';
            if (!window.confirm(confirmMsg)) {
                event.preventDefault();
            }
        });
    });

    // 6. Global Chart.js styling defaults (if Chart is loaded)
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = "'Plus Jakarta Sans', -apple-system, sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#64748b';
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
    }
});
