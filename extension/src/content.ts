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

/* hostname checks that the user is on Amazon.

pathname checks that they're on the cart page.

The if statement prevents cart workflow from running on ordinary product pages. */

function isAmazonCartPage(): boolean {
  const hostname = window.location.hostname;
  const pathname = window.location.pathname;

  const isAmazon =
    hostname === 'amazon.com' ||
    hostname.endsWith('.amazon.com');

  const isCart =
    pathname.startsWith('/gp/cart/') ||
    pathname.startsWith('/cart/');

  return isAmazon && isCart;
}



if (isAmazonCartPage()) {
  console.log('[Thred] Amazon cart detected!');

  const asins = getCartASINs();
  console.log('[Thred] Cart ASINs:', asins);

  if (asins.length > 0) {
    chrome.runtime.sendMessage({
      type: 'SCRAPE_AMAZON_CART',
      asins,
    });
  }
}




/* Finds the Amazon product IDs (ASINs) of the items in the cart.

The cart page also has [data-asin] elements outside the cart ("Saved for later",
recommendation carousels), so look inside the active cart first. If Amazon's
layout doesn't have that section, fall back to every [data-asin] on the page.

.map() extracts each ASIN.

.filter() removes empty values.

new Set() removes duplicates.*/
function getCartASINs(): string[] {
  // Declared inside the function: this file runs top to bottom on page load, and
  // a top-level const below the call site isn't initialized yet when it runs.
  const activeCartItems = '#sc-active-cart [data-asin], [data-name="Active Items"] [data-asin]';
  const inCart = document.querySelectorAll(activeCartItems);
  const items = inCart.length > 0 ? inCart : document.querySelectorAll('[data-asin]');

  const asins = [...items]
    .map(item => item.getAttribute('data-asin'))
    .filter((asin): asin is string => Boolean(asin));

  return [...new Set(asins)];
}

