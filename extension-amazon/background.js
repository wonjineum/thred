chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id || !tab.url?.includes("amazon.com")) return;

  try {
    await chrome.tabs.sendMessage(tab.id, { type: "THRED_TOGGLE" });
  } catch {
    await chrome.scripting?.executeScript?.({ target: { tabId: tab.id }, files: ["content.js"] });
  }
});

chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === "THRED_OPEN_DASHBOARD") {
    chrome.tabs.create({ url: "http://localhost:5173" });
  }
});