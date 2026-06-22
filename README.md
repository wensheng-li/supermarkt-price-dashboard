# supermarkt-price-dashboard
A demo dashboard for comparing the groceries' prices in the local supermarket.

```
supermarket-price-dashboard/
├── frontend/          ← React app (deployed to Vercel)
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       └── utils/
├── backend/           ← Express.js API (deployed to Railway)
│   └── src/
│       ├── routes/
│       ├── controllers/
│       ├── middleware/
│       └── db/
├── scraper/           ← Python scraper (runs via GitHub Actions)
│   ├── spiders/
│   └── pipelines/
├── docker-compose.yml ← Spin up local DB + Redis instantly
├── .gitignore
└── README.md
```

