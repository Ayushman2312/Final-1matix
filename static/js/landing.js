document.addEventListener('DOMContentLoaded', () => {
    // Mobile menu toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', () => {
            const isOpen = mobileMenu.classList.contains('opacity-100');

            if (isOpen) {
                mobileMenu.classList.remove('max-h-screen', 'opacity-100', 'py-8');
                mobileMenu.classList.add('max-h-0', 'opacity-0');
            } else {
                mobileMenu.classList.remove('max-h-0', 'opacity-0');
                mobileMenu.classList.add('max-h-screen', 'opacity-100', 'py-8');
            }
        });
    }
}); 