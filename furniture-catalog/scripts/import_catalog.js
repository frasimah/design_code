const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const PRODUCTS_FILE = path.join(PROJECT_ROOT, 'data', 'processed', 'full_catalog.json');

function importCatalog() {
    const args = process.argv.slice(2);
    if (args.length < 1) {
        console.error("Usage: node scripts/import_catalog.js <path_to_new_catalog.json>");
        process.exit(1);
    }

    const newCatalogPath = args[0];

    try {
        // Read existing products
        let existingProducts = [];
        if (fs.existsSync(PRODUCTS_FILE)) {
            const fileContent = fs.readFileSync(PRODUCTS_FILE, 'utf-8');
            try {
                existingProducts = JSON.parse(fileContent);
            } catch (e) {
                console.warn("Could not parse existing products.json, starting fresh.");
                existingProducts = [];
            }
        }

        // Read new catalog
        const newCatalogContent = fs.readFileSync(newCatalogPath, 'utf-8');
        let newProducts = JSON.parse(newCatalogContent);

        // Generate slugs if missing and normalize category
        newProducts = newProducts.map(p => {
            if (!p.slug) {
                const source = p.name || p.title || 'untitled-product';
                p.slug = source.toLowerCase()
                    .replace(/[^a-z0-9]+/g, '-')
                    .replace(/(^-|-$)+/g, '');
            }

            // Normalize category: map 'categories' string to 'category' field
            if (!p.category && p.categories) {
                // Take the first category, splitting by comma if present
                const parts = p.categories.toString().split(',');
                p.category = parts[0].trim();
            } else if (!p.category) {
                // Default if missing
                p.category = 'Uncategorized';
            }

            return p;
        });

        if (!Array.isArray(newProducts)) {
            throw new Error("New catalog must be a JSON array of products.");
        }

        console.log(`Found ${newProducts.length} products to import.`);

        // Simple merge strategy: append new products
        // In a real app, you might want to check for duplicates by ID or slug
        const mergedProducts = [...existingProducts, ...newProducts];

        // Write back to file
        fs.writeFileSync(PRODUCTS_FILE, JSON.stringify(mergedProducts, null, 2));

        console.log(`Successfully imported. Total products now: ${mergedProducts.length}`);

    } catch (error) {
        console.error("Error importing catalog:", error.message);
        process.exit(1);
    }
}

importCatalog();
