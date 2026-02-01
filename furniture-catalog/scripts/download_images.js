const fs = require('fs');
const path = require('path');
const https = require('https');
const { promisify } = require('util');
const stream = require('stream');
const pipeline = promisify(stream.pipeline);

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const SOURCE_JSON_PATH = path.join(PROJECT_ROOT, 'products.json');
const OUTPUT_JSON_PATH = path.join(PROJECT_ROOT, 'products_local.json');
const IMAGES_DIR = path.join(__dirname, '../public/product-images');

if (!fs.existsSync(IMAGES_DIR)) {
    fs.mkdirSync(IMAGES_DIR, { recursive: true });
}

async function downloadImage(url, filepath) {
    return new Promise((resolve, reject) => {
        const file = fs.createWriteStream(filepath);
        https.get(url, (response) => {
            if (response.statusCode !== 200) {
                reject(new Error(`Failed to download image: ${response.statusCode}`));
                return;
            }
            response.pipe(file);
            file.on('finish', () => {
                file.close(resolve);
            });
        }).on('error', (err) => {
            fs.unlink(filepath, () => { }); // Delete partial file
            reject(err);
        });
    });
}

(async () => {
    try {
        console.log(`Reading products from ${SOURCE_JSON_PATH}...`);
        const content = fs.readFileSync(SOURCE_JSON_PATH, 'utf-8');
        const products = JSON.parse(content);

        console.log(`Found ${products.length} products. Starting image download...`);

        let processedCount = 0;
        for (const product of products) {
            // Generate slug if missing (same logic as import)
            if (!product.slug) {
                const source = product.name || product.title || 'untitled-product';
                product.slug = source.toLowerCase()
                    .replace(/[^a-z0-9]+/g, '-')
                    .replace(/(^-|-$)+/g, '');
            }

            if (product.images && product.images.length > 0) {
                const imageUrl = product.images[0];
                const extension = path.extname(imageUrl).split('?')[0] || '.jpg';
                const filename = `${product.slug}${extension}`;
                const localPath = path.join(IMAGES_DIR, filename);
                const publicPath = `/product-images/${filename}`;

                // Check if file already exists to avoid re-downloading
                if (!fs.existsSync(localPath)) {
                    try {
                        console.log(`Downloading image for ${product.slug}...`);
                        await downloadImage(imageUrl, localPath);
                    } catch (err) {
                        console.error(`Error downloading ${imageUrl}: ${err.message}`);
                        continue; // Skip image update if download fails
                    }
                }

                // Update product image path to local
                product.images[0] = publicPath;
            }
            processedCount++;
            if (processedCount % 10 === 0) console.log(`Processed ${processedCount}/${products.length}...`);
        }

        console.log(`Saving updated products to ${OUTPUT_JSON_PATH}...`);
        fs.writeFileSync(OUTPUT_JSON_PATH, JSON.stringify(products, null, 2));
        console.log('Done!');

    } catch (error) {
        console.error('Script failed:', error);
    }
})();
