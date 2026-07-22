// Content script — scrapes product page data and sends it to the background worker.
// Phase 2 work: replace the placeholder selectors below with real scraping logic
// once you're testing against actual retailer sites.

interface ScrapedProduct {
  domain: string;
  imageUrl: string | null;
  materialText: string | null;
  price: string | null;
}

function scrapeProduct(): ScrapedProduct {
  const domain = window.location.hostname;

  // TODO: replace with real selectors once testing against live sites
  const imageUrl = document.querySelector<HTMLImageElement>('img')?.src ?? null;
  const materialText = null;
  const price = null;

  return { domain, imageUrl, materialText, price };
}

// Phase 1/2: just log it. Phase 4: send to background worker -> backend.
console.log('[Thred] scraped product:', scrapeProduct());
