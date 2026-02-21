document.body.addEventListener('htmx:beforeSwap', function(evt) {
    if (evt.detail.target.id === 'main-view' || evt.detail.target.id === 'video-grid') {
        evt.detail.target.classList.add('opacity-50');
    }
});

document.body.addEventListener('htmx:afterSwap', function(evt) {
    if (evt.detail.target.id === 'main-view' || evt.detail.target.id === 'video-grid') {
        evt.detail.target.classList.remove('opacity-50');
        evt.detail.target.classList.add('animate-in', 'fade-in', 'duration-500');
    }
});

// Update active state in sidebar
document.querySelectorAll('.sidebar-link').forEach(link => {
    link.addEventListener('click', function() {
        document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active', 'text-neon-orange'));
        document.querySelectorAll('.sidebar-link').forEach(l => l.classList.add('text-gray-400'));
        this.classList.add('active', 'text-neon-orange');
        this.classList.remove('text-gray-400');
    });
});

console.log("Nocta Trends Pro UI Loaded.");
