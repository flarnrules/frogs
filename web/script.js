document.addEventListener('DOMContentLoaded', function() {
    const grid = document.getElementById('imageGrid');
    for (let i = 1; i <= 300; i++) {
        let img = document.createElement('img');
        img.src = `../nfts/images/${i}.png`; // Update the path as needed
        grid.appendChild(img);
    }
});
