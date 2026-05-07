# Tracker

Personal-use, **localhost-only** portfolio tracker. Crypto via Binance (read-only API). Anything else (Argentine equities held at IEB+, Cocos, IoL; positions on Quantfury) is **manually entered**, with current prices and history pulled from public price-data feeds.

## Locked product decisions

- **No FX conversion.** Each position stays in its source's native currency. The Overview shows per-currency-bucket subtotals only — never a single merged global number.
- USD stablecoins (USDT / USDC / BUSD / FDUSD / DAI) are grouped into a single display bucket called `USD-stables`.
- **Binance is the only live API connector** in this MVP (Spot only). Quantfury, IEB+, Cocos Capital, and IoL have no documented public APIs for personal automation, so they are not integrated — use manual entry instead.
- Background sync runs every 15 minutes (with jitter), plus a manual refresh per connector in the UI.
- Everything binds to `127.0.0.1`. No cloud deployment.

## Quick start (Docker)

```powershell
copy .env.example .env
# (Optional, Phase 2) edit .env and add your read-only Binance API key + secret
docker compose up --build
```

Then visit:

- UI: <http://127.0.0.1:3000>
- API: <http://127.0.0.1:8000/docs>

## Native dev (alternate)

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Frontend (separate terminal):

```powershell
cd frontend
npm install
npm run dev
```

## Binance API key — read-only setup

1. Sign in at <https://www.binance.com> and go to **API Management**.
2. **Create API** → label it `tracker-readonly`.
3. **Edit restrictions**:
   - ✅ **Enable Reading**
   - ❌ Disable spot & margin trading
   - ❌ Disable withdrawals
   - ❌ Disable futures
4. (Recommended) Restrict access to your home IP.
5. Copy the API key and secret into `.env`:
   ```
   BINANCE_API_KEY=...
   BINANCE_API_SECRET=...
   ```
6. Restart the backend.

The app **never** writes orders. If your key has trading permissions, the app still won't use them, but read-only is the safe default.

## Manual position entry

Add anything that isn't on Binance via **Positions → New**. You'll need:

- A symbol the price feed recognizes:
  - **Crypto** → CoinGecko id, e.g. `bitcoin`, `solana`, `ethereum`
  - **ARG equities** → Stooq symbol, e.g. `ggal.ar`, `ypfd.ar`, `pamp.ar`
- Quantity, cost basis (price per unit), and the cost-basis currency.

Current marks and history come from the same public feed. P/L is computed as
`(current_price − cost_basis_per_unit) × quantity` in the position's cost-basis currency. **Cross-currency conversion is never done.**

## Stubbed venues

`backend/app/adapters/{quantfury,iebplus,cocos,iol}.py` exist as files only and raise `NotImplementedError`. Until each venue publishes an official API for personal automation, they will stay stubbed; use manual entry.

## Repository

This project has its own git repo at `tracker/.git`. The home directory's outer git repo (at `c:\Users\pepe_\`) ignores everything by default, so `tracker/` does not leak into it.
