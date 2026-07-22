// Background service worker — will eventually call the FastAPI backend
// and coordinate between the content script and the popup.

chrome.runtime.onInstalled.addListener(() => {
  console.log('[Thred] extension installed');
});
