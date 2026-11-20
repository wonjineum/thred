// Sample data for previewing the popup outside Chrome (npx vite, then open
// http://localhost:5173/?state=ready). Matches the cart in Zoe's design, and
// shows the shape to aim for when the backend starts returning alternatives.

import type { CartState } from './types';

const now = Date.now();

export const SAMPLE_READY: CartState = {
  status: 'ready',
  updatedAt: now,
  skipped: 0,
  items: [
    {
      item_id: 'B0HOODIE01',
      title: 'Oversized Hoodie',
      brand: 'Amazon Essentials',
      price: 49.99,
      image_url: null,
      product_url: 'https://www.amazon.com/dp/B0HOODIE01',
      material_text: '100% Recycled Polyester',
      category: 'Hoodies',
      certifications: [],
    },
    {
      item_id: 'B0JEANS002',
      title: 'Straight Leg Jeans',
      brand: 'The Drop',
      price: 69.99,
      image_url: null,
      product_url: 'https://www.amazon.com/dp/B0JEANS002',
      material_text: null,
      category: 'Jeans',
      certifications: [],
    },
  ],
  response: {
    mock: true,
    cart: {
      item_count: 2,
      average_total: 50,
      verdict: 'okay',
      verdict_label: 'Okay',
      headline: '1 of 2 items have a lower-impact alternative',
    },
    items: [
      {
        item_id: 'B0HOODIE01',
        total: 72,
        verdict: 'good_choice',
        verdict_label: 'Good choice',
        impact: 'Uses roughly 40% less water than a typical item like this',
        brand: { points: 28, max: 34, summary: 'Some verified sustainability practices' },
        material: { points: 25, max: 33, summary: 'Recycled materials' },
      },
      {
        item_id: 'B0JEANS002',
        total: 28,
        verdict: 'consider_alternatives',
        verdict_label: 'Consider alternatives',
        impact: 'A lower-impact alternative is likely available',
        brand: { points: 8, max: 34, summary: 'No sustainability information found' },
        material: { points: 11, max: 33, summary: 'Plastic-based materials' },
        alternatives: [
          {
            title: 'Vintage Straight Jeans',
            brand: 'Pact',
            product_url: 'https://www.amazon.com/s?k=pact+organic+straight+jeans',
            image_url: null,
            price: 64,
            total: 78,
          },
          {
            title: "Levi's 501 Original Fit Jeans",
            brand: "Levi's",
            product_url: 'https://www.amazon.com/s?k=levis+501',
            image_url: null,
            price: 59.5,
            total: 66,
          },
        ],
      },
    ],
  },
};

export const SAMPLE_STATES: Record<string, CartState | null> = {
  ready: SAMPLE_READY,
  loading: { status: 'loading', startedAt: now },
  error: {
    status: 'error',
    updatedAt: now,
    message: "Can't reach the Thred server. Make sure the backend is running, then try again.",
  },
  empty: null,
};
