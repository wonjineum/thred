// Thred popup. Layout follows Zoe's "[FINAL] Thred extension 3" design:
// header -> cart summary -> swap banner -> item cards -> better alternatives -> Swap item.

import React, { useEffect, useState } from 'react';
import { SAMPLE_STATES } from './sampleData';
import {
  STATE_KEY,
  type Alternative,
  type CartItem,
  type CartState,
  type ItemScore,
  type ScoreComponent,
  type Verdict,
} from './types';

// If scoring hasn't finished after this long, show an error instead of loading forever.
const LOADING_TIMEOUT_MS = 2 * 60 * 1000;

// Outside Chrome (npx vite), chrome.storage doesn't exist, so the popup shows
// sample data instead. Pick a state with ?state=ready|loading|error|empty.
const IN_EXTENSION = typeof chrome !== 'undefined' && !!chrome.storage?.local;

// Profile menu links. TODO: fill these in once the dashboard is deployed.
const MENU_LINKS: { label: string; url: string | null }[] = [
  { label: 'Help', url: null },
  { label: 'Dashboard', url: null },
  { label: 'Profile', url: null },
  { label: 'Settings', url: null },
];

// Colors from the design.
const COLORS: Record<Verdict, { text: string; bar: string }> = {
  good_choice: { text: 'text-[#2E7D32]', bar: 'bg-[#2E7D32]' },
  okay: { text: 'text-[#D99A1A]', bar: 'bg-[#E0A21B]' },
  consider_alternatives: { text: 'text-[#D32F2F]', bar: 'bg-[#D64545]' },
};
const SUMMARY_TOOLTIP =
  "This is the average of your items' scores. Each item is scored out of 100 based on its brand, its fabric, and history.";

// ---------- Reading the state the background saved ----------

function useCartState(): CartState | null | undefined {
  // undefined = still reading storage, null = nothing scored yet
  const [state, setState] = useState<CartState | null | undefined>(undefined);

  useEffect(() => {
    if (!IN_EXTENSION) {
      const pick = new URLSearchParams(window.location.search).get('state') ?? 'ready';
      setState(SAMPLE_STATES[pick] ?? null);
      return;
    }
    chrome.storage.local.get(STATE_KEY).then(saved => {
      setState((saved[STATE_KEY] as CartState | undefined) ?? null);
    });
    // Update live while the popup is open (e.g. loading -> ready).
    const onChange = (changes: { [key: string]: chrome.storage.StorageChange }, area: string) => {
      if (area === 'local' && changes[STATE_KEY]) {
        setState((changes[STATE_KEY].newValue as CartState | undefined) ?? null);
      }
    };
    chrome.storage.onChanged.addListener(onChange);
    return () => chrome.storage.onChanged.removeListener(onChange);
  }, []);

  return state;
}

function retry() {
  if (IN_EXTENSION) chrome.runtime.sendMessage({ type: 'RESCORE' });
  else console.log('[Thred] Retry clicked (preview mode)');
}

function formatPrice(price: number | null | undefined) {
  return typeof price === 'number' ? `$${price.toFixed(2)}` : null;
}

// ---------- Icons ----------

function LeafLogo() {
  return (
    <svg viewBox="0 0 24 24" className="h-6 w-6 text-[#D23A3A]" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
      <path d="M20 3C10 3 5 9 5 15c0 2 .5 3.5 1.5 4.5" strokeLinecap="round" />
      <path d="M20 3c0 9-5 15-12 15" strokeLinecap="round" />
      <path d="M3 21l7-8" strokeLinecap="round" />
    </svg>
  );
}

function ProfileIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <circle cx="12" cy="12" r="9.5" />
      <circle cx="12" cy="10" r="3" />
      <path d="M6.5 18.5c1.2-2.2 3.2-3.3 5.5-3.3s4.3 1.1 5.5 3.3" />
    </svg>
  );
}

function SproutIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-[#2E7D32]" fill="currentColor" aria-hidden>
      <path d="M12 21v-7c0-4-3-7-9-7 0 4 3 7 9 7" />
      <path d="M12 14c0-4 3-7 9-7 0 4-3 7-9 7" />
    </svg>
  );
}

// ---------- Header ----------

