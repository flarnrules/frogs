document.addEventListener('DOMContentLoaded', function() {
    const grid = document.getElementById('imageGrid');
    for (let i = 1; i <= 10; i++) {
        let img = document.createElement('img');
        img.src = `../media/${i}.png`; // Update the path as needed
        grid.appendChild(img);
    }
});
