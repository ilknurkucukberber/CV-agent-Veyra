# Veyra · Frontend

Next.js App Router, React ve TypeScript ile geliştirilen Veyra arayüzü.

Kurulum, test hesabı, mimari ve uçtan uca çalıştırma adımları için [ana README](../README.md) dosyasına bakın.

## Yerel geliştirme

```bash
npm ci
cp .env.example .env.local
npm run dev -- --port 3006
```

API istekleri `/api/v1` üzerinden Next.js’e gelir. `next.config.ts`, bu istekleri `API_INTERNAL_URL` ile belirtilen FastAPI servisine iletir. Yerel geliştirmede varsayılan backend adresi `http://127.0.0.1:8000`, Docker derlemesinde `http://backend:8000` olur.

## Kontroller

```bash
npm test
npx tsc --noEmit
npm run build
```

Docker’da ön yüz standalone imajdan çalışır. Kaynak değişikliklerini görmek için depo kökünden yeniden derleyin:

```bash
docker compose up -d --build --wait frontend
```
