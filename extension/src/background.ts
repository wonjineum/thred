// Background service worker — will eventually call the FastAPI backend
// and coordinate between the content script and the popup.

chrome.runtime.onInstalled.addListener(() => {
  console.log('[Thred] extension installed');
});

/* When content.ts sends a message containing the cart ASINs, background.ts will receive it. */

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type !== 'SCRAPE_AMAZON_CART') {
    return;
  }

  async function scrapeCart() {
    const products = [];

    for (const asin of message.asins as string[]) {
      try {
        const productResponse = await fetch(
          `https://www.amazon.com/dp/${asin}`,
          { credentials: 'include' }
        );

        if (!productResponse.ok) {
          throw new Error(`Amazon returned ${productResponse.status}`);
        }

        const html = await productResponse.text();

        const apiResponse = await fetch(
          'http://127.0.0.1:8000/scrape/amazon-html',
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ asin, html }),
          }
        );

        if (!apiResponse.ok) {
          throw new Error(`Backend returned ${apiResponse.status}`);
        }

        const result = await apiResponse.json();
        products.push(result.product);

        console.log('[Thred] Scraped product:', result.product);
      } catch (error) {
        console.error(`[Thred] Failed to scrape ${asin}:`, error);
      }
    }

    await chrome.storage.local.set({ cartItems: products });
    console.log('[Thred] Saved cart items:', products);
  }

  scrapeCart()
    .then(() => sendResponse({ success: true }))
    .catch(error => sendResponse({ success: false, error: String(error) }));

  return true;
});

