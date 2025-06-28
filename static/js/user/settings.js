document.addEventListener('DOMContentLoaded', function () {
    const tabs = document.querySelectorAll('.tab-link');
    const sections = document.querySelectorAll('.tab-content');

    const activateTab = function(tabToActivate) {
        if (!tabToActivate) return; 

        const targetId = tabToActivate.dataset.target;
        const targetSection = document.getElementById(targetId + '-section');

        // Deactivate all tabs and hide all sections
        tabs.forEach(t => {
            t.classList.remove('bg-gray-100', 'text-gray-900', 'border-purple-500');
            t.classList.add('text-gray-600', 'hover:bg-gray-50', 'border-transparent');
        });
        sections.forEach(s => {
            s.classList.add('hidden');
        });

        // Activate the target tab and section
        tabToActivate.classList.add('bg-gray-100', 'text-gray-900', 'border-purple-500');
        tabToActivate.classList.remove('text-gray-600', 'hover:bg-gray-50', 'border-transparent');
        if (targetSection) {
            targetSection.classList.remove('hidden');
        }
    };

    tabs.forEach(tab => {
        tab.addEventListener('click', function (e) {
            e.preventDefault();
            activateTab(this);
            
            if (history.pushState) {
                history.pushState(null, null, '#' + this.dataset.target);
            } else {
                window.location.hash = this.dataset.target;
            }
        });
    });

    // Handle initial page load
    const currentHash = window.location.hash.substring(1);
    let tabToActivateOnLoad = null;
    if (currentHash) {
        tabToActivateOnLoad = document.querySelector(`.tab-link[data-target="${currentHash}"]`);
    }

    // Activate the tab from the hash, or the first tab as a default
    activateTab(tabToActivateOnLoad || (tabs.length > 0 ? tabs[0] : null));
}); 