function Header({ mock }: { mock?: boolean }) {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <header className="relative mb-3 flex items-center justify-between">
      <div className="flex items-center gap-1.5">
        <LeafLogo />
        <span className="text-xl font-bold text-[#D23A3A]">Thred</span>
        {mock && (
          <span
            className="ml-1 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500"
            title="The backend is still returning placeholder scores"
          >
            Sample scores
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 text-gray-600">
        <button
          type="button"
          aria-label="Account menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(o => !o)}
          className="rounded-full p-0.5 hover:bg-gray-100"
        >
          <ProfileIcon />
        </button>
        <button type="button" aria-label="Close" onClick={() => window.close()} className="px-1 text-lg leading-none hover:text-gray-900">
          ×
        </button>
      </div>
      {menuOpen && (
        <ul className="absolute right-6 top-8 z-10 w-32 rounded-md border border-gray-200 bg-white py-1 text-center text-xs shadow-md">
          {MENU_LINKS.map(link => (
            <li key={link.label}>
              {link.url ? (
                <a href={link.url} target="_blank" rel="noreferrer" className="block px-3 py-1.5 text-gray-700 hover:bg-gray-50">
                  {link.label}
                </a>
              ) : (
                <span className="block cursor-default px-3 py-1.5 text-gray-400" title="Coming soon">
                  {link.label}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </header>
  );
}

function Shell({ children, mock }: { children: React.ReactNode; mock?: boolean }) {
  return (
    <div className="w-[360px] bg-white p-4 font-sans text-gray-900">
      <Header mock={mock} />
      {children}
    </div>
  );
}

// ---------- Cart summary ----------

function CartSummaryCard({ total, count, verdict }: { total: number; count: number; verdict: Verdict }) {
  const [tip, setTip] = useState(false);
  const pos = Math.min(100, Math.max(0, total));
  return (
    <section className="relative mb-3 rounded-xl border border-gray-200 p-3">
      <div className="flex items-start justify-between">
        <div>
          <p className="flex items-center gap-1 text-[15px] font-medium">
            Cart Sustainability Summary
            <button
              type="button"
              aria-label="What is this score?"
              onMouseEnter={() => setTip(true)}
              onMouseLeave={() => setTip(false)}
              onFocus={() => setTip(true)}
              onBlur={() => setTip(false)}
              className="flex h-3.5 w-3.5 items-center justify-center rounded-full border border-gray-400 text-[9px] text-gray-500"
            >
              i
            </button>
          </p>
          <p className="text-xs text-gray-500">
            {count} {count === 1 ? 'Item' : 'Items'}
          </p>
        </div>
        <div className="text-right">
          <p className={`text-3xl font-semibold leading-none ${COLORS[verdict].text}`}>
            {total} <span className="text-sm font-normal text-gray-500">/100</span>
          </p>
          <p className="mt-1 text-[11px] text-gray-500">Average score</p>
        </div>
      </div>
      {tip && (
        <p role="tooltip" className="absolute left-24 top-9 z-10 w-52 rounded-md border border-gray-200 bg-white p-2 text-[10px] leading-snug text-gray-600 shadow-md">
          {SUMMARY_TOOLTIP}
        </p>
      )}
      <div className="relative mx-1 mt-3 h-2 rounded-full bg-gradient-to-r from-[#C62828] via-[#E0A21B] to-[#2E7D32]">
        <div
          className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-[4px] border-2 border-white bg-[#E0A21B] shadow"
          style={{ left: `${pos}%` }}
          aria-hidden
        />
      </div>
      <div className="mt-2 flex justify-between text-xs">
        <span className="text-[#D32F2F]">Poor</span>
        <span className="text-[#2E7D32]">Great</span>
      </div>
    </section>
  );
}

function Banner({ text }: { text: string }) {
  return (
    <div className="mb-3 flex items-center gap-2 rounded-lg bg-[#DDF1E1] px-3 py-2 text-xs font-medium leading-snug text-gray-800">
      <SproutIcon />
      <p>{text}</p>
    </div>
  );
}

// ---------- Item cards ----------

function ProductImage({ src, alt, size }: { src?: string | null; alt: string; size: string }) {
  const [broken, setBroken] = useState(false);
  if (!src || broken) {
    return <div className={`${size} shrink-0 rounded-md bg-[#A3BAD6]`} aria-label="No image" />;
  }
  return <img src={src} alt={alt} onError={() => setBroken(true)} className={`${size} shrink-0 rounded-md bg-white object-contain`} />;
}

function ScoreRow({ label, component, color }: { label: string; component: ScoreComponent; color: string }) {
  const pct = component.max > 0 ? Math.round((component.points / component.max) * 100) : 0;
  return (
    <div className="flex items-center gap-2 text-[11px] text-gray-500">
      <span className="w-12">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-9 text-right">
        {component.points}/{component.max}
      </span>
    </div>
  );
}

// History is scored by the extension itself, which isn't built yet.
function HistoryRowPlaceholder() {
  return (
    <div className="flex items-center gap-2 text-[11px] text-gray-400" title="History isn't scored yet">
      <span className="w-12">History</span>
      <div className="h-1.5 flex-1 rounded-full border border-dashed border-gray-300" />
      <span className="w-9 text-right">–/33</span>
    </div>
  );
}

function missingDataNotes(item: CartItem): string[] {
  const notes: string[] = [];
  if (!item.brand) notes.push('No brand found on the page');
  if (!item.material_text) notes.push('No material info on the page');
  return notes;
}

function ItemCard({ item, score }: { item: CartItem; score: ItemScore }) {
  const colors = COLORS[score.verdict];
  const hasAlternative = (score.alternatives?.length ?? 0) > 0;
  const tag = [score.material.summary, hasAlternative ? 'Better option available' : null].filter(Boolean).join(' · ');
  const notes = missingDataNotes(item);

  return (
    <li className="rounded-xl border border-gray-200 p-3">
      <div className="flex gap-3">
        <ProductImage src={item.image_url} alt={item.title} size="h-16 w-16" />
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="line-clamp-2 text-sm font-medium leading-snug">{item.title}</p>
              <p className="truncate text-[11px] text-gray-500">{item.brand ?? 'Unknown brand'}</p>
            </div>
            <p className={`shrink-0 text-xl font-semibold leading-none ${colors.text}`} aria-label={`Score ${score.total} out of 100`}>
              {score.total} <span className="text-[11px] font-normal text-gray-500">/100</span>
            </p>
          </div>
          <div className="mt-2 space-y-1.5">
            <ScoreRow label="Brand" component={score.brand} color={colors.bar} />
            <ScoreRow label="Material" component={score.material} color={colors.bar} />
            <HistoryRowPlaceholder />
          </div>
        </div>
      </div>
      <p className={`mt-2 text-[11px] ${colors.text}`}>{tag}</p>
      {notes.length > 0 && <p className="mt-0.5 text-[10px] text-gray-400">ⓘ {notes.join(' · ')}, so the score is a rough estimate</p>}
    </li>
  );
}

// ---------- Better alternatives ----------

interface AltWithContext {
  alt: Alternative;
  original: CartItem; // the cart item it would replace
}

function AlternativeCard({ entry }: { entry: AltWithContext }) {
  const { alt, original } = entry;
  const saving =
    typeof alt.price === 'number' && typeof original.price === 'number' && original.price > alt.price
      ? original.price - alt.price
      : null;
  return (
    <a href={alt.product_url} target="_blank" rel="noreferrer" className="flex min-w-0 flex-1 gap-3 rounded-xl border border-gray-200 p-2.5 hover:border-[#2E7D32]">
      <ProductImage src={alt.image_url} alt={alt.title} size="h-16 w-16" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{alt.title}</p>
        <div className="mt-0.5 flex items-center gap-2 text-[11px] text-gray-500">
          {alt.brand && <span className="truncate">{alt.brand}</span>}
          <span className="whitespace-nowrap rounded bg-[#DDF1E1] px-1.5 py-0.5 text-[10px] font-medium text-[#2E7D32]">Better Choice</span>
        </div>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-sm font-semibold">{formatPrice(alt.price) ?? ''}</span>
          {saving !== null && (
            <span className="whitespace-nowrap rounded bg-[#DDF1E1] px-1.5 py-0.5 text-[10px] font-semibold text-[#2E7D32]">
              SAVE ${saving.toFixed(2)}
            </span>
          )}
        </div>
      </div>
      {typeof alt.total === 'number' && (
        <p className="self-center whitespace-nowrap text-xl font-semibold text-[#2E7D32]">
          {alt.total} <span className="text-[11px] font-normal text-gray-500">/100</span>
        </p>
      )}
    </a>
  );
}

function Alternatives({ entries }: { entries: AltWithContext[] }) {
  const [index, setIndex] = useState(0);
  const [showAll, setShowAll] = useState(false);
  const current = entries[Math.min(index, entries.length - 1)];
  const step = (d: number) => setIndex(i => (i + d + entries.length) % entries.length);
  const arrow = 'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-gray-200 text-xs text-gray-500 hover:bg-gray-50';

  return (
    <section className="mt-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-medium">Better alternatives</p>
        {entries.length > 1 && (
          <button type="button" onClick={() => setShowAll(s => !s)} className="text-xs text-[#2E7D32] underline">
            {showAll ? 'Show less' : 'See all'}
          </button>
        )}
      </div>

      {showAll ? (
        <div className="space-y-2">
          {entries.map(e => (
            <AlternativeCard key={e.alt.product_url} entry={e} />
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-1">
          {entries.length > 1 && (
            <button type="button" aria-label="Previous alternative" onClick={() => step(-1)} className={arrow}>
              ‹
            </button>
          )}
          <AlternativeCard entry={current} />
          {entries.length > 1 && (
            <button type="button" aria-label="Next alternative" onClick={() => step(1)} className={arrow}>
              ›
            </button>
          )}
        </div>
      )}

      {/* Amazon doesn't let extensions edit the cart, so "Swap item" opens the better product. */}
      <a
        href={current.alt.product_url}
        target="_blank"
        rel="noreferrer"
        className="mt-3 block rounded-lg bg-[#D23A3A] py-2 text-center text-sm font-semibold text-white hover:bg-[#B92F2F]"
      >
        Swap item
      </a>
    </section>
  );
}

// ---------- Whole-popup states ----------

function LoadingView() {
  return (
    <Shell>
      <p className="mb-3 text-sm text-gray-600" role="status">
        Scoring the clothes in your cart…
      </p>
      <div className="mb-3 h-24 animate-pulse rounded-xl bg-gray-100" />
      <ul className="space-y-3">
        {[0, 1].map(i => (
          <li key={i} className="flex animate-pulse gap-3 rounded-xl border border-gray-200 p-3">
            <div className="h-16 w-16 rounded-md bg-gray-200" />
            <div className="flex-1 space-y-2 py-1">
              <div className="h-3 w-3/5 rounded bg-gray-200" />
              <div className="h-2 w-full rounded bg-gray-100" />
              <div className="h-2 w-full rounded bg-gray-100" />
              <div className="h-2 w-full rounded bg-gray-100" />
            </div>
          </li>
        ))}
      </ul>
    </Shell>
  );
}

function MessageView({ title, body, action }: { title: string; body: string; action?: boolean }) {
  return (
    <Shell>
      <div className="rounded-xl border border-gray-200 p-4 text-center">
        <p className="text-sm font-semibold">{title}</p>
        <p className="mt-1 text-xs leading-relaxed text-gray-600">{body}</p>
        {action && (
          <button type="button" onClick={retry} className="mt-3 rounded-lg bg-[#D23A3A] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#B92F2F]">
            Try again
          </button>
        )}
      </div>
    </Shell>
  );
}

function ReadyView({ state }: { state: Extract<CartState, { status: 'ready' }> }) {
  const { response, items, skipped } = state;
  const byId = new Map(items.map(i => [i.item_id, i]));
  const rows = response.items.map(score => ({
    score,
    item: byId.get(score.item_id) ?? ({ item_id: score.item_id, title: 'Unknown item' } as CartItem),
  }));
  const alternatives: AltWithContext[] = rows.flatMap(({ score, item }) =>
    (score.alternatives ?? []).map(alt => ({ alt, original: item })),
  );
  const cart = response.cart;
  const bannerText = rows.some(r => r.score.verdict === 'consider_alternatives')
    ? 'Swap to the lower-impact option and help keep clothes out of landfill!'
    : cart.headline;

  return (
    <Shell mock={response.mock}>
      <CartSummaryCard total={cart.average_total} count={cart.item_count} verdict={cart.verdict} />
      <Banner text={bannerText} />
      {/* Chrome caps popups at 600px tall and scrolls the whole popup past that. */}
      <ul className="space-y-3">
        {rows.map(({ score, item }) => (
          <ItemCard key={score.item_id} item={item} score={score} />
        ))}
      </ul>
      {alternatives.length > 0 && <Alternatives entries={alternatives} />}
      {skipped > 0 && (
        <p className="mt-3 text-center text-[11px] text-gray-500">
          {skipped} {skipped === 1 ? 'item' : 'items'} in your cart couldn't be read and {skipped === 1 ? "isn't" : "aren't"} shown.
        </p>
      )}
    </Shell>
  );
}

// ---------- The popup ----------

export default function Popup() {
  const state = useCartState();

  if (state === undefined) return <Shell>{null}</Shell>; // reading storage, takes a few ms

  if (state === null) {
    return (
      <MessageView
        title="Open your Amazon cart"
        body="Thred scores the clothes in your Amazon cart. Go to your cart and they'll show up here."
      />
    );
  }

  if (state.status === 'loading') {
    if (Date.now() - state.startedAt > LOADING_TIMEOUT_MS) {
      return <MessageView title="This is taking too long" body="Scoring didn't finish. Please try again." action />;
    }
    return <LoadingView />;
  }

  if (state.status === 'error') {
    return <MessageView title="Couldn't score your cart" body={state.message} action />;
  }

  return <ReadyView state={state} />;
}
