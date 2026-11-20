// Shared types for the extension. These mirror backend/app/schemas.py,
// so if the backend's /score response changes, update this file too.

// Where the FastAPI backend runs. Change this when it's deployed on Railway.
export const API_BASE = 'http://127.0.0.1:8000';

// chrome.storage.local key that holds everything the popup shows.
export const STATE_KEY = 'thredCart';

// ---------- What we send to POST /score ----------

export interface CartItem {
  item_id: string;
  title: string;
  brand?: string | null;
  price?: number | null;
  image_url?: string | null;
  product_url?: string | null;
  material_text?: string | null;
  category?: string | null;
  certifications?: string[];
}

// ---------- What POST /score sends back ----------

export type Verdict = 'good_choice' | 'okay' | 'consider_alternatives';

export interface ScoreComponent {
  points: number;
  max: number;
  summary: string;
}

// The backend doesn't return alternatives yet. When it does, it should send
// a list like this on each item, and the popup will show them automatically.
export interface Alternative {
  title: string;
  product_url: string;
  brand?: string | null;
  image_url?: string | null;
  price?: number | null;
  total?: number | null; // its Thred score, if known
}

export interface ItemScore {
  item_id: string;
  total: number;
  verdict: Verdict;
  verdict_label: string;
  impact: string;
  brand: ScoreComponent;
  material: ScoreComponent;
  alternatives?: Alternative[];
}

export interface CartSummary {
  item_count: number;
  average_total: number;
  verdict: Verdict;
  verdict_label: string;
  headline: string;
}

export interface ScoreResponse {
  items: ItemScore[];
  cart: CartSummary;
  mock: boolean;
}

// ---------- What the background saves for the popup ----------

export type CartState =
  | { status: 'loading'; startedAt: number }
  | {
      status: 'ready';
      items: CartItem[];
      response: ScoreResponse;
      skipped: number; // cart items we couldn't read from Amazon
      updatedAt: number;
    }
  | { status: 'error'; message: string; updatedAt: number };

// Messages between content script, popup and background.
export type ThredMessage =
  | { type: 'SCRAPE_AMAZON_CART'; asins: string[] }
  | { type: 'RESCORE' };
