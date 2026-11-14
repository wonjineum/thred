// Background service worker. It talks to the FastAPI backend and saves the
// results in chrome.storage so the popup can show them.
//
// Flow:
//   content.ts finds the cart ASINs  ->  SCRAPE_AMAZON_CART message
//   1. fetch each product page and send it to /scrape/amazon-html  (product info)
//   2. send all products to /score                                  (scores)
//   3. save { status, items, response } under STATE_KEY             (popup reads this)
//
// The popup can also send RESCORE to run the whole thing again (the Retry button).

import {
  API_BASE,
  STATE_KEY,
  type CartItem,
  type CartState,
  type ScoreResponse,
  type ThredMessage,
} from './types';

const LAST_ASINS_KEY = 'thredLastAsins';
const MAX_ITEMS = 50; // /score accepts 1-50 items

chrome.runtime.onInstalled.addListener(() => {
  console.log('[Thred] extension installed');
});

chrome.runtime.onMessage.addListener((message: ThredMessage, _sender, sendResponse) => {
  if (message.type === 'SCRAPE_AMAZON_CART') {
    chrome.storage.local.set({ [LAST_ASINS_KEY]: message.asins });
    runCart(message.asins).then(sendResponse);
    return true; // keeps sendResponse open for the async work
  }

  if (message.type === 'RESCORE') {
    chrome.storage.local.get(LAST_ASINS_KEY).then(saved => {
      const asins = (saved[LAST_ASINS_KEY] as string[] | undefined) ?? [];
      if (asins.length === 0) {
        sendResponse({ success: false, error: 'No cart to score yet' });
        return;
      }
      runCart(asins).then(sendResponse);
    });
    return true;
  }
});

async function runCart(asins: string[]) {
  await saveState({ status: 'loading', startedAt: Date.now() });
  try {
    const { products, skipped } = await scrapeProducts(asins.slice(0, MAX_ITEMS));
    // Kept for anything else that reads the raw scraped items.
    await chrome.storage.local.set({ cartItems: products });

    if (products.length === 0) {
      throw new FriendlyError("We couldn't read any items in your cart. Try refreshing the cart page.");
    }

    const response = await scoreItems(products);
    await saveState({ status: 'ready', items: products, response, skipped, updatedAt: Date.now() });
    return { success: true };
  } catch (error) {
    console.error('[Thred] Scoring failed:', error);
    await saveState({ status: 'error', message: friendlyMessage(error), updatedAt: Date.now() });
    return { success: false, error: String(error) };
  }
}

// Step 1: get product info for each ASIN (teammate's original scraping loop).
async function scrapeProducts(asins: string[]) {
  const products: CartItem[] = [];
  let skipped = 0;

  for (const asin of asins) {
    try {
      const productResponse = await fetch(`https://www.amazon.com/dp/${asin}`, {
        credentials: 'include',
      });
      if (!productResponse.ok) {
        throw new Error(`Amazon returned ${productResponse.status}`);
      }
      const html = await productResponse.text();

      const apiResponse = await fetch(`${API_BASE}/scrape/amazon-html`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ asin, html }),
      });
      if (!apiResponse.ok) {
        throw new Error(`Backend returned ${apiResponse.status}`);
      }

      const result = await apiResponse.json();
      const product = cleanProduct(result.product, asin);
      if (product) {
        products.push(product);
        console.log('[Thred] Scraped product:', product);
      } else {
        skipped += 1;
      }
    } catch (error) {
      // If the backend itself is down, stop now instead of failing on every item.
      if (error instanceof TypeError) throw error;
      skipped += 1;
      console.error(`[Thred] Failed to scrape ${asin}:`, error);
    }
  }

  return { products, skipped };
}

// /score needs item_id and title. Drop anything without a title and remove
// null values so the request matches the backend's schema.
function cleanProduct(raw: Record<string, unknown> | null | undefined, asin: string): CartItem | null {
  if (!raw || typeof raw.title !== 'string' || !raw.title.trim()) return null;
  return {
    item_id: typeof raw.item_id === 'string' && raw.item_id ? raw.item_id : asin,
    title: raw.title,
    brand: typeof raw.brand === 'string' ? raw.brand : null,
    price: typeof raw.price === 'number' ? raw.price : null,
    image_url: typeof raw.image_url === 'string' ? raw.image_url : null,
    product_url: typeof raw.product_url === 'string' ? raw.product_url : null,
    material_text: typeof raw.material_text === 'string' ? raw.material_text : null,
    category: typeof raw.category === 'string' ? raw.category : null,
    certifications: Array.isArray(raw.certifications)
      ? raw.certifications.filter((c): c is string => typeof c === 'string')
      : [],
  };
}

// Step 2: send all products to /score in one request.
async function scoreItems(items: CartItem[]): Promise<ScoreResponse> {
  const res = await fetch(`${API_BASE}/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) {
    throw new FriendlyError(`The Thred server had a problem scoring your cart (error ${res.status}).`);
  }
  return (await res.json()) as ScoreResponse;
}

function saveState(state: CartState) {
  return chrome.storage.local.set({ [STATE_KEY]: state });
}

class FriendlyError extends Error {}

function friendlyMessage(error: unknown): string {
  if (error instanceof FriendlyError) return error.message;
  // fetch() throws TypeError when it can't reach the server at all.
  if (error instanceof TypeError) {
    return "Can't reach the Thred server. Make sure the backend is running, then try again.";
  }
  return 'Something went wrong while scoring your cart. Please try again.';
}
