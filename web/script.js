document.addEventListener('DOMContentLoaded', function() {
    const grid = document.getElementById('imageGrid');
    for (let i = 1; i <= 420; i++) {
        let img = document.createElement('img');
        img.onerror = function() {
            // If PNG fails to load, try with GIF
            this.src = `../nfts/images/${i}.gif`; // Update the path as needed
        };
        img.src = `../nfts/images/${i}.png`; // Tries to load PNG first
        grid.appendChild(img);
    }
});
