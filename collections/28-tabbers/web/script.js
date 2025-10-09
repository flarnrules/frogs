document.addEventListener('DOMContentLoaded', function() {
    const grid = document.getElementById('imageGrid');
    const columnSlider = document.getElementById('columnSlider');
    const traitFilter = document.getElementById('traitFilter');

    let metadata = [];
    const BATCH_SIZE = 100;  // Adjust the batch size as needed
    let totalNFTs = 2222;

    // Function to update the number of columns
    function updateColumns(numColumns) {
        grid.style.gridTemplateColumns = `repeat(${numColumns}, 1fr)`;
    }

    // Function to load images based on selected batch
    function loadImages(batchName) {
        grid.innerHTML = ''; // Clear existing images
        metadata = []; // Clear existing metadata
        loadMetadataInBatches(1, totalNFTs, batchName);
    }

    // Function to load metadata in batches
    function loadMetadataInBatches(start, end, batchName) {
        let promises = [];
        for (let i = start; i <= Math.min(end, start + BATCH_SIZE - 1); i++) {
            promises.push(fetch(`../nfts/metadata/${i}.json`)
                .then(response => {
                    if (!response.ok) {
                        console.error(`Failed to fetch metadata for ${i}`);
                        return null; // Return null if fetching fails
                    }
                    return response.json();
                })
                .then(data => {
                    if (data !== null) {
                        metadata.push(data);
                    }
                })
                .catch(error => console.error(`Error fetching metadata for ${i}:`, error)));
        }

        Promise.all(promises).then(() => {
            if (start + BATCH_SIZE <= end) {
                loadMetadataInBatches(start + BATCH_SIZE, end, batchName);
            } else {
                console.log('Metadata loaded:', metadata);
                populateTraitFilter(metadata);
                displayImages(metadata);
            }
        });
    }

    // Function to populate the trait filter
    function populateTraitFilter(data) {
        const traits = {};
        data.forEach(item => {
            item.attributes.forEach(attr => {
                if (!traits[attr.trait_type]) {
                    traits[attr.trait_type] = {};
                }
                if (!traits[attr.trait_type][attr.value]) {
                    traits[attr.trait_type][attr.value] = 0;
                }
                traits[attr.trait_type][attr.value]++;
            });
        });

        traitFilter.innerHTML = '<option value="all">All Traits</option>';
        for (const traitType in traits) {
            for (const traitValue in traits[traitType]) {
                const option = document.createElement('option');
                option.value = `${traitType}:${traitValue}`;
                option.textContent = `${traitType}: ${traitValue} (${traits[traitType][traitValue]})`;
                traitFilter.appendChild(option);
            }
        }
    }

    // Function to check existence of images
    function checkImageExists(url) {
        return fetch(url, { method: 'HEAD' })
            .then(response => response.ok)
            .catch(() => false);
    }

    // Function to display images and GIFs
    async function displayImages(data) {
        for (let item of data) {
            const imgId = item.name.split('#')[1]; // Extract the image ID from the name
            const pngPath = `../nfts/images/${imgId}.png`;
            const gifPath = `../nfts/images/${imgId}.gif`;

            let mediaElement = document.createElement('img');
            mediaElement.dataset.traits = JSON.stringify(item.attributes);
            mediaElement.dataset.id = imgId; // Store the image ID
            mediaElement.classList.add('nft-image');

            const gifExists = await checkImageExists(gifPath);
            if (gifExists) {
                mediaElement.src = gifPath;
            } else {
                mediaElement.src = pngPath;
            }

            mediaElement.onerror = function() {
                console.error(`Failed to load image for ID ${imgId}`);
            };

            grid.appendChild(mediaElement);
        }
    }

    // Function to filter images by selected trait
    function filterByTrait(trait) {
        const images = grid.getElementsByTagName('img');
        let visibleCount = 0;
        for (const img of images) {
            const traits = JSON.parse(img.dataset.traits);
            if (trait === 'all' || traits.some(attr => `${attr.trait_type}:${attr.value}` === trait)) {
                img.style.display = '';
                visibleCount++;
            } else {
                img.style.display = 'none';
            }
        }
        console.log(`Visible images: ${visibleCount}`);
    }

    // Setup initial columns and load initial batch
    updateColumns(columnSlider.value);
    loadImages('images'); // Default batch

    // Event listener for column slider
    columnSlider.addEventListener('input', function() {
        updateColumns(this.value);
    });

    // Add hover event listener to display NFT ID
    grid.addEventListener('mouseover', function(event) {
        if (event.target.tagName === 'IMG') {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.innerText = `ID: ${event.target.dataset.id}`;
            document.body.appendChild(tooltip);

            function positionTooltip(e) {
                tooltip.style.left = `${e.pageX + 10}px`;
                tooltip.style.top = `${e.pageY + 10}px`;
            }

            positionTooltip(event);

            event.target.addEventListener('mousemove', positionTooltip);

            event.target.addEventListener('mouseout', function() {
                tooltip.remove();
            }, { once: true });
        }
    });

    // Expose functions to global scope so they can be called from HTML
    window.updateColumns = updateColumns;
    window.loadImages = loadImages;
    window.filterByTrait = filterByTrait;
});
