document.addEventListener('DOMContentLoaded', function() {
    const grid = document.getElementById('imageGrid');
    for (let i = 1; i <= 120; i++) {
        let img = document.createElement('img');
        img.onerror = function() {
            // If PNG fails to load, try with GIF
            this.src = `../media/${i}.gif`; // Update the path as needed
        };
        img.src = `../media/${i}.png`; // Tries to load PNG first
        grid.appendChild(img);
    }
});